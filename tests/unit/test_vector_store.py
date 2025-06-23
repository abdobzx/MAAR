"""
Tests unitaires pour le module vector_store
"""

import pytest
import asyncio
from unittest.mock import patch, Mock

from vector_store.models import Document, DocumentChunk, SearchQuery, DocumentStatus
from vector_store.faiss_store import FAISSVectorStore
from vector_store.ingestion import DocumentIngestion
from tests.conftest import assert_document_valid, assert_chunk_valid, assert_vector_store_functional


class TestDocumentModels:
    """Tests pour les modèles de données"""
    
    def test_document_creation(self, sample_document):
        """Test de création d'un document"""
        assert_document_valid(sample_document)
        assert sample_document.status == DocumentStatus.PENDING
        assert sample_document.chunk_count == 0
    
    def test_document_chunk_creation(self, sample_chunks):
        """Test de création de chunks"""
        for chunk in sample_chunks:
            assert_chunk_valid(chunk)
            assert len(chunk.embedding) == 384
    
    def test_search_query_validation(self):
        """Test de validation des requêtes de recherche"""
        query = SearchQuery(
            query="test query",
            max_results=10,
            min_score=0.5
        )
        
        assert query.query == "test query"
        assert query.max_results == 10
        assert query.min_score == 0.5
        assert query.filters == {}
        assert query.include_metadata is True


class TestDocumentIngestion:
    """Tests pour l'ingestion de documents"""
    
    def test_ingestion_initialization(self):
        """Test d'initialisation du système d'ingestion"""
        ingestion = DocumentIngestion()
        assert ingestion.chunk_size == 512
        assert ingestion.chunk_overlap == 50
        assert ingestion.min_chunk_size == 50
    
    def test_custom_config(self):
        """Test avec configuration personnalisée"""
        config = {
            "chunk_size": 200,
            "chunk_overlap": 20,
            "min_chunk_size": 30
        }
        
        ingestion = DocumentIngestion(config)
        assert ingestion.chunk_size == 200
        assert ingestion.chunk_overlap == 20
        assert ingestion.min_chunk_size == 30
    
    @pytest.mark.asyncio
    async def test_document_chunking(self, document_ingestion, sample_document):
        """Test du découpage en chunks"""
        chunks = await document_ingestion.chunk_document(sample_document)
        
        assert len(chunks) > 0
        
        for i, chunk in enumerate(chunks):
            assert_chunk_valid(chunk)
            assert chunk.document_id == sample_document.id
            assert chunk.chunk_index == i
            assert f"{sample_document.id}_chunk_{i}" == chunk.id
    
    @pytest.mark.asyncio
    async def test_file_ingestion_txt(self, document_ingestion, sample_files):
        """Test d'ingestion d'un fichier texte"""
        document = await document_ingestion.ingest_file(sample_files['txt'])
        
        assert_document_valid(document)
        assert "test.txt" in document.metadata["file_name"]
        assert document.metadata["file_extension"] == ".txt"
        assert len(document.content) > 0
    
    @pytest.mark.asyncio
    async def test_file_ingestion_json(self, document_ingestion, sample_files):
        """Test d'ingestion d'un fichier JSON"""
        document = await document_ingestion.ingest_file(sample_files['json'])
        
        assert_document_valid(document)
        assert "test" in document.content
        assert "42" in document.content
    
    @pytest.mark.asyncio
    async def test_file_ingestion_md(self, document_ingestion, sample_files):
        """Test d'ingestion d'un fichier Markdown"""
        document = await document_ingestion.ingest_file(sample_files['md'])
        
        assert_document_valid(document)
        assert "Titre" in document.content
        assert "markdown" in document.content
    
    @pytest.mark.asyncio
    async def test_unsupported_extension(self, document_ingestion, temp_dir):
        """Test avec une extension non supportée"""
        import os
        
        unsupported_file = os.path.join(temp_dir, "test.xyz")
        with open(unsupported_file, 'w') as f:
            f.write("contenu")
        
        with pytest.raises(ValueError, match="Extension non supportée"):
            await document_ingestion.ingest_file(unsupported_file)
    
    @pytest.mark.asyncio
    async def test_directory_ingestion(self, document_ingestion, sample_files, temp_dir):
        """Test d'ingestion d'un répertoire"""
        documents = await document_ingestion.ingest_directory(temp_dir)
        
        assert len(documents) == len(sample_files)
        
        for doc in documents:
            assert_document_valid(doc)
    
    def test_supported_extensions(self, document_ingestion):
        """Test de la liste des extensions supportées"""
        extensions = document_ingestion.get_supported_extensions()
        
        expected = ['.txt', '.pdf', '.docx', '.md', '.json']
        for ext in expected:
            assert ext in extensions


