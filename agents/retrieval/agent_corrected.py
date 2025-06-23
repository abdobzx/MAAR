"""
Agent de récupération pour le système RAG Enterprise.
Version corrigée pour production - sans dépendances manquantes.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from core.config import settings
from core.exceptions import LLMError, VectorDBError, ErrorCodes, AgentError
from core.logging import LoggerMixin, log_agent_action, log_error
from core.models import SearchQuery, SearchResult, SearchResponse, SearchType
from database.models import DocumentChunk as DBDocumentChunk, Document as DBDocument
from database.manager import DatabaseManager

# Imports optionnels avec fallback
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False


class SimpleBM25:
    """Implémentation simple de BM25 sans dépendances externes."""
    
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / self.corpus_size if self.corpus_size > 0 else 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        
        if self.corpus_size > 0:
            self._initialize()
    
    def _initialize(self):
        """Initialise les structures de données BM25."""
        nd = {}  # Nombre de documents contenant chaque terme
        
        for document in self.corpus:
            self.doc_len.append(len(document))
            frequencies = {}
            
            for word in document:
                frequencies[word] = frequencies.get(word, 0) + 1
                
            self.doc_freqs.append(frequencies)
            
            for word in frequencies.keys():
                nd[word] = nd.get(word, 0) + 1
        
        # Calcul de l'IDF
        for word, freq in nd.items():
            self.idf[word] = max(0.01, len(self.corpus) - freq + 0.5) / (freq + 0.5)
    
    def get_scores(self, query):
        """Calcule les scores BM25 pour une requête."""
        if not self.corpus:
            return []
            
        scores = []
        
        for i, doc in enumerate(self.corpus):
            score = 0
            doc_freqs = self.doc_freqs[i]
            
            for word in query:
                if word in doc_freqs:
                    freq = doc_freqs[word]
                    score += self.idf.get(word, 0) * (freq * (self.k1 + 1)) / (
                        freq + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                    )
            
            scores.append(score)
        
        return scores


class KeywordSearchEngine:
    """Moteur de recherche par mots-clés basé sur BM25."""
    
    def __init__(self):
        self.tokenized_corpus = []
        self.bm25 = None
        self.corpus_metadata = []
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenise le texte pour BM25."""
        text = text.lower()
        # Supprime la ponctuation et sépare
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return [token for token in tokens if len(token) > 2]
    
    async def build_index(self, chunks: List[DBDocumentChunk]) -> None:
        """Construit l'index BM25 à partir des chunks de documents."""
        self.tokenized_corpus = []
        self.corpus_metadata = []
        
        for chunk in chunks:
            tokens = self._tokenize(chunk.content)
            self.tokenized_corpus.append(tokens)
            self.corpus_metadata.append({
                'chunk_id': chunk.id,
                'document_id': chunk.document_id,
                'content': chunk.content,
                'metadata': chunk.metadata
            })
        
        # Utilise BM25Okapi si disponible, sinon SimpleBM25
        if BM25_AVAILABLE and self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        elif self.tokenized_corpus:
            self.bm25 = SimpleBM25(self.tokenized_corpus)
        else:
            self.bm25 = None
    
    async def search(self, query: str, limit: int = 10) -> List[Tuple[int, float]]:
        """Effectue une recherche par mots-clés."""
        if not self.bm25 or not self.tokenized_corpus:
            return []
        
        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []
        
        scores = self.bm25.get_scores(tokenized_query)
        
        # Trie par score décroissant et retourne les indices et scores
        indexed_scores = [(i, score) for i, score in enumerate(scores)]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        return indexed_scores[:limit]


