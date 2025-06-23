"""
Storage agent for the Enterprise RAG System.
Handles vector database operations and metadata management.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from sqlalchemy.ext.asyncio import AsyncSession
import weaviate

from core.config import settings
from core.exceptions import VectorDBError, ErrorCodes
from core.logging import LoggerMixin, log_agent_action, log_error
from core.models import DocumentChunk, SearchQuery, SearchResult
from database.models import DocumentChunk as DBDocumentChunk


class VectorDatabase(ABC):
    """Abstract base class for vector databases."""
    
    @abstractmethod
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """Create a new collection."""
        pass
    
    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,
        chunks: List[DocumentChunk]
    ) -> bool:
        """Insert vectors into the collection."""
        pass
    
    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,
        chunk_ids: List[UUID]
    ) -> bool:
        """Delete vectors by chunk IDs."""
        pass
    
    @abstractmethod
    async def update_vector(
        self,
        collection_name: str,
        chunk: DocumentChunk
    ) -> bool:
        """Update a vector."""
        pass
    
    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection information."""
        pass


class QdrantDatabase(VectorDatabase):
    """Qdrant vector database implementation."""
    
    def __init__(self):
        self.client = QdrantClient(
            host=settings.vector_db.qdrant_host,
            port=settings.vector_db.qdrant_port,
            api_key=settings.vector_db.qdrant_api_key
        )
    
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """Create a new Qdrant collection."""
        try:
            # Check if collection exists
            try:
                self.client.get_collection(collection_name)
                return True  # Collection already exists
            except:
                pass
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to create Qdrant collection: {str(e)}",
                error_code=ErrorCodes.VECTOR_DB_CONNECTION_FAILED
            )
    
    async def insert_vectors(
        self,
        collection_name: str,
        chunks: List[DocumentChunk]
    ) -> bool:
        """Insert vectors into Qdrant collection."""
        try:
            points = []
            for chunk in chunks:
                if not chunk.embedding:
                    continue
                
                point = models.PointStruct(
                    id=str(chunk.id),
                    vector=chunk.embedding,
                    payload={
                        "document_id": str(chunk.document_id),
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "metadata": chunk.metadata,
                        "created_at": chunk.created_at.isoformat(),
                    }
                )
                points.append(point)
            
            if points:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points
                )
            
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to insert vectors into Qdrant: {str(e)}",
                error_code=ErrorCodes.VECTOR_INSERT_FAILED
            )
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar vectors in Qdrant."""
        try:
            # Build filter conditions
            filter_conditions = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchAny(any=value)
                            )
                        )
                    else:
                        conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value)
                            )
                        )
                
                if conditions:
                    filter_conditions = models.Filter(must=conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=filter_conditions,
                limit=limit,
                score_threshold=threshold
            )
            
            # Convert to SearchResult objects
            results = []
            for hit in search_results:
                result = SearchResult(
                    chunk_id=UUID(hit.id),
                    document_id=UUID(hit.payload["document_id"]),
                    content=hit.payload["content"],
                    score=hit.score,
                    metadata=hit.payload.get("metadata", {})
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to search vectors in Qdrant: {str(e)}",
                error_code=ErrorCodes.VECTOR_SEARCH_FAILED
            )
    
    async def delete_vectors(
        self,
        collection_name: str,
        chunk_ids: List[UUID]
    ) -> bool:
        """Delete vectors from Qdrant collection."""
        try:
            point_ids = [str(chunk_id) for chunk_id in chunk_ids]
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids
                )
            )
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to delete vectors from Qdrant: {str(e)}",
                error_code=ErrorCodes.VECTOR_DELETE_FAILED
            )
    
    async def update_vector(
        self,
        collection_name: str,
        chunk: DocumentChunk
    ) -> bool:
        """Update a vector in Qdrant collection."""
        try:
            if not chunk.embedding:
                return False
            
            point = models.PointStruct(
                id=str(chunk.id),
                vector=chunk.embedding,
                payload={
                    "document_id": str(chunk.document_id),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "metadata": chunk.metadata,
                    "updated_at": chunk.updated_at.isoformat(),
                }
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to update vector in Qdrant: {str(e)}",
                error_code=ErrorCodes.VECTOR_INSERT_FAILED
            )
    
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get Qdrant collection information."""
        try:
            collection_info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "optimizer_status": collection_info.optimizer_status,
                "disk_data_size": collection_info.disk_data_size,
                "ram_data_size": collection_info.ram_data_size,
            }
        except Exception as e:
            raise VectorDBError(
                f"Failed to get Qdrant collection info: {str(e)}",
                error_code=ErrorCodes.VECTOR_DB_CONNECTION_FAILED
            )


