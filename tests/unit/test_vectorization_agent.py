"""
Tests unitaires pour l'agent de vectorisation.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

from agents.vectorization.agent import VectorizationAgent
from core.models import EmbeddingRequest, EmbeddingResult, VectorSearchRequest
from core.exceptions import VectorizationError, EmbeddingError


class TestVectorizationAgent:
    """Tests pour l'agent de vectorisation."""
    
    @pytest.fixture
    async def vectorization_agent(self, db_session, mock_qdrant_client, mock_openai_client):
        """Instance de l'agent de vectorisation pour les tests."""
        with patch('agents.vectorization.agent.QdrantClient', return_value=mock_qdrant_client), \
             patch('agents.vectorization.agent.OpenAI', return_value=mock_openai_client):
            agent = VectorizationAgent(db_session=db_session)
            yield agent
    
    async def test_generate_embeddings_success(self, vectorization_agent, mock_openai_client):
        """Test de génération réussie d'embeddings."""
        
        # Mock de la réponse OpenAI
        mock_openai_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3] * 512)  # 1536 dimensions
        ]
        
        texts = ["Premier texte à vectoriser", "Deuxième texte à vectoriser"]
        
        embeddings = await vectorization_agent.generate_embeddings(texts)
        
        assert len(embeddings) == 2
        assert all(len(emb) == 1536 for emb in embeddings)
        assert all(isinstance(emb, list) for emb in embeddings)
    
    async def test_generate_embeddings_batch(self, vectorization_agent, mock_openai_client):
        """Test de génération d'embeddings en lot."""
        
        # Mock de la réponse OpenAI pour un lot
        mock_openai_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1] * 1536) for _ in range(100)
        ]
        
        # Générer 100 textes
        texts = [f"Texte numéro {i}" for i in range(100)]
        
        embeddings = await vectorization_agent.generate_embeddings(texts)
        
        assert len(embeddings) == 100
        assert all(len(emb) == 1536 for emb in embeddings)
    
    async def test_store_vectors_success(self, vectorization_agent, mock_qdrant_client):
        """Test du stockage réussi de vecteurs."""
        
        vectors = [
            {
                "id": "doc-1",
                "vector": [0.1] * 1536,
                "payload": {"content": "Premier document", "source": "test1.pdf"}
            },
            {
                "id": "doc-2", 
                "vector": [0.2] * 1536,
                "payload": {"content": "Deuxième document", "source": "test2.pdf"}
            }
        ]
        
        result = await vectorization_agent.store_vectors(vectors, "test-collection")
        
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()
    
    async def test_search_similar_vectors(self, vectorization_agent, mock_qdrant_client, mock_vector_search_results):
        """Test de recherche de vecteurs similaires."""
        
        # Mock de la réponse Qdrant
        mock_qdrant_client.search.return_value = [
            MagicMock(
                id="doc-1", 
                score=0.95, 
                payload={"content": "Document pertinent 1", "source": "test1.pdf"}
            ),
            MagicMock(
                id="doc-2",
                score=0.85,
                payload={"content": "Document pertinent 2", "source": "test2.pdf"}
            )
        ]
        
        query_vector = [0.1] * 1536
        
        results = await vectorization_agent.search_similar_vectors(
            query_vector, 
            collection_name="test-collection",
            top_k=5
        )
        
        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"]  # Trié par score
        assert all("content" in result["payload"] for result in results)
    
    async def test_create_collection(self, vectorization_agent, mock_qdrant_client):
        """Test de création d'une collection."""
        
        collection_name = "new-test-collection"
        vector_size = 1536
        
        result = await vectorization_agent.create_collection(collection_name, vector_size)
        
        assert result is True
        mock_qdrant_client.create_collection.assert_called_once()
    
    async def test_delete_collection(self, vectorization_agent, mock_qdrant_client):
        """Test de suppression d'une collection."""
        
        collection_name = "test-collection-to-delete"
        
        result = await vectorization_agent.delete_collection(collection_name)
        
        assert result is True
        mock_qdrant_client.delete_collection.assert_called_once_with(collection_name)
    
    async def test_update_vector(self, vectorization_agent, mock_qdrant_client):
        """Test de mise à jour d'un vecteur."""
        
        vector_id = "doc-123"
        new_vector = [0.5] * 1536
        new_payload = {"content": "Contenu mis à jour", "updated": True}
        
        result = await vectorization_agent.update_vector(
            vector_id, 
            new_vector, 
            new_payload,
            "test-collection"
        )
        
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()
    
    async def test_delete_vector(self, vectorization_agent, mock_qdrant_client):
        """Test de suppression d'un vecteur."""
        
        vector_id = "doc-to-delete"
        collection_name = "test-collection"
        
        result = await vectorization_agent.delete_vector(vector_id, collection_name)
        
        assert result is True
        mock_qdrant_client.delete.assert_called_once()
    
    async def test_embedding_error_handling(self, vectorization_agent, mock_openai_client):
        """Test de gestion d'erreur lors de la génération d'embeddings."""
        
        # Simuler une erreur OpenAI
        mock_openai_client.embeddings.create.side_effect = Exception("Erreur API OpenAI")
        
        texts = ["Texte qui va causer une erreur"]
        
        with pytest.raises(EmbeddingError):
            await vectorization_agent.generate_embeddings(texts)
    
    async def test_vector_search_with_filters(self, vectorization_agent, mock_qdrant_client):
        """Test de recherche vectorielle avec filtres."""
        
        # Mock avec filtres
        mock_qdrant_client.search.return_value = [
            MagicMock(
                id="doc-1",
                score=0.90,
                payload={"content": "Document filtré", "category": "policy"}
            )
        ]
        
        query_vector = [0.1] * 1536
        filters = {"category": "policy"}
        
        results = await vectorization_agent.search_similar_vectors(
            query_vector,
            collection_name="test-collection",
            top_k=5,
            filters=filters
        )
        
        assert len(results) == 1
        assert results[0]["payload"]["category"] == "policy"
    
    async def test_batch_vector_operations(self, vectorization_agent, mock_qdrant_client):
        """Test d'opérations vectorielles en lot."""
        
        # Préparer un lot de vecteurs
        vectors = []
        for i in range(50):
            vectors.append({
                "id": f"batch-doc-{i}",
                "vector": [0.1 * i] * 1536,
                "payload": {"content": f"Document {i}", "batch": True}
            })
        
        result = await vectorization_agent.store_vectors(vectors, "batch-collection")
        
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()
    
    async def test_collection_info(self, vectorization_agent, mock_qdrant_client):
        """Test de récupération d'informations sur une collection."""
        
        # Mock de l'info collection
        mock_qdrant_client.get_collection.return_value = MagicMock(
            vectors_count=1000,
            config=MagicMock(params=MagicMock(vectors=MagicMock(size=1536)))
        )
        
        info = await vectorization_agent.get_collection_info("test-collection")
        
        assert info["vectors_count"] == 1000
        assert info["vector_size"] == 1536
    
    async def test_similarity_threshold_filtering(self, vectorization_agent, mock_qdrant_client):
        """Test de filtrage par seuil de similarité."""
        
        # Mock avec scores variés
        mock_qdrant_client.search.return_value = [
            MagicMock(id="doc-1", score=0.95, payload={"content": "Très pertinent"}),
            MagicMock(id="doc-2", score=0.85, payload={"content": "Moyennement pertinent"}),
            MagicMock(id="doc-3", score=0.60, payload={"content": "Peu pertinent"}),
            MagicMock(id="doc-4", score=0.40, payload={"content": "Non pertinent"})
        ]
        
        query_vector = [0.1] * 1536
        similarity_threshold = 0.7
        
        results = await vectorization_agent.search_similar_vectors(
            query_vector,
            collection_name="test-collection",
            top_k=10,
            similarity_threshold=similarity_threshold
        )
        
        # Seuls les résultats avec score >= 0.7 doivent être retournés
        assert len(results) == 2
        assert all(result["score"] >= similarity_threshold for result in results)
    
    async def test_vector_normalization(self, vectorization_agent):
        """Test de normalisation des vecteurs."""
        
        # Vecteur non normalisé
        vector = [1.0, 2.0, 3.0, 4.0]
        
        normalized = await vectorization_agent._normalize_vector(vector)
        
        # Vérifier que la norme est 1
        norm = np.linalg.norm(normalized)
        assert abs(norm - 1.0) < 1e-6
    
    async def test_embedding_caching(self, vectorization_agent, mock_redis_client):
        """Test de mise en cache des embeddings."""
        
        with patch.object(vectorization_agent, 'redis_client', mock_redis_client):
            # Première fois : pas de cache
            mock_redis_client.get.return_value = None
            
            texts = ["Texte à mettre en cache"]
            
            embeddings = await vectorization_agent.generate_embeddings(texts, use_cache=True)
            
            # Vérifier que le cache a été appelé
            mock_redis_client.get.assert_called()
            mock_redis_client.set.assert_called()
    
    async def test_hybrid_search(self, vectorization_agent, mock_qdrant_client):
        """Test de recherche hybride (vectorielle + texte)."""
        
        # Mock de résultats vectoriels
        mock_qdrant_client.search.return_value = [
            MagicMock(id="doc-1", score=0.90, payload={"content": "Résultat vectoriel"}),
            MagicMock(id="doc-2", score=0.80, payload={"content": "Autre résultat"})
        ]
        
        query = "recherche hybride test"
        
        results = await vectorization_agent.hybrid_search(
            query,
            collection_name="test-collection",
            top_k=5,
            alpha=0.7  # Pondération vectoriel vs texte
        )
        
        assert len(results) > 0
        assert all("score" in result for result in results)
    
    async def test_reindex_collection(self, vectorization_agent, mock_qdrant_client):
        """Test de réindexation d'une collection."""
        
        collection_name = "collection-to-reindex"
        
        # Mock de la liste des vecteurs existants
        mock_qdrant_client.scroll.return_value = ([
            MagicMock(id="doc-1", payload={"content": "Document 1"}),
            MagicMock(id="doc-2", payload={"content": "Document 2"})
        ], None)
        
        result = await vectorization_agent.reindex_collection(collection_name)
        
        assert result is True
        # Vérifier que la collection a été supprimée et recréée
        mock_qdrant_client.delete_collection.assert_called_once()
        mock_qdrant_client.create_collection.assert_called_once()
    
    async def test_vector_backup_restore(self, vectorization_agent, mock_qdrant_client):
        """Test de sauvegarde et restauration de vecteurs."""
        
        collection_name = "collection-backup"
        
        # Mock pour la sauvegarde
        mock_qdrant_client.scroll.return_value = ([
            MagicMock(
                id="doc-1", 
                vector=[0.1] * 1536,
                payload={"content": "Document sauvegardé"}
            )
        ], None)
        
        # Test de sauvegarde
        backup_data = await vectorization_agent.backup_collection(collection_name)
        
        assert len(backup_data) == 1
        assert "id" in backup_data[0]
        assert "vector" in backup_data[0]
        assert "payload" in backup_data[0]
        
        # Test de restauration
        result = await vectorization_agent.restore_collection(collection_name, backup_data)
        
        assert result is True
        mock_qdrant_client.upsert.assert_called()