class HybridSearchRanker:
    """Combinateur pour la recherche hybride."""
    
    def __init__(self, semantic_weight: float = 0.7, keyword_weight: float = 0.3):
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
    
    def combine_scores(
        self, 
        semantic_results: List[Tuple[int, float]], 
        keyword_results: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        """Combine les scores sémantiques et de mots-clés."""
        # Normalise les scores sur [0, 1]
        semantic_scores = self._normalize_scores([score for _, score in semantic_results])
        keyword_scores = self._normalize_scores([score for _, score in keyword_results])
        
        # Crée des dictionnaires pour un accès rapide
        semantic_dict = {idx: score for (idx, _), score in zip(semantic_results, semantic_scores)}
        keyword_dict = {idx: score for (idx, _), score in zip(keyword_results, keyword_scores)}
        
        # Combine les scores
        all_indices = set(semantic_dict.keys()) | set(keyword_dict.keys())
        combined_results = []
        
        for idx in all_indices:
            semantic_score = semantic_dict.get(idx, 0.0)
            keyword_score = keyword_dict.get(idx, 0.0)
            
            combined_score = (
                self.semantic_weight * semantic_score + 
                self.keyword_weight * keyword_score
            )
            
            combined_results.append((idx, combined_score))
        
        # Trie par score combiné décroissant
        combined_results.sort(key=lambda x: x[1], reverse=True)
        return combined_results
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """Normalise les scores sur [0, 1]."""
        if not scores:
            return []
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(score - min_score) / (max_score - min_score) for score in scores]


