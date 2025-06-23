"""
Implémentation Chroma pour le vector store MAR
Alternative moderne à FAISS avec métadonnées natives
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from .base import BaseVectorStore
from .models import Document, DocumentChunk, QueryResult, SearchQuery, IngestionStatus, DocumentStatus

logger = logging.getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """
    Vector Store utilisant ChromaDB
    Avantages: métadonnées natives, requêtes complexes, interface simple
    """
    
    def __init__(
        self,
        storage_path: str,
        collection_name: str = "mar_documents",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le Chroma vector store
        
        Args:
            storage_path: Chemin de stockage de la base
            collection_name: Nom de la collection
            config: Configuration additionnelle
        """
        super().__init__("Chroma", config)
        
        if chromadb is None:
            raise ImportError("ChromaDB n'est pas installé. Installez avec: pip install chromadb")
        
        self.storage_path = storage_path
        self.collection_name = collection_name
        
        # Composants Chroma
        self.client = None
        self.collection = None
        
        # Configuration
        self.embedding_function = config.get("embedding_function") if config else None
        self.distance_metric = config.get("distance_metric", "cosine") if config else "cosine"
        
        # Créer le répertoire de stockage
        os.makedirs(storage_path, exist_ok=True)
    
    async def initialize(self) -> bool:
        """
        Initialise le client ChromaDB et la collection
        """
        try:
            logger.info(f"Initialisation du Chroma vector store: {self.storage_path}")
            
            # Créer le client persistant
            settings = Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.storage_path,
                anonymized_telemetry=False
            )
            
            self.client = chromadb.Client(settings)
            
            # Créer ou récupérer la collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Collection existante chargée: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"distance_metric": self.distance_metric}
                )
                logger.info(f"Nouvelle collection créée: {self.collection_name}")
            
            self.is_initialized = True
            
            # Afficher les stats
            count = self.collection.count()
            logger.info(f"Chroma vector store initialisé avec {count} chunks")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation Chroma: {e}")
            return False
    
    async def add_documents(
        self, 
        documents: List[Document]
    ) -> IngestionStatus:
        """
        Ajoute des documents après les avoir découpés en chunks
        """
        job_id = str(uuid.uuid4())
        status = IngestionStatus(
            job_id=job_id,
            status=DocumentStatus.PROCESSING,
            total_documents=len(documents)
        )
        
        try:
            from .ingestion import DocumentIngestion
            ingestion = DocumentIngestion()
            
            all_chunks = []
            for doc in documents:
                chunks = await ingestion.chunk_document(doc)
                all_chunks.extend(chunks)
                status.processed_documents += 1
            
            # Ajouter les chunks au vector store
            success = await self.add_chunks(all_chunks)
            
            if success:
                status.status = DocumentStatus.INDEXED
            else:
                status.status = DocumentStatus.FAILED
                status.error_message = "Échec de l'ajout des chunks"
            
            status.end_time = datetime.now()
            return status
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des documents: {e}")
            status.status = DocumentStatus.FAILED
            status.error_message = str(e)
            status.end_time = datetime.now()
            return status
    
    async def add_chunks(
        self,
        chunks: List[DocumentChunk]
    ) -> bool:
        """
        Ajoute des chunks à la collection Chroma
        """
        try:
            if not chunks:
                return True
            
            # Préparer les données pour Chroma
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for chunk in chunks:
                ids.append(chunk.id)
                documents.append(chunk.content)
                
                # Métadonnées pour Chroma
                metadata = {
                    **chunk.metadata,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "added_at": datetime.now().isoformat()
                }
                metadatas.append(metadata)
                
                # Embeddings (optionnel si fonction d'embedding configurée)
                if chunk.embedding:
                    embeddings.append(chunk.embedding)
            
            # Ajouter à la collection
            if embeddings:
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            else:
                # Laisser Chroma générer les embeddings
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            logger.info(f"Ajouté {len(chunks)} chunks à la collection Chroma")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des chunks: {e}")
            return False
    
    async def search(
        self,
        query: SearchQuery
    ) -> List[QueryResult]:
        """
        Effectue une recherche vectorielle avec la requête textuelle
        """
        try:
            # Préparer les filtres Where pour Chroma
            where_filter = None
            if query.filters:
                where_filter = self._build_where_filter(query.filters)
            
            # Effectuer la recherche
            results = self.collection.query(
                query_texts=[query.query],
                n_results=query.max_results,
                where=where_filter,
                include=["documents", "metadatas", "distances", "embeddings"]
            )
            
            # Convertir les résultats
            query_results = []
            
            if results["ids"] and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    metadata = results["metadatas"][0][i]
                    document_text = results["documents"][0][i]
                    
                    # Calculer le score de similarité
                    similarity_score = 1.0 - distance if distance <= 1.0 else 1.0 / (1.0 + distance)
                    
                    # Filtrer par score minimum
                    if similarity_score < query.min_score:
                        continue
                    
                    # Reconstruire le DocumentChunk
                    chunk = DocumentChunk(
                        id=chunk_id,
                        document_id=metadata.get("document_id", "unknown"),
                        content=document_text,
                        chunk_index=metadata.get("chunk_index", 0),
                        start_char=metadata.get("start_char", 0),
                        end_char=metadata.get("end_char", len(document_text)),
                        metadata=metadata
                    )
                    
                    result = QueryResult(
                        chunk=chunk,
                        score=similarity_score,
                        distance=distance,
                        rank=i
                    )
                    query_results.append(result)
            
            # Trier par score décroissant
            query_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.debug(f"Recherche Chroma: {len(query_results)} résultats trouvés")
            return query_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return []
    
    async def search_by_embedding(
        self,
        embedding: List[float],
        max_results: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[QueryResult]:
        """
        Recherche par vecteur d'embedding
        """
        try:
            # Préparer les filtres
            where_filter = None
            if filters:
                where_filter = self._build_where_filter(filters)
            
            # Effectuer la recherche
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=max_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convertir les résultats (même logique que search)
            query_results = []
            
            if results["ids"] and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    metadata = results["metadatas"][0][i]
                    document_text = results["documents"][0][i]
                    
                    similarity_score = 1.0 - distance if distance <= 1.0 else 1.0 / (1.0 + distance)
                    
                    if similarity_score < min_score:
                        continue
                    
                    chunk = DocumentChunk(
                        id=chunk_id,
                        document_id=metadata.get("document_id", "unknown"),
                        content=document_text,
                        chunk_index=metadata.get("chunk_index", 0),
                        start_char=metadata.get("start_char", 0),
                        end_char=metadata.get("end_char", len(document_text)),
                        metadata=metadata
                    )
                    
                    result = QueryResult(
                        chunk=chunk,
                        score=similarity_score,
                        distance=distance,
                        rank=i
                    )
                    query_results.append(result)
            
            query_results.sort(key=lambda x: x.score, reverse=True)
            return query_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par embedding: {e}")
            return []
    
    def _build_where_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construit un filtre Where pour ChromaDB
        """
        where_filter = {}
        
        for key, value in filters.items():
            if isinstance(value, (str, int, float, bool)):
                where_filter[key] = {"$eq": value}
            elif isinstance(value, list):
                where_filter[key] = {"$in": value}
            elif isinstance(value, dict):
                # Support pour des opérateurs complexes
                where_filter[key] = value
        
        return where_filter
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Supprime un document et tous ses chunks
        """
        try:
            # Trouver tous les chunks du document
            results = self.collection.get(
                where={"document_id": {"$eq": document_id}},
                include=["metadatas"]
            )
            
            if results["ids"]:
                # Supprimer tous les chunks
                self.collection.delete(ids=results["ids"])
                logger.info(f"Document {document_id} supprimé ({len(results['ids'])} chunks)")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du document: {e}")
            return False
    
    async def delete_chunks(self, chunk_ids: List[str]) -> bool:
        """
        Supprime des chunks spécifiques
        """
        try:
            self.collection.delete(ids=chunk_ids)
            logger.info(f"Supprimé {len(chunk_ids)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des chunks: {e}")
            return False
    
    async def get_document_count(self) -> int:
        """
        Retourne le nombre de documents uniques
        """
        try:
            # Requête pour obtenir tous les document_ids uniques
            results = self.collection.get(include=["metadatas"])
            
            document_ids = set()
            for metadata in results["metadatas"]:
                if "document_id" in metadata:
                    document_ids.add(metadata["document_id"])
            
            return len(document_ids)
            
        except Exception as e:
            logger.error(f"Erreur lors du comptage des documents: {e}")
            return 0
    
    async def get_chunk_count(self) -> int:
        """
        Retourne le nombre total de chunks
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Erreur lors du comptage des chunks: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du vector store
        """
        try:
            chunk_count = await self.get_chunk_count()
            document_count = await self.get_document_count()
            
            return {
                "type": "Chroma",
                "collection_name": self.collection_name,
                "total_chunks": chunk_count,
                "total_documents": document_count,
                "distance_metric": self.distance_metric,
                "storage_path": self.storage_path,
                "embedding_function": str(self.embedding_function) if self.embedding_function else None
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return {
                "type": "Chroma",
                "collection_name": self.collection_name,
                "error": str(e)
            }
    
    async def cleanup(self):
        """
        Nettoie les ressources
        """
        try:
            # Chroma gère automatiquement la persistance
            logger.info("Chroma vector store nettoyé")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
