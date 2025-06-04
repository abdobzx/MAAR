"""
Retrieval agent for the Enterprise RAG System.
Handles intelligent search with hybrid search (BM25 + dense) and reranking.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import cohere
import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agents.storage.agent import StorageAgent
from agents.vectorization.agent import VectorizationAgent
from core.config import settings
from core.exceptions import LLMError, VectorDBError, ErrorCodes
from core.logging import LoggerMixin, log_agent_action, log_error
from core.models import SearchQuery, SearchResult, SearchResponse, SearchType
from database.models import DocumentChunk as DBDocumentChunk, Document as DBDocument


class KeywordSearchEngine:
    """BM25-based keyword search engine."""
    
    def __init__(self):
        self.tokenized_corpus = []
        self.bm25 = None
        self.corpus_metadata = []
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25."""
        # Simple tokenization - can be enhanced with proper NLP
        text = text.lower()
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return [token for token in tokens if len(token) > 2]
    
    async def build_index(self, chunks: List[DBDocumentChunk]) -> None:
        """Build BM25 index from document chunks."""
        self.tokenized_corpus = []
        self.corpus_metadata = []
        
        for chunk in chunks:
            tokens = self._tokenize(chunk.content)
            self.tokenized_corpus.append(tokens)
            self.corpus_metadata.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "metadata": chunk.metadata or {}
            })
        
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Search using BM25."""
        if not self.bm25:
            return []
        
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top results
        top_indices = np.argsort(scores)[::-1][:limit]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include relevant results
                results.append((self.corpus_metadata[idx], float(scores[idx])))
        
        return results


class RerankingService:
    """Document reranking service using Cohere or ColBERT."""
    
    def __init__(self):
        self.cohere_client = None
        if settings.llm.cohere_api_key:
            self.cohere_client = cohere.Client(settings.llm.cohere_api_key)
    
    async def rerank_cohere(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """Rerank documents using Cohere's rerank endpoint."""
        if not self.cohere_client:
            # Return original order if Cohere is not available
            return [(i, 1.0 - i * 0.1) for i in range(min(len(documents), top_k))]
        
        try:
            response = self.cohere_client.rerank(
                model="rerank-english-v2.0",
                query=query,
                documents=documents,
                top_k=top_k
            )
            
            return [(result.index, result.relevance_score) for result in response.results]
            
        except Exception as e:
            log_error(e, {"service": "RerankingService", "provider": "cohere"})
            # Fallback to original order
            return [(i, 1.0 - i * 0.1) for i in range(min(len(documents), top_k))]
    
    async def rerank_with_embedding_similarity(
        self,
        query: str,
        query_embedding: List[float],
        search_results: List[SearchResult]
    ) -> List[SearchResult]:
        """Simple reranking based on embedding similarity."""
        # This is a simple implementation - could be enhanced with cross-encoders
        for result in search_results:
            # Combine original score with text length penalty
            length_penalty = min(1.0, len(result.content) / 1000)
            result.score = result.score * (0.8 + 0.2 * length_penalty)
        
        return sorted(search_results, key=lambda x: x.score, reverse=True)