class RetrievalAgent(LoggerMixin):
    """
    Agent de récupération pour le système RAG Enterprise.
    Version corrigée pour la production.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialise l'agent de récupération."""
        super().__init__()
        self.config = config or {}
        self.settings = settings
        
        # Composants de recherche
        self.keyword_engine = KeywordSearchEngine()
        self.hybrid_ranker = HybridSearchRanker()
        
        # Gestionnaire de base de données
        self.db_manager = DatabaseManager()
        
        # Cache pour les chunks
        self._chunks_cache = None
        self._cache_timestamp = None
        
        # Configuration des seuils
        self.min_score_threshold = self.config.get("min_score_threshold", 0.3)
        self.rerank_enabled = self.config.get("rerank_enabled", True)
        
        self.logger.info("RetrievalAgent initialisé avec succès")
    
    async def initialize(self):
        """Initialise l'agent et ses dépendances."""
        try:
            # Initialisation du gestionnaire de base de données
            await self.db_manager.initialize()
            
            # Construction de l'index de recherche par mots-clés
            await self._build_search_index()
            
            self.logger.info("Agent de récupération initialisé avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            raise AgentError(f"Échec de l'initialisation: {e}")
    
    async def _build_search_index(self):
        """Construit l'index de recherche."""
        try:
            # Récupère tous les chunks depuis la base de données
            async with self.db_manager.get_session() as session:
                chunks = await self._get_all_chunks(session)
                
            # Construction de l'index des mots-clés
            await self.keyword_engine.build_index(chunks)
            
            # Cache les chunks pour éviter les requêtes répétées
            self._chunks_cache = chunks
            self._cache_timestamp = asyncio.get_event_loop().time()
            
            self.logger.info(f"Index de recherche construit avec {len(chunks)} chunks")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la construction de l'index: {e}")
            raise
    
    async def _get_all_chunks(self, session) -> List[DBDocumentChunk]:
        """Récupère tous les chunks de documents depuis la base de données."""
        try:
            # Utilise une méthode simple si SQLAlchemy n'est pas disponible
            if hasattr(session, 'query'):
                chunks = session.query(DBDocumentChunk).all()
            else:
                # Fallback pour les sessions async
                chunks = await session.execute(
                    "SELECT * FROM document_chunks"
                )
                chunks = chunks.fetchall()
                
            return chunks if chunks else []
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des chunks: {e}")
            return []
    
    @log_agent_action("search")
    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.HYBRID,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7,
        rerank: bool = True
    ) -> List[SearchResult]:
        """
        Effectue une recherche dans la base de documents.
        
        Args:
            query: Requête de recherche
            search_type: Type de recherche (semantic, keyword, hybrid)
            user_id: ID de l'utilisateur
            organization_id: ID de l'organisation
            limit: Nombre maximum de résultats
            threshold: Seuil de pertinence
            rerank: Activer le re-ranking
        
        Returns:
            Liste des résultats de recherche
        """
        try:
            self.logger.info(f"Recherche: '{query}' (type: {search_type}, limit: {limit})")
            
            # Validation de la requête
            if not query or not query.strip():
                return []
            
            # Vérifie si l'index doit être reconstruit
            await self._refresh_index_if_needed()
            
            # Effectue la recherche selon le type
            if search_type == SearchType.KEYWORD:
                results = await self._keyword_search(query, limit)
            elif search_type == SearchType.SEMANTIC:
                results = await self._semantic_search(query, limit)
            else:  # HYBRID
                results = await self._hybrid_search(query, limit)
            
            # Filtre par seuil de pertinence
            results = [r for r in results if r.score >= threshold]
            
            # Re-ranking si activé
            if rerank and self.rerank_enabled and len(results) > 1:
                results = await self._rerank_results(query, results)
            
            self.logger.info(f"Recherche terminée: {len(results)} résultats trouvés")
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche: {e}")
            raise AgentError(f"Échec de la recherche: {e}")
    
    async def _refresh_index_if_needed(self):
        """Rafraîchit l'index si nécessaire."""
        # Rafraîchit l'index toutes les heures
        current_time = asyncio.get_event_loop().time()
        if (self._cache_timestamp is None or 
            current_time - self._cache_timestamp > 3600):
            await self._build_search_index()
    
    async def _keyword_search(self, query: str, limit: int) -> List[SearchResult]:
        """Effectue une recherche par mots-clés."""
        try:
            keyword_results = await self.keyword_engine.search(query, limit * 2)
            
            search_results = []
            for idx, score in keyword_results:
                if idx < len(self._chunks_cache):
                    chunk = self._chunks_cache[idx]
                    metadata = self.keyword_engine.corpus_metadata[idx]
                    
                    search_result = SearchResult(
                        chunk_id=metadata['chunk_id'],
                        document_id=metadata['document_id'],
                        content=metadata['content'],
                        score=float(score),
                        metadata=metadata.get('metadata', {})
                    )
                    search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche par mots-clés: {e}")
            return []
    
    async def _semantic_search(self, query: str, limit: int) -> List[SearchResult]:
        """Effectue une recherche sémantique."""
        try:
            # Tente d'utiliser l'agent de vectorisation pour la recherche sémantique
            try:
                from agents.vectorization.agent import VectorizationAgent
                
                vectorization_agent = VectorizationAgent()
                await vectorization_agent.initialize()
                
                # Recherche vectorielle
                semantic_results = await vectorization_agent.search_similar(
                    query=query,
                    limit=limit * 2
                )
                
                return semantic_results
                
            except Exception as e:
                self.logger.warning(f"Recherche sémantique indisponible: {e}")
                # Fallback vers recherche par mots-clés
                return await self._keyword_search(query, limit)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche sémantique: {e}")
            return []
    
    async def _hybrid_search(self, query: str, limit: int) -> List[SearchResult]:
        """Effectue une recherche hybride (sémantique + mots-clés)."""
        try:
            # Recherche par mots-clés
            keyword_results = await self.keyword_engine.search(query, limit * 2)
            
            # Recherche sémantique
            semantic_results_raw = await self._semantic_search(query, limit * 2)
            
            # Conversion des résultats sémantiques en format compatible
            semantic_results = []
            for i, result in enumerate(semantic_results_raw):
                # Trouve l'index correspondant dans le cache
                for j, cached_chunk in enumerate(self._chunks_cache):
                    if cached_chunk.id == result.chunk_id:
                        semantic_results.append((j, result.score))
                        break
            
            # Combine les scores
            combined_results = self.hybrid_ranker.combine_scores(
                semantic_results, keyword_results
            )
            
            # Convertit en SearchResult
            search_results = []
            for idx, score in combined_results:
                if idx < len(self._chunks_cache):
                    chunk = self._chunks_cache[idx]
                    metadata = self.keyword_engine.corpus_metadata[idx]
                    
                    search_result = SearchResult(
                        chunk_id=metadata['chunk_id'],
                        document_id=metadata['document_id'],
                        content=metadata['content'],
                        score=float(score),
                        metadata=metadata.get('metadata', {})
                    )
                    search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche hybride: {e}")
            # Fallback vers recherche par mots-clés
            return await self._keyword_search(query, limit)
    
    async def _rerank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Re-classe les résultats pour améliorer la pertinence."""
        try:
            # Re-ranking simple basé sur la longueur et la position des mots-clés
            query_words = set(query.lower().split())
            
            def calculate_rerank_score(result: SearchResult) -> float:
                content_lower = result.content.lower()
                
                # Score basé sur la fréquence des mots-clés de la requête
                keyword_count = sum(1 for word in query_words if word in content_lower)
                keyword_density = keyword_count / len(query_words) if query_words else 0
                
                # Score basé sur la position des mots-clés (plus tôt = mieux)
                position_score = 1.0
                for word in query_words:
                    pos = content_lower.find(word)
                    if pos != -1:
                        # Score plus élevé si le mot apparaît plus tôt
                        position_score *= max(0.1, 1 - (pos / len(content_lower)))
                
                # Score combiné
                combined_score = (
                    0.5 * result.score +  # Score original
                    0.3 * keyword_density +  # Densité des mots-clés
                    0.2 * position_score  # Position des mots-clés
                )
                
                return combined_score
            
            # Recalcule les scores et trie
            for result in results:
                result.score = calculate_rerank_score(result)
            
            results.sort(key=lambda x: x.score, reverse=True)
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors du re-ranking: {e}")
            return results
    
    async def get_document_chunks(self, document_id: UUID, limit: int = 50) -> List[SearchResult]:
        """Récupère tous les chunks d'un document spécifique."""
        try:
            async with self.db_manager.get_session() as session:
                chunks = await self._get_chunks_by_document(session, document_id, limit)
                
            search_results = []
            for chunk in chunks:
                search_result = SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=1.0,  # Score maximal pour tous les chunks du document
                    metadata=chunk.metadata or {}
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des chunks: {e}")
            return []
    
    async def _get_chunks_by_document(self, session, document_id: UUID, limit: int) -> List[DBDocumentChunk]:
        """Récupère les chunks d'un document depuis la base de données."""
        try:
            if hasattr(session, 'query'):
                chunks = session.query(DBDocumentChunk).filter(
                    DBDocumentChunk.document_id == document_id
                ).limit(limit).all()
            else:
                # Fallback pour les sessions async
                chunks = await session.execute(
                    f"SELECT * FROM document_chunks WHERE document_id = '{document_id}' LIMIT {limit}"
                )
                chunks = chunks.fetchall()
                
            return chunks if chunks else []
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des chunks du document: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé de l'agent de récupération."""
        try:
            status = {
                "status": "healthy",
                "search_index_size": len(self._chunks_cache) if self._chunks_cache else 0,
                "keyword_search": self.keyword_engine.bm25 is not None,
                "database_connection": await self.db_manager.health_check(),
                "dependencies": {
                    "numpy": NUMPY_AVAILABLE,
                    "rank_bm25": BM25_AVAILABLE,
                    "cohere": COHERE_AVAILABLE
                }
            }
            
            return status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def rebuild_index(self) -> bool:
        """Reconstruit l'index de recherche."""
        try:
            await self._build_search_index()
            self.logger.info("Index de recherche reconstruit avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la reconstruction de l'index: {e}")
            return False