class WeaviateDatabase(VectorDatabase):
    """Weaviate vector database implementation."""
    
    def __init__(self):
        self.client = weaviate.Client(
            url=settings.vector_db.weaviate_url,
            auth_client_secret=weaviate.AuthApiKey(
                api_key=settings.vector_db.weaviate_api_key
            ) if settings.vector_db.weaviate_api_key else None
        )
    
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """Create a new Weaviate class (collection)."""
        try:
            # Check if class exists
            if self.client.schema.exists(collection_name):
                return True
            
            # Create class schema
            class_schema = {
                "class": collection_name,
                "description": f"Document chunks for {collection_name}",
                "vectorizer": "none",
                "properties": [
                    {
                        "name": "document_id",
                        "dataType": ["string"],
                        "description": "Document ID"
                    },
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Chunk content"
                    },
                    {
                        "name": "chunk_index",
                        "dataType": ["int"],
                        "description": "Chunk index"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["object"],
                        "description": "Chunk metadata"
                    }
                ]
            }
            
            self.client.schema.create_class(class_schema)
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to create Weaviate class: {str(e)}",
                error_code=ErrorCodes.VECTOR_DB_CONNECTION_FAILED
            )
    
    async def insert_vectors(
        self,
        collection_name: str,
        chunks: List[DocumentChunk]
    ) -> bool:
        """Insert vectors into Weaviate class."""
        try:
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for chunk in chunks:
                    if not chunk.embedding:
                        continue
                    
                    properties = {
                        "document_id": str(chunk.document_id),
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "metadata": chunk.metadata,
                    }
                    
                    batch.add_data_object(
                        data_object=properties,
                        class_name=collection_name,
                        uuid=str(chunk.id),
                        vector=chunk.embedding
                    )
            
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to insert vectors into Weaviate: {str(e)}",
                error_code=ErrorCodes.VECTOR_INSERT_FAILED
            )
    
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar vectors in Weaviate."""
        try:
            query = (
                self.client.query
                .get(collection_name, ["document_id", "content", "chunk_index", "metadata"])
                .with_near_vector({"vector": query_vector})
                .with_limit(limit)
                .with_additional(["id", "distance"])
            )
            
            # Add filters if provided
            if filters:
                where_filter = {"operator": "And", "operands": []}
                for key, value in filters.items():
                    where_filter["operands"].append({
                        "path": [key],
                        "operator": "Equal",
                        "valueString": str(value)
                    })
                query = query.with_where(where_filter)
            
            result = query.do()
            
            # Convert to SearchResult objects
            results = []
            if "data" in result and "Get" in result["data"]:
                for item in result["data"]["Get"][collection_name]:
                    # Convert distance to similarity score
                    distance = item["_additional"]["distance"]
                    score = 1 - distance  # Convert distance to similarity
                    
                    if score >= threshold:
                        result_obj = SearchResult(
                            chunk_id=UUID(item["_additional"]["id"]),
                            document_id=UUID(item["document_id"]),
                            content=item["content"],
                            score=score,
                            metadata=item.get("metadata", {})
                        )
                        results.append(result_obj)
            
            return results
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to search vectors in Weaviate: {str(e)}",
                error_code=ErrorCodes.VECTOR_SEARCH_FAILED
            )
    
    async def delete_vectors(
        self,
        collection_name: str,
        chunk_ids: List[UUID]
    ) -> bool:
        """Delete vectors from Weaviate class."""
        try:
            for chunk_id in chunk_ids:
                self.client.data_object.delete(
                    uuid=str(chunk_id),
                    class_name=collection_name
                )
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to delete vectors from Weaviate: {str(e)}",
                error_code=ErrorCodes.VECTOR_DELETE_FAILED
            )
    
    async def update_vector(
        self,
        collection_name: str,
        chunk: DocumentChunk
    ) -> bool:
        """Update a vector in Weaviate class."""
        try:
            if not chunk.embedding:
                return False
            
            properties = {
                "document_id": str(chunk.document_id),
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata,
            }
            
            self.client.data_object.replace(
                uuid=str(chunk.id),
                class_name=collection_name,
                data_object=properties,
                vector=chunk.embedding
            )
            return True
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to update vector in Weaviate: {str(e)}",
                error_code=ErrorCodes.VECTOR_INSERT_FAILED
            )
    
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get Weaviate class information."""
        try:
            schema = self.client.schema.get(collection_name)
            # Get object count
            result = (
                self.client.query
                .aggregate(collection_name)
                .with_meta_count()
                .do()
            )
            
            count = 0
            if "data" in result and "Aggregate" in result["data"]:
                count = result["data"]["Aggregate"][collection_name][0]["meta"]["count"]
            
            return {
                "name": collection_name,
                "description": schema.get("description", ""),
                "properties": schema.get("properties", []),
                "objects_count": count,
                "vectorizer": schema.get("vectorizer", "none"),
            }
            
        except Exception as e:
            raise VectorDBError(
                f"Failed to get Weaviate class info: {str(e)}",
                error_code=ErrorCodes.VECTOR_DB_CONNECTION_FAILED
            )


