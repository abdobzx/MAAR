"""
Implémentation FAISS pour le vector store MAR
Optimisé pour la recherche locale haute performance
"""

import os
import json
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
import uuid
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from .base import BaseVectorStore
from .models import Document, DocumentChunk, QueryResult, SearchQuery, IngestionStatus, DocumentStatus

logger = logging.getLogger(__name__)


class FAISSVectorStore(BaseVectorStore):
    """
    Vector Store utilisant FAISS pour la recherche vectorielle locale
    Optimisé pour la performance et la scalabilité
    """
    
    def __init__(
        self,
        storage_path: str,
        embedding_dim: int = 384,  # Dimension par défaut pour sentence-transformers
        index_type: str = "flat",  # flat, ivf, hnsw
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le FAISS vector store
        
        Args:
            storage_path: Chemin de stockage des indices
            embedding_dim: Dimension des vecteurs d'embedding
            index_type: Type d'index FAISS (flat, ivf, hnsw)
            config: Configuration additionnelle
        """
        super().__init__("FAISS", config)
        
        if faiss is None:
            raise ImportError("FAISS n'est pas installé. Installez avec: pip install faiss-cpu")
        
        self.storage_path = storage_path
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        
        # Composants FAISS
        self.index = None
        self.id_to_chunk = {}  # Mapping ID -> DocumentChunk
        self.chunk_counter = 0
        
        # Métadonnées
        self.metadata_file = os.path.join(storage_path, "metadata.json")
        self.chunks_file = os.path.join(storage_path, "chunks.pkl")
        self.index_file = os.path.join(storage_path, "faiss.index")
        
        # Configuration
        self.metric = config.get("metric", "cosine") if config else "cosine"
        self.nprobe = config.get("nprobe", 10) if config else 10  # Pour IVF
        
        # Créer le répertoire de stockage
        os.makedirs(storage_path, exist_ok=True)
        
    async def initialize(self) -> bool:
        """
        Initialise l'index FAISS
        """
        try:
            logger.info(f"Initialisation du FAISS vector store: {self.storage_path}")
            
            # Charger l'index existant ou en créer un nouveau
            if os.path.exists(self.index_file):
                await self._load_index()
            else:
                await self._create_new_index()
            
            self.is_initialized = True
            logger.info(f"FAISS vector store initialisé avec {self.chunk_counter} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation FAISS: {e}")
            return False
    
    async def _create_new_index(self):
        """Crée un nouvel index FAISS"""
        if self.index_type == "flat":
            if self.metric == "cosine":
                self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner Product pour cosine
            else:
                self.index = faiss.IndexFlatL2(self.embedding_dim)
                
        elif self.index_type == "ivf":
            # Index IVF pour de gros datasets
            nlist = self.config.get("nlist", 100)
            quantizer = faiss.IndexFlatL2(self.embedding_dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, nlist)
            
        elif self.index_type == "hnsw":
            # Index HNSW pour recherche rapide
            m = self.config.get("hnsw_m", 16)
            self.index = faiss.IndexHNSWFlat(self.embedding_dim, m)
            
        else:
            raise ValueError(f"Type d'index non supporté: {self.index_type}")
        
        logger.info(f"Nouvel index FAISS créé: {self.index_type}")
    
    async def _load_index(self):
        """Charge un index existant"""
        try:
            # Charger l'index FAISS
            self.index = faiss.read_index(self.index_file)
            
            # Charger les métadonnées
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self.chunk_counter = metadata.get("chunk_counter", 0)
            
            # Charger les chunks
            if os.path.exists(self.chunks_file):
                with open(self.chunks_file, 'rb') as f:
                    self.id_to_chunk = pickle.load(f)
            
            logger.info(f"Index FAISS chargé: {self.chunk_counter} chunks")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'index: {e}")
            # Fallback: créer un nouvel index
            await self._create_new_index()
    
    async def _save_index(self):
        """Sauvegarde l'index et les métadonnées"""
        try:
            # Sauvegarder l'index FAISS
            faiss.write_index(self.index, self.index_file)
            
            # Sauvegarder les métadonnées
            metadata = {
                "chunk_counter": self.chunk_counter,
                "embedding_dim": self.embedding_dim,
                "index_type": self.index_type,
                "last_saved": datetime.now().isoformat()
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Sauvegarder les chunks
            with open(self.chunks_file, 'wb') as f:
                pickle.dump(self.id_to_chunk, f)
            
            logger.debug("Index FAISS sauvegardé")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
    
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
        Ajoute des chunks avec leurs embeddings à l'index
        """
        try:
            if not chunks:
                return True
            
            # Vérifier que tous les chunks ont des embeddings
            embeddings = []
            chunk_ids = []
            
            for chunk in chunks:
                if chunk.embedding is None:
                    # TODO: Générer l'embedding si manquant
                    logger.warning(f"Chunk {chunk.id} sans embedding - générer l'embedding")
                    continue
                
                embeddings.append(chunk.embedding)
                chunk_ids.append(self.chunk_counter)
                self.id_to_chunk[self.chunk_counter] = chunk
                self.chunk_counter += 1
            
            if not embeddings:
                logger.warning("Aucun chunk avec embedding valide")
                return False
            
            # Convertir en numpy array
            embeddings_np = np.array(embeddings).astype('float32')
            
            # Normaliser pour la similarité cosine si nécessaire
            if self.metric == "cosine":
                faiss.normalize_L2(embeddings_np)
            
            # Ajouter à l'index FAISS
            self.index.add(embeddings_np)
            
            # Sauvegarder
            await self._save_index()
            
            logger.info(f"Ajouté {len(embeddings)} chunks à l'index FAISS")
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
            # TODO: Générer l'embedding de la requête
            # Pour l'instant, simulation avec un vecteur random
            query_embedding = np.random.rand(self.embedding_dim).astype('float32')
            
            return await self.search_by_embedding(
                embedding=query_embedding.tolist(),
                max_results=query.max_results,
                min_score=query.min_score,
                filters=query.filters
            )
            
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
            if not self.is_initialized or self.index.ntotal == 0:
                logger.warning("Index vide ou non initialisé")
                return []
            
            # Préparer le vecteur de requête
            query_vector = np.array([embedding]).astype('float32')
            
            # Normaliser pour cosine similarity
            if self.metric == "cosine":
                faiss.normalize_L2(query_vector)
            
            # Configurer les paramètres de recherche
            if self.index_type == "ivf":
                self.index.nprobe = self.nprobe
            
            # Effectuer la recherche
            scores, indices = self.index.search(query_vector, max_results)
            
            # Construire les résultats
            results = []
            for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # Pas de résultat trouvé
                    continue
                
                # Convertir le score selon la métrique
                if self.metric == "cosine":
                    # FAISS retourne le produit scalaire, convertir en similarité cosine
                    similarity_score = float(score)
                    distance = 1.0 - similarity_score
                else:
                    # Distance L2
                    distance = float(score)
                    similarity_score = 1.0 / (1.0 + distance)
                
                if similarity_score < min_score:
                    continue
                
                # Récupérer le chunk
                chunk = self.id_to_chunk.get(int(idx))
                if chunk is None:
                    logger.warning(f"Chunk manquant pour l'index {idx}")
                    continue
                
                # Appliquer les filtres
                if filters and not self._apply_filters(chunk, filters):
                    continue
                
                result = QueryResult(
                    chunk=chunk,
                    score=similarity_score,
                    distance=distance,
                    rank=rank
                )
                results.append(result)
            
            # Trier par score décroissant
            results.sort(key=lambda x: x.score, reverse=True)
            
            logger.debug(f"Recherche FAISS: {len(results)} résultats trouvés")
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par embedding: {e}")
            return []
    
    def _apply_filters(
        self, 
        chunk: DocumentChunk, 
        filters: Dict[str, Any]
    ) -> bool:
        """
        Applique des filtres de métadonnées sur un chunk
        """
        try:
            for key, expected_value in filters.items():
                chunk_value = chunk.metadata.get(key)
                if chunk_value != expected_value:
                    return False
            return True
        except Exception:
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Supprime un document (pas trivial avec FAISS - reconstruction nécessaire)
        """
        try:
            # Identifier les chunks à supprimer
            chunks_to_remove = [
                idx for idx, chunk in self.id_to_chunk.items()
                if chunk.document_id == document_id
            ]
            
            if not chunks_to_remove:
                logger.warning(f"Aucun chunk trouvé pour le document {document_id}")
                return True
            
            # Supprimer des métadonnées
            for idx in chunks_to_remove:
                del self.id_to_chunk[idx]
            
            # Reconstruire l'index (limitation de FAISS)
            await self._rebuild_index()
            
            logger.info(f"Document {document_id} supprimé ({len(chunks_to_remove)} chunks)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du document: {e}")
            return False
    
    async def _rebuild_index(self):
        """
        Reconstruit l'index FAISS après suppression
        """
        try:
            # Créer un nouvel index
            await self._create_new_index()
            
            # Réajouter tous les chunks restants
            if self.id_to_chunk:
                embeddings = []
                for chunk in self.id_to_chunk.values():
                    if chunk.embedding:
                        embeddings.append(chunk.embedding)
                
                if embeddings:
                    embeddings_np = np.array(embeddings).astype('float32')
                    if self.metric == "cosine":
                        faiss.normalize_L2(embeddings_np)
                    self.index.add(embeddings_np)
            
            # Sauvegarder
            await self._save_index()
            
            logger.info("Index FAISS reconstruit")
            
        except Exception as e:
            logger.error(f"Erreur lors de la reconstruction de l'index: {e}")
    
    async def delete_chunks(self, chunk_ids: List[str]) -> bool:
        """
        Supprime des chunks spécifiques
        """
        # Pour FAISS, nécessite une reconstruction
        try:
            removed_count = 0
            for chunk_id in chunk_ids:
                # Trouver l'index du chunk
                for idx, chunk in self.id_to_chunk.items():
                    if chunk.id == chunk_id:
                        del self.id_to_chunk[idx]
                        removed_count += 1
                        break
            
            if removed_count > 0:
                await self._rebuild_index()
            
            logger.info(f"Supprimé {removed_count} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des chunks: {e}")
            return False
    
    async def get_document_count(self) -> int:
        """
        Retourne le nombre de documents uniques
        """
        document_ids = set()
        for chunk in self.id_to_chunk.values():
            document_ids.add(chunk.document_id)
        return len(document_ids)
    
    async def get_chunk_count(self) -> int:
        """
        Retourne le nombre total de chunks
        """
        return len(self.id_to_chunk)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du vector store
        """
        return {
            "type": "FAISS",
            "index_type": self.index_type,
            "embedding_dim": self.embedding_dim,
            "total_chunks": await self.get_chunk_count(),
            "total_documents": await self.get_document_count(),
            "index_size": self.index.ntotal if self.index else 0,
            "metric": self.metric,
            "storage_path": self.storage_path,
            "is_trained": getattr(self.index, 'is_trained', True)
        }
    
    async def cleanup(self):
        """
        Nettoie les ressources
        """
        try:
            if self.index:
                await self._save_index()
            logger.info("FAISS vector store nettoyé")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
