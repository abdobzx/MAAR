"""
Classe de base abstraite pour les vector stores
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import logging
from .models import Document, DocumentChunk, QueryResult, SearchQuery, IngestionStatus

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """
    Interface abstraite pour les différents types de vector stores
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le vector store
        
        Args:
            name: Nom du vector store
            config: Configuration spécifique
        """
        self.name = name
        self.config = config or {}
        self.is_initialized = False
        logger.info(f"Vector store {name} créé")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialise le vector store
        
        Returns:
            True si l'initialisation a réussi
        """
        pass
    
    @abstractmethod
    async def add_documents(
        self, 
        documents: List[Document]
    ) -> IngestionStatus:
        """
        Ajoute des documents au vector store
        
        Args:
            documents: Liste des documents à ajouter
            
        Returns:
            Statut de l'ingestion
        """
        pass
    
    @abstractmethod
    async def add_chunks(
        self,
        chunks: List[DocumentChunk]
    ) -> bool:
        """
        Ajoute des chunks pré-traités au vector store
        
        Args:
            chunks: Liste des chunks à ajouter
            
        Returns:
            True si l'ajout a réussi
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: SearchQuery
    ) -> List[QueryResult]:
        """
        Effectue une recherche vectorielle
        
        Args:
            query: Requête de recherche
            
        Returns:
            Liste des résultats triés par pertinence
        """
        pass
    
    @abstractmethod
    async def search_by_embedding(
        self,
        embedding: List[float],
        max_results: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[QueryResult]:
        """
        Recherche par vecteur d'embedding directement
        
        Args:
            embedding: Vecteur d'embedding
            max_results: Nombre maximum de résultats
            min_score: Score minimum
            filters: Filtres optionnels
            
        Returns:
            Liste des résultats
        """
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """
        Supprime un document et tous ses chunks
        
        Args:
            document_id: ID du document à supprimer
            
        Returns:
            True si la suppression a réussi
        """
        pass
    
    @abstractmethod
    async def delete_chunks(self, chunk_ids: List[str]) -> bool:
        """
        Supprime des chunks spécifiques
        
        Args:
            chunk_ids: IDs des chunks à supprimer
            
        Returns:
            True si la suppression a réussi
        """
        pass
    
    @abstractmethod
    async def get_document_count(self) -> int:
        """
        Retourne le nombre total de documents
        """
        pass
    
    @abstractmethod
    async def get_chunk_count(self) -> int:
        """
        Retourne le nombre total de chunks
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques du vector store
        """
        pass
    
    @abstractmethod
    async def cleanup(self):
        """
        Nettoie les ressources du vector store
        """
        pass
    
    # Méthodes utilitaires communes
    
    def is_ready(self) -> bool:
        """Vérifie si le vector store est prêt"""
        return self.is_initialized
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Vérifie la santé du vector store
        
        Returns:
            Dictionnaire avec le statut de santé
        """
        try:
            stats = await self.get_stats()
            return {
                "status": "healthy",
                "initialized": self.is_initialized,
                "name": self.name,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return {
                "status": "unhealthy",
                "initialized": self.is_initialized,
                "name": self.name,
                "error": str(e)
            }