class StorageAgent(LoggerMixin):
    """Storage agent for vector database management."""
    
    def __init__(self):
        self.vector_databases = self._initialize_databases()
        self.default_db = self._get_default_database()
        self.default_collection = settings.vector_db.qdrant_collection_name
    
    def _initialize_databases(self) -> Dict[str, VectorDatabase]:
        """Initialize available vector databases."""
        databases = {}
        
        # Qdrant
        try:
            databases["qdrant"] = QdrantDatabase()
        except Exception as e:
            self.logger.warning(f"Failed to initialize Qdrant: {e}")
        
        # Weaviate
        try:
            databases["weaviate"] = WeaviateDatabase()
        except Exception as e:
            self.logger.warning(f"Failed to initialize Weaviate: {e}")
        
        return databases
    
    def _get_default_database(self) -> VectorDatabase:
        """Get the default vector database."""
        provider = settings.vector_db.default_provider
        
        if provider in self.vector_databases:
            return self.vector_databases[provider]
        
        # Fallback to first available database
        if self.vector_databases:
            return next(iter(self.vector_databases.values()))
        
        raise VectorDBError(
            "No vector databases available",
            error_code=ErrorCodes.VECTOR_DB_CONNECTION_FAILED
        )
    
    async def initialize_collection(
        self,
        collection_name: str,
        dimension: int,
        database_name: Optional[str] = None
    ) -> bool:
        """Initialize a collection in the vector database."""
        
        log_agent_action(
            agent_name="StorageAgent",
            action="initialize_collection",
            collection_name=collection_name,
            dimension=dimension
        )
        
        try:
            db = self.vector_databases.get(database_name) if database_name else self.default_db
            result = await db.create_collection(collection_name, dimension)
            
            self.logger.info(
                "Collection initialized",
                collection_name=collection_name,
                dimension=dimension,
                database=database_name or "default"
            )
            
            return result
            
        except Exception as e:
            log_error(e, {
                "agent": "StorageAgent",
                "collection_name": collection_name,
                "dimension": dimension
            })
            raise
    
    async def store_chunks(
        self,
        chunks: List[DocumentChunk],
        db_session: AsyncSession,
        collection_name: Optional[str] = None,
        database_name: Optional[str] = None
    ) -> bool:
        """Store chunks in both vector database and SQL database."""
        
        collection = collection_name or self.default_collection
        
        log_agent_action(
            agent_name="StorageAgent",
            action="store_chunks",
            num_chunks=len(chunks),
            collection_name=collection
        )
        
        try:
            # Store in vector database
            db = self.vector_databases.get(database_name) if database_name else self.default_db
            await db.insert_vectors(collection, chunks)
            
            # Store metadata in SQL database
            db_chunks = []
            for chunk in chunks:
                db_chunk = DBDocumentChunk(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    metadata=chunk.metadata,
                    created_at=chunk.created_at,
                    updated_at=chunk.updated_at
                )
                db_chunks.append(db_chunk)
            
            db_session.add_all(db_chunks)
            await db_session.commit()
            
            self.logger.info(
                "Chunks stored successfully",
                num_chunks=len(chunks),
                collection_name=collection
            )
            
            return True
            
        except Exception as e:
            await db_session.rollback()
            log_error(e, {
                "agent": "StorageAgent",
                "num_chunks": len(chunks),
                "collection_name": collection
            })
            raise
    
    async def search_similar_chunks(
        self,
        query_vector: List[float],
        search_query: SearchQuery,
        collection_name: Optional[str] = None,
        database_name: Optional[str] = None
    ) -> List[SearchResult]:
        """Search for similar chunks in the vector database."""
        
        collection = collection_name or self.default_collection
        
        log_agent_action(
            agent_name="StorageAgent",
            action="search_similar_chunks",
            collection_name=collection,
            limit=search_query.limit
        )
        
        try:
            db = self.vector_databases.get(database_name) if database_name else self.default_db
            results = await db.search_vectors(
                collection_name=collection,
                query_vector=query_vector,
                limit=search_query.limit,
                filters=search_query.filters,
                threshold=search_query.threshold
            )
            
            self.logger.info(
                "Search completed",
                collection_name=collection,
                num_results=len(results)
            )
            
            return results
            
        except Exception as e:
            log_error(e, {
                "agent": "StorageAgent",
                "collection_name": collection,
                "query": search_query.query
            })
            raise
    
    async def delete_document_chunks(
        self,
        document_id: UUID,
        db_session: AsyncSession,
        collection_name: Optional[str] = None,
        database_name: Optional[str] = None
    ) -> bool:
        """Delete all chunks for a document."""
        
        collection = collection_name or self.default_collection
        
        try:
            # Get chunk IDs from SQL database
            from sqlalchemy import select
            stmt = select(DBDocumentChunk.id).where(
                DBDocumentChunk.document_id == document_id
            )
            result = await db_session.execute(stmt)
            chunk_ids = [row[0] for row in result.fetchall()]
            
            if chunk_ids:
                # Delete from vector database
                db = self.vector_databases.get(database_name) if database_name else self.default_db
                await db.delete_vectors(collection, chunk_ids)
                
                # Delete from SQL database
                from sqlalchemy import delete
                stmt = delete(DBDocumentChunk).where(
                    DBDocumentChunk.document_id == document_id
                )
                await db_session.execute(stmt)
                await db_session.commit()
            
            self.logger.info(
                "Document chunks deleted",
                document_id=str(document_id),
                num_chunks=len(chunk_ids)
            )
            
            return True
            
        except Exception as e:
            await db_session.rollback()
            log_error(e, {
                "agent": "StorageAgent",
                "document_id": str(document_id)
            })
            raise
    
    async def get_database_stats(
        self,
        collection_name: Optional[str] = None,
        database_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get database statistics."""
        
        collection = collection_name or self.default_collection
        
        try:
            db = self.vector_databases.get(database_name) if database_name else self.default_db
            stats = await db.get_collection_info(collection)
            
            return stats
            
        except Exception as e:
            log_error(e, {
                "agent": "StorageAgent",
                "collection_name": collection
            })
            raise