class HybridSearchEngine:
    """Hybrid search combining dense and sparse retrieval."""
    
    def __init__(self, storage_agent: StorageAgent, vectorization_agent: VectorizationAgent):
        self.storage_agent = storage_agent
        self.vectorization_agent = vectorization_agent
        self.keyword_engine = KeywordSearchEngine()
        self.reranker = RerankingService()
    
    async def initialize_keyword_index(self, db_session: AsyncSession) -> None:
        """Initialize the keyword search index."""
        try:
            # Load all chunks for keyword indexing
            stmt = select(DBDocumentChunk)
            result = await db_session.execute(stmt)
            chunks = result.scalars().all()
            
            await self.keyword_engine.build_index(chunks)
            
        except Exception as e:
            log_error(e, {"service": "HybridSearchEngine", "operation": "initialize_keyword_index"})
    
    async def dense_search(
        self,
        query: str,
        search_query: SearchQuery,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """Perform dense vector search."""
        try:
            # Generate query embedding
            provider = self.vectorization_agent.default_provider
            query_embeddings = await provider.generate_embeddings([query])
            query_vector = query_embeddings[0]
            
            # Search in vector database
            results = await self.storage_agent.search_similar_chunks(
                query_vector=query_vector,
                search_query=search_query,
                collection_name=collection_name
            )
            
            return results
            
        except Exception as e:
            log_error(e, {"service": "HybridSearchEngine", "operation": "dense_search"})
            return []
    
    async def sparse_search(
        self,
        query: str,
        limit: int = 10
    ) -> List[SearchResult]:
        """Perform sparse keyword search."""
        try:
            keyword_results = self.keyword_engine.search(query, limit)
            
            results = []
            for metadata, score in keyword_results:
                result = SearchResult(
                    chunk_id=metadata["chunk_id"],
                    document_id=metadata["document_id"],
                    content=metadata["content"],
                    score=score,
                    metadata=metadata["metadata"]
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            log_error(e, {"service": "HybridSearchEngine", "operation": "sparse_search"})
            return []
    
    def _merge_results(
        self,
        dense_results: List[SearchResult],
        sparse_results: List[SearchResult],
        alpha: float = 0.7
    ) -> List[SearchResult]:
        """Merge dense and sparse search results using RRF (Reciprocal Rank Fusion)."""
        # Create a mapping of chunk_id to results
        all_results = {}
        
        # Add dense results
        for i, result in enumerate(dense_results):
            chunk_id = result.chunk_id
            dense_rank = i + 1
            dense_score = result.score
            
            all_results[chunk_id] = {
                "result": result,
                "dense_rank": dense_rank,
                "dense_score": dense_score,
                "sparse_rank": None,
                "sparse_score": 0.0
            }
        
        # Add sparse results
        for i, result in enumerate(sparse_results):
            chunk_id = result.chunk_id
            sparse_rank = i + 1
            sparse_score = result.score
            
            if chunk_id in all_results:
                all_results[chunk_id]["sparse_rank"] = sparse_rank
                all_results[chunk_id]["sparse_score"] = sparse_score
            else:
                all_results[chunk_id] = {
                    "result": result,
                    "dense_rank": None,
                    "dense_score": 0.0,
                    "sparse_rank": sparse_rank,
                    "sparse_score": sparse_score
                }
        
        # Calculate RRF scores
        rrf_k = 60  # RRF parameter
        merged_results = []
        
        for chunk_id, data in all_results.items():
            rrf_score = 0.0
            
            # Dense contribution
            if data["dense_rank"] is not None:
                rrf_score += alpha * (1.0 / (rrf_k + data["dense_rank"]))
            
            # Sparse contribution
            if data["sparse_rank"] is not None:
                rrf_score += (1 - alpha) * (1.0 / (rrf_k + data["sparse_rank"]))
            
            # Update the result score
            result = data["result"]
            result.score = rrf_score
            merged_results.append(result)
        
        # Sort by RRF score
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results
    
    async def hybrid_search(
        self,
        search_query: SearchQuery,
        db_session: AsyncSession,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """Perform hybrid search combining dense and sparse methods."""
        
        # Perform both search types concurrently
        dense_task = self.dense_search(search_query.query, search_query, collection_name)
        sparse_task = self.sparse_search(search_query.query, search_query.limit)
        
        dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)
        
        # Merge results using RRF
        merged_results = self._merge_results(dense_results, sparse_results)
        
        # Apply filters
        if search_query.filters:
            filtered_results = await self._apply_filters(merged_results, search_query.filters, db_session)
        else:
            filtered_results = merged_results
        
        # Limit results
        final_results = filtered_results[:search_query.limit]
        
        # Rerank if requested
        if search_query.rerank and final_results:
            final_results = await self._rerank_results(search_query.query, final_results)
        
        return final_results
    
    async def _apply_filters(
        self,
        results: List[SearchResult],
        filters: Dict[str, Any],
        db_session: AsyncSession
    ) -> List[SearchResult]:
        """Apply metadata filters to search results."""
        if not filters:
            return results
        
        filtered_results = []
        chunk_ids = [str(result.chunk_id) for result in results]
        
        # Build filter conditions for SQL query
        filter_conditions = []
        filter_values = {}
        
        for key, value in filters.items():
            if key == "document_id":
                filter_conditions.append("d.id = :document_id")
                filter_values["document_id"] = value
            elif key == "user_id":
                filter_conditions.append("d.user_id = :user_id")
                filter_values["user_id"] = value
            elif key == "organization_id":
                filter_conditions.append("d.organization_id = :organization_id")
                filter_values["organization_id"] = value
            else:
                # Handle metadata filters
                filter_conditions.append(f"dc.metadata ->> '{key}' = :{key}")
                filter_values[key] = str(value)
        
        if filter_conditions:
            where_clause = " AND ".join(filter_conditions)
            query = f"""
                SELECT dc.id
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.id = ANY(:chunk_ids) AND {where_clause}
            """
            
            result = await db_session.execute(
                text(query),
                {**filter_values, "chunk_ids": chunk_ids}
            )
            valid_chunk_ids = {str(row[0]) for row in result.fetchall()}
            
            # Filter results
            for result in results:
                if str(result.chunk_id) in valid_chunk_ids:
                    filtered_results.append(result)
        else:
            filtered_results = results
        
        return filtered_results
    
    async def _rerank_results(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Rerank search results using Cohere or other reranking service."""
        if not results:
            return results
        
        try:
            documents = [result.content for result in results]
            rerank_scores = await self.reranker.rerank_cohere(query, documents, len(results))
            
            # Update scores based on reranking
            reranked_results = []
            for original_idx, rerank_score in rerank_scores:
                result = results[original_idx]
                # Combine original score with rerank score
                result.score = 0.3 * result.score + 0.7 * rerank_score
                reranked_results.append(result)
            
            return reranked_results
            
        except Exception as e:
            log_error(e, {"service": "HybridSearchEngine", "operation": "rerank_results"})
            return results


class RetrievalAgent(LoggerMixin):
    """Retrieval agent for intelligent document search and retrieval."""
    
    def __init__(self, storage_agent: StorageAgent, vectorization_agent: VectorizationAgent):
        self.storage_agent = storage_agent
        self.vectorization_agent = vectorization_agent
        self.hybrid_engine = HybridSearchEngine(storage_agent, vectorization_agent)
    
    async def initialize(self, db_session: AsyncSession) -> None:
        """Initialize the retrieval agent."""
        await self.hybrid_engine.initialize_keyword_index(db_session)
        self.logger.info("RetrievalAgent initialized successfully")
    
    async def search(
        self,
        search_query: SearchQuery,
        db_session: AsyncSession,
        collection_name: Optional[str] = None
    ) -> SearchResponse:
        """Perform intelligent search based on query type."""
        
        log_agent_action(
            agent_name="RetrievalAgent",
            action="search",
            query=search_query.query,
            search_type=search_query.search_type.value,
            limit=search_query.limit
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            if search_query.search_type == SearchType.SEMANTIC:
                results = await self.hybrid_engine.dense_search(
                    search_query.query,
                    search_query,
                    collection_name
                )
            elif search_query.search_type == SearchType.KEYWORD:
                results = await self.hybrid_engine.sparse_search(
                    search_query.query,
                    search_query.limit
                )
            else:  # HYBRID
                results = await self.hybrid_engine.hybrid_search(
                    search_query,
                    db_session,
                    collection_name
                )
            
            # Enrich results with document metadata
            enriched_results = await self._enrich_results_with_metadata(results, db_session)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            response = SearchResponse(
                results=enriched_results,
                total_results=len(enriched_results),
                query=search_query.query,
                search_type=search_query.search_type,
                execution_time=execution_time
            )
            
            self.logger.info(
                "Search completed",
                query=search_query.query,
                search_type=search_query.search_type.value,
                num_results=len(enriched_results),
                execution_time=execution_time
            )
            
            return response
            
        except Exception as e:
            log_error(e, {
                "agent": "RetrievalAgent",
                "query": search_query.query,
                "search_type": search_query.search_type.value
            })
            raise
    
    async def _enrich_results_with_metadata(
        self,
        results: List[SearchResult],
        db_session: AsyncSession
    ) -> List[SearchResult]:
        """Enrich search results with document metadata."""
        if not results:
            return results
        
        try:
            # Get document metadata for all results
            document_ids = list(set(str(result.document_id) for result in results))
            
            stmt = select(DBDocument).where(DBDocument.id.in_(document_ids))
            db_result = await db_session.execute(stmt)
            documents = {str(doc.id): doc for doc in db_result.scalars().all()}
            
            # Enrich results
            for result in results:
                doc_id = str(result.document_id)
                if doc_id in documents:
                    doc = documents[doc_id]
                    result.document_metadata = {
                        "filename": doc.filename,
                        "document_type": doc.document_type.value,
                        "metadata": doc.metadata or {}
                    }
            
            return results
            
        except Exception as e:
            log_error(e, {"agent": "RetrievalAgent", "operation": "enrich_results"})
            return results
    
    async def get_similar_documents(
        self,
        document_id: UUID,
        limit: int = 5,
        db_session: Optional[AsyncSession] = None,
        collection_name: Optional[str] = None
    ) -> List[SearchResult]:
        """Find documents similar to a given document."""
        try:
            # Get document content
            stmt = select(DBDocument).where(DBDocument.id == document_id)
            result = await db_session.execute(stmt)
            document = result.scalar_one_or_none()
            
            if not document or not document.content:
                return []
            
            # Create search query using document content
            search_query = SearchQuery(
                query=document.content[:1000],  # Use first 1000 chars as query
                search_type=SearchType.SEMANTIC,
                limit=limit + 1,  # +1 to exclude the original document
                filters={"document_id": {"$ne": str(document_id)}}  # Exclude original
            )
            
            # Perform search
            response = await self.search(search_query, db_session, collection_name)
            
            # Filter out the original document
            similar_docs = [
                result for result in response.results
                if result.document_id != document_id
            ][:limit]
            
            return similar_docs
            
        except Exception as e:
            log_error(e, {
                "agent": "RetrievalAgent",
                "operation": "get_similar_documents",
                "document_id": str(document_id)
            })
            return []
    
    async def refresh_keyword_index(self, db_session: AsyncSession) -> None:
        """Refresh the keyword search index."""
        try:
            await self.hybrid_engine.initialize_keyword_index(db_session)
            self.logger.info("Keyword index refreshed successfully")
        except Exception as e:
            log_error(e, {"agent": "RetrievalAgent", "operation": "refresh_keyword_index"})
            raise
