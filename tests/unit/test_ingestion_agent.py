"""
Tests unitaires pour l'agent d'ingestion.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import tempfile
import os

from agents.ingestion.agent import IngestionAgent
from core.models import DocumentMetadata, ProcessingResult
from core.exceptions import ProcessingError, ValidationError


class TestIngestionAgent:
    """Tests pour l'agent d'ingestion."""
    
    @pytest.fixture
    async def ingestion_agent(self, db_session, mock_minio_client):
        """Instance de l'agent d'ingestion pour les tests."""
        with patch('agents.ingestion.agent.MinIO', return_value=mock_minio_client):
            agent = IngestionAgent(db_session=db_session)
            yield agent
    
    @pytest.fixture
    def sample_pdf_file(self):
        """Fichier PDF de test."""
        content = b"%PDF-1.4\n1 0 obj\n<<>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 1\n0000000000 65535 f\ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        yield tmp_path
        
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    async def test_process_document_success(self, ingestion_agent, sample_pdf_file, test_user, test_organization):
        """Test du traitement réussi d'un document."""
        
        with patch('agents.ingestion.agent.PyPDF2.PdfReader') as mock_pdf:
            # Mock de l'extraction de texte
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Contenu de test du PDF"
            mock_pdf.return_value.pages = [mock_page]
            
            # Métadonnées du document
            metadata = DocumentMetadata(
                filename="test.pdf",
                file_path=sample_pdf_file,
                user_id=test_user["user_id"],
                organization_id=test_organization["organization_id"]
            )
            
            # Contenu du fichier
            with open(sample_pdf_file, 'rb') as f:
                content = f.read()
            
            # Traitement du document
            result = await ingestion_agent.process_document(metadata, content)
            
            # Vérifications
            assert isinstance(result, ProcessingResult)
            assert result.success is True
            assert result.document_id is not None
            assert result.extracted_text == "Contenu de test du PDF"
            assert result.chunks is not None
            assert len(result.chunks) > 0
    
    async def test_process_document_invalid_file(self, ingestion_agent, test_user, test_organization):
        """Test du traitement d'un fichier invalide."""
        
        metadata = DocumentMetadata(
            filename="test.invalid",
            file_path="/path/to/invalid/file",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"]
        )
        
        with pytest.raises(ValidationError):
            await ingestion_agent.process_document(metadata, b"invalid content")
    
    async def test_extract_text_from_pdf(self, ingestion_agent, sample_pdf_file):
        """Test de l'extraction de texte à partir d'un PDF."""
        
        with patch('agents.ingestion.agent.PyPDF2.PdfReader') as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Texte extrait du PDF"
            mock_pdf.return_value.pages = [mock_page]
            
            with open(sample_pdf_file, 'rb') as f:
                content = f.read()
            
            text = await ingestion_agent._extract_text_from_pdf(content)
            assert text == "Texte extrait du PDF"
    
    async def test_extract_text_from_docx(self, ingestion_agent):
        """Test de l'extraction de texte à partir d'un DOCX."""
        
        with patch('agents.ingestion.agent.docx.Document') as mock_docx:
            mock_paragraph = MagicMock()
            mock_paragraph.text = "Texte extrait du DOCX"
            mock_docx.return_value.paragraphs = [mock_paragraph]
            
            text = await ingestion_agent._extract_text_from_docx(b"docx content")
            assert text == "Texte extrait du DOCX"
    
    async def test_extract_text_from_txt(self, ingestion_agent):
        """Test de l'extraction de texte à partir d'un fichier texte."""
        
        content = "Ceci est un fichier texte de test."
        text = await ingestion_agent._extract_text_from_txt(content.encode('utf-8'))
        assert text == content
    
    async def test_chunk_text(self, ingestion_agent):
        """Test du découpage de texte en chunks."""
        
        text = "Ceci est un texte long qui doit être découpé en plusieurs chunks pour tester la fonctionnalité de chunking de l'agent d'ingestion. " * 10
        
        chunks = await ingestion_agent._chunk_text(text)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 1000 for chunk in chunks)
        assert all(chunk.strip() for chunk in chunks)  # Pas de chunks vides
    
    async def test_validate_document_success(self, ingestion_agent):
        """Test de validation réussie d'un document."""
        
        metadata = DocumentMetadata(
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            user_id="user-123",
            organization_id="org-123"
        )
        
        content = b"Valid PDF content"
        
        # Ne doit pas lever d'exception
        await ingestion_agent._validate_document(metadata, content)
    
    async def test_validate_document_large_file(self, ingestion_agent):
        """Test de validation d'un fichier trop volumineux."""
        
        metadata = DocumentMetadata(
            filename="large.pdf",
            file_path="/path/to/large.pdf",
            user_id="user-123",
            organization_id="org-123"
        )
        
        # Simuler un fichier de 200MB
        content = b"x" * (200 * 1024 * 1024)
        
        with pytest.raises(ValidationError, match="trop volumineux"):
            await ingestion_agent._validate_document(metadata, content)
    
    async def test_validate_document_unsupported_format(self, ingestion_agent):
        """Test de validation d'un format non supporté."""
        
        metadata = DocumentMetadata(
            filename="test.xyz",  # Format non supporté
            file_path="/path/to/test.xyz",
            user_id="user-123",
            organization_id="org-123"
        )
        
        content = b"Some content"
        
        with pytest.raises(ValidationError, match="Format de fichier non supporté"):
            await ingestion_agent._validate_document(metadata, content)
    
    async def test_store_document_success(self, ingestion_agent, test_user, test_organization):
        """Test du stockage réussi d'un document."""
        
        metadata = DocumentMetadata(
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"]
        )
        
        content = b"PDF content"
        text = "Texte extrait"
        chunks = ["Chunk 1", "Chunk 2"]
        
        document_id = await ingestion_agent._store_document(
            metadata, content, text, chunks
        )
        
        assert document_id is not None
        assert isinstance(document_id, str)
    
    async def test_process_batch_documents(self, ingestion_agent, test_user, test_organization):
        """Test du traitement en lot de documents."""
        
        documents = []
        for i in range(3):
            metadata = DocumentMetadata(
                filename=f"test{i}.txt",
                file_path=f"/path/to/test{i}.txt",
                user_id=test_user["user_id"],
                organization_id=test_organization["organization_id"]
            )
            content = f"Contenu du document {i}".encode('utf-8')
            documents.append((metadata, content))
        
        results = await ingestion_agent.process_batch_documents(documents)
        
        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(result.document_id for result in results)
    
    async def test_error_handling(self, ingestion_agent, test_user, test_organization):
        """Test de la gestion d'erreur lors du traitement."""
        
        metadata = DocumentMetadata(
            filename="error.pdf",
            file_path="/path/to/error.pdf",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"]
        )
        
        # Simuler une erreur lors de l'extraction
        with patch.object(ingestion_agent, '_extract_text_from_pdf', side_effect=Exception("Erreur PDF")):
            result = await ingestion_agent.process_document(metadata, b"pdf content")
            
            assert result.success is False
            assert "Erreur PDF" in result.error_message
    
    async def test_document_metadata_extraction(self, ingestion_agent):
        """Test de l'extraction des métadonnées d'un document."""
        
        content = b"Contenu de test"
        filename = "test.pdf"
        
        metadata = await ingestion_agent._extract_metadata(content, filename)
        
        assert metadata["filename"] == filename
        assert metadata["size"] == len(content)
        assert metadata["format"] == "pdf"
        assert "processed_at" in metadata
    
    async def test_concurrent_processing(self, ingestion_agent, test_user, test_organization):
        """Test du traitement concurrent de documents."""
        
        import asyncio
        
        async def process_single_doc(index):
            metadata = DocumentMetadata(
                filename=f"concurrent{index}.txt",
                file_path=f"/path/to/concurrent{index}.txt",
                user_id=test_user["user_id"],
                organization_id=test_organization["organization_id"]
            )
            content = f"Contenu concurrent {index}".encode('utf-8')
            return await ingestion_agent.process_document(metadata, content)
        
        # Traiter 5 documents en parallèle
        tasks = [process_single_doc(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(result.success for result in results)
        
        # Vérifier que tous les IDs sont uniques
        document_ids = [result.document_id for result in results]
        assert len(set(document_ids)) == 5