@pytest.mark.skipif(
    True,  # Skip par défaut car nécessite FAISS
    reason="FAISS tests nécessitent faiss-cpu installé"
)
class TestFAISSVectorStore:
    """Tests pour le FAISS vector store"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, temp_dir):
        """Test d'initialisation du FAISS store"""
        store = FAISSVectorStore(
            storage_path=temp_dir,
            embedding_dim=384
        )
        
        success = await store.initialize()
        assert success
        assert_vector_store_functional(store)
        
        await store.cleanup()
    
    @pytest.mark.asyncio
    async def test_add_chunks(self, faiss_store, sample_chunks):
        """Test d'ajout de chunks"""
        success = await faiss_store.add_chunks(sample_chunks)
        assert success
        
        stats = await faiss_store.get_stats()
        assert stats["total_chunks"] == len(sample_chunks)
    
    @pytest.mark.asyncio
    async def test_search_by_embedding(self, faiss_store, sample_chunks):
        """Test de recherche par embedding"""
        # Ajouter des chunks
        await faiss_store.add_chunks(sample_chunks)
        
        # Rechercher avec un embedding similaire
        results = await faiss_store.search_by_embedding(
            embedding=sample_chunks[0].embedding,
            max_results=2
        )
        
        assert len(results) > 0
        assert results[0].score > 0.5  # Similarité élevée avec lui-même
    
    @pytest.mark.asyncio
    async def test_document_deletion(self, faiss_store, sample_chunks):
        """Test de suppression de document"""
        # Ajouter des chunks
        await faiss_store.add_chunks(sample_chunks)
        
        # Supprimer le document
        success = await faiss_store.delete_document(sample_chunks[0].document_id)
        assert success
        
        # Vérifier que les chunks sont supprimés
        stats = await faiss_store.get_stats()
        assert stats["total_chunks"] == 0
    
    @pytest.mark.asyncio
    async def test_stats(self, faiss_store, sample_chunks):
        """Test des statistiques"""
        await faiss_store.add_chunks(sample_chunks)
        
        stats = await faiss_store.get_stats()
        
        assert stats["type"] == "FAISS"
        assert stats["embedding_dim"] == 384
        assert stats["total_chunks"] == len(sample_chunks)
        assert stats["total_documents"] == 1  # Tous les chunks du même document


class TestVectorStoreIntegration:
    """Tests d'intégration vector store + ingestion"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, temp_dir, sample_files):
        """Test du workflow complet d'ingestion"""
        # Initialiser l'ingestion
        ingestion = DocumentIngestion()
        
        # Mock du vector store (pour éviter les dépendances)
        from unittest.mock import AsyncMock
        mock_store = AsyncMock()
        mock_store.add_chunks.return_value = True
        
        # Ingérer un fichier
        document = await ingestion.ingest_file(sample_files['txt'])
        assert_document_valid(document)
        
        # Découper en chunks
        chunks = await ingestion.chunk_document(document)
        assert len(chunks) > 0
        
        for chunk in chunks:
            assert_chunk_valid(chunk)
        
        # Simuler l'ajout au vector store
        success = await mock_store.add_chunks(chunks)
        assert success
        
        # Vérifier l'appel
        mock_store.add_chunks.assert_called_once_with(chunks)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, document_ingestion):
        """Test de gestion d'erreur"""
        # Fichier inexistant
        with pytest.raises(FileNotFoundError):
            await document_ingestion.ingest_file("/nonexistent/file.txt")
        
        # Répertoire inexistant
        with pytest.raises(ValueError):
            await document_ingestion.ingest_directory("/nonexistent/directory")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
