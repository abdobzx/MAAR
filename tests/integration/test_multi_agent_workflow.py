"""
Tests d'intégration pour les agents multi-agents.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agents.orchestration.agent import OrchestrationAgent
from agents.ingestion.agent import IngestionAgent
from agents.vectorization.agent import VectorizationAgent
from agents.retrieval.agent import RetrievalAgent
from agents.synthesis.agent import SynthesisAgent
from agents.feedback.agent import FeedbackMemoryAgent
from core.models import DocumentMetadata, QueryRequest, ProcessingResult


class TestMultiAgentIntegration:
    """Tests d'intégration pour le système multi-agent."""
    
    @pytest.fixture
    async def orchestration_agent(self, db_session):
        """Agent d'orchestration pour les tests."""
        with patch('agents.orchestration.agent.IngestionAgent') as mock_ingestion, \
             patch('agents.orchestration.agent.VectorizationAgent') as mock_vectorization, \
             patch('agents.orchestration.agent.RetrievalAgent') as mock_retrieval, \
             patch('agents.orchestration.agent.SynthesisAgent') as mock_synthesis, \
             patch('agents.orchestration.agent.FeedbackMemoryAgent') as mock_feedback:
            
            agent = OrchestrationAgent(db_session=db_session)
            
            # Configurer les mocks des agents
            agent.ingestion_agent = mock_ingestion.return_value
            agent.vectorization_agent = mock_vectorization.return_value
            agent.retrieval_agent = mock_retrieval.return_value
            agent.synthesis_agent = mock_synthesis.return_value
            agent.feedback_agent = mock_feedback.return_value
            
            yield agent
    
    async def test_complete_document_processing_flow(self, orchestration_agent, test_user, test_organization):
        """Test du flux complet de traitement de document."""
        
        # Préparer les données de test
        document_metadata = DocumentMetadata(
            filename="test-policy.pdf",
            file_path="/tmp/test-policy.pdf",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"]
        )
        
        document_content = b"Politique de sécurité informatique de l'entreprise..."
        
        # Mock du résultat d'ingestion
        ingestion_result = ProcessingResult(
            success=True,
            document_id="doc-123",
            extracted_text="Politique de sécurité informatique...",
            chunks=["Chunk 1: Politique générale", "Chunk 2: Règles spécifiques"],
            metadata={"pages": 5, "format": "pdf"}
        )
        
        orchestration_agent.ingestion_agent.process_document = AsyncMock(return_value=ingestion_result)
        
        # Mock de la vectorisation
        orchestration_agent.vectorization_agent.generate_embeddings = AsyncMock(
            return_value=[[0.1] * 1536, [0.2] * 1536]
        )
        orchestration_agent.vectorization_agent.store_vectors = AsyncMock(return_value=True)
        
        # Exécuter le flux complet
        result = await orchestration_agent.process_document(document_metadata, document_content)
        
        # Vérifications
        assert result.success is True
        assert result.document_id == "doc-123"
        
        # Vérifier que tous les agents ont été appelés
        orchestration_agent.ingestion_agent.process_document.assert_called_once()
        orchestration_agent.vectorization_agent.generate_embeddings.assert_called_once()
        orchestration_agent.vectorization_agent.store_vectors.assert_called_once()
    
    async def test_complete_query_processing_flow(self, orchestration_agent, test_user, test_organization):
        """Test du flux complet de traitement de requête."""
        
        query_request = QueryRequest(
            query="Quelle est la politique de sécurité pour les mots de passe?",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            use_rag=True,
            conversation_id="conv-123"
        )
        
        # Mock de la recherche
        search_results = [
            {
                "id": "doc-1",
                "content": "La politique des mots de passe exige...",
                "metadata": {"source": "security-policy.pdf", "page": 3},
                "score": 0.95
            },
            {
                "id": "doc-2",
                "content": "Les mots de passe doivent contenir...",
                "metadata": {"source": "password-guide.pdf", "page": 1},
                "score": 0.88
            }
        ]
        
        orchestration_agent.retrieval_agent.search_documents = AsyncMock(return_value=search_results)
        
        # Mock de la synthèse
        synthesis_result = {
            "response": "Selon la politique de sécurité, les mots de passe doivent...",
            "sources": ["security-policy.pdf", "password-guide.pdf"],
            "confidence": 0.9,
            "tokens_used": 150
        }
        
        orchestration_agent.synthesis_agent.generate_response = AsyncMock(return_value=synthesis_result)
        
        # Mock du feedback
        orchestration_agent.feedback_agent.store_interaction_memory = AsyncMock(return_value=True)
        
        # Exécuter le flux de requête
        result = await orchestration_agent.process_query(query_request)
        
        # Vérifications
        assert result["response"] == synthesis_result["response"]
        assert len(result["sources"]) == 2
        assert result["confidence"] == 0.9
        
        # Vérifier que tous les agents ont été appelés
        orchestration_agent.retrieval_agent.search_documents.assert_called_once()
        orchestration_agent.synthesis_agent.generate_response.assert_called_once()
        orchestration_agent.feedback_agent.store_interaction_memory.assert_called_once()
    
    async def test_error_handling_in_orchestration(self, orchestration_agent, test_user, test_organization):
        """Test de gestion d'erreur dans l'orchestration."""
        
        query_request = QueryRequest(
            query="Requête qui va échouer",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"]
        )
        
        # Simuler une erreur dans la recherche
        orchestration_agent.retrieval_agent.search_documents = AsyncMock(
            side_effect=Exception("Erreur de recherche")
        )
        
        # Le flux doit gérer l'erreur gracieusement
        result = await orchestration_agent.process_query(query_request)
        
        assert "error" in result
        assert "Erreur de recherche" in result["error"]
    
    async def test_feedback_learning_loop(self, orchestration_agent, test_user, test_organization):
        """Test de la boucle d'apprentissage par feedback."""
        
        # Simuler une interaction avec feedback
        query_request = QueryRequest(
            query="Comment configurer l'authentification à deux facteurs?",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"]
        )
        
        # Mock des résultats
        orchestration_agent.retrieval_agent.search_documents = AsyncMock(return_value=[
            {"id": "doc-1", "content": "Configuration 2FA...", "score": 0.8}
        ])
        
        orchestration_agent.synthesis_agent.generate_response = AsyncMock(return_value={
            "response": "Pour configurer l'authentification à deux facteurs...",
            "sources": ["auth-guide.pdf"],
            "confidence": 0.8
        })
        
        # Mock de la génération d'insights
        learning_insights = [
            MagicMock(dict=lambda: {
                "type": "query_pattern",
                "title": "Questions fréquentes sur l'authentification",
                "confidence_score": 0.9
            })
        ]
        
        orchestration_agent.feedback_agent.get_learning_insights = AsyncMock(
            return_value=learning_insights
        )
        
        # Traiter la requête
        result = await orchestration_agent.process_query(query_request)
        
        # Simuler un feedback positif
        feedback_data = {
            "rating": 5,
            "feedback_type": "helpfulness",
            "content": "Réponse très utile!",
            "context": {"query": query_request.query, "response_id": result.get("response_id")}
        }
        
        orchestration_agent.feedback_agent.store_feedback = AsyncMock(return_value="feedback-123")
        
        await orchestration_agent.process_feedback(
            test_user["user_id"],
            test_organization["organization_id"],
            feedback_data
        )
        
        # Récupérer les insights d'apprentissage
        insights = await orchestration_agent.get_learning_insights(
            test_organization["organization_id"]
        )
        
        assert len(insights) > 0
        assert insights[0].dict()["type"] == "query_pattern"
    
    async def test_concurrent_document_processing(self, orchestration_agent, test_user, test_organization):
        """Test de traitement concurrent de documents."""
        
        # Préparer plusieurs documents
        documents = []
        for i in range(5):
            metadata = DocumentMetadata(
                filename=f"document-{i}.pdf",
                file_path=f"/tmp/document-{i}.pdf",
                user_id=test_user["user_id"],
                organization_id=test_organization["organization_id"]
            )
            content = f"Contenu du document {i}".encode('utf-8')
            documents.append((metadata, content))
        
        # Mock des résultats de traitement
        async def mock_process_document(metadata, content):
            await asyncio.sleep(0.1)  # Simuler le traitement
            return ProcessingResult(
                success=True,
                document_id=f"doc-{metadata.filename}",
                extracted_text=content.decode('utf-8'),
                chunks=[content.decode('utf-8')],
                metadata={"filename": metadata.filename}
            )
        
        orchestration_agent.ingestion_agent.process_document = mock_process_document
        orchestration_agent.vectorization_agent.generate_embeddings = AsyncMock(
            return_value=[[0.1] * 1536]
        )
        orchestration_agent.vectorization_agent.store_vectors = AsyncMock(return_value=True)
        
        # Traiter tous les documents en parallèle
        tasks = [
            orchestration_agent.process_document(metadata, content)
            for metadata, content in documents
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Vérifications
        assert len(results) == 5
        assert all(result.success for result in results)
        
        # Vérifier que tous les IDs sont uniques
        document_ids = [result.document_id for result in results]
        assert len(set(document_ids)) == 5
    
    async def test_streaming_query_processing(self, orchestration_agent, test_user, test_organization):
        """Test de traitement de requête en streaming."""
        
        query_request = QueryRequest(
            query="Expliquez le processus de déploiement d'applications",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            stream=True
        )
        
        # Mock du streaming
        async def mock_stream_response(*args, **kwargs):
            yield {"type": "search_started", "message": "Recherche de documents..."}
            await asyncio.sleep(0.1)
            yield {"type": "documents_found", "count": 3}
            await asyncio.sleep(0.1)
            yield {"type": "text", "content": "Le processus de déploiement comprend..."}
            await asyncio.sleep(0.1)
            yield {"type": "text", "content": " plusieurs étapes importantes."}
            yield {"type": "sources", "sources": ["deploy-guide.pdf", "best-practices.pdf"]}
            yield {"type": "done"}
        
        orchestration_agent.synthesis_agent.stream_response = mock_stream_response
        
        # Collecter les chunks du stream
        chunks = []
        async for chunk in orchestration_agent.stream_query(query_request):
            chunks.append(chunk)
        
        # Vérifications
        assert len(chunks) == 6
        assert chunks[0]["type"] == "search_started"
        assert chunks[-1]["type"] == "done"
        
        # Vérifier que le texte est bien streamé
        text_chunks = [chunk for chunk in chunks if chunk["type"] == "text"]
        assert len(text_chunks) == 2
    
    async def test_agent_health_monitoring(self, orchestration_agent):
        """Test de monitoring de santé des agents."""
        
        # Mock des health checks des agents
        orchestration_agent.ingestion_agent.health_check = AsyncMock(return_value=True)
        orchestration_agent.vectorization_agent.health_check = AsyncMock(return_value=True)
        orchestration_agent.retrieval_agent.health_check = AsyncMock(return_value=True)
        orchestration_agent.synthesis_agent.health_check = AsyncMock(return_value=False)  # Agent en panne
        orchestration_agent.feedback_agent.health_check = AsyncMock(return_value=True)
        
        # Vérifier la santé du système
        health_status = await orchestration_agent.check_system_health()
        
        assert health_status["overall_status"] == "degraded"  # Un agent en panne
        assert health_status["agents"]["synthesis"] is False
        assert health_status["agents"]["ingestion"] is True
    
    async def test_performance_optimization(self, orchestration_agent, test_user, test_organization):
        """Test d'optimisation des performances."""
        
        # Test avec mise en cache
        query_request = QueryRequest(
            query="Politique de télétravail",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            use_cache=True
        )
        
        # Mock du cache hit
        cached_result = {
            "response": "Réponse mise en cache",
            "sources": ["policy.pdf"],
            "from_cache": True
        }
        
        orchestration_agent.retrieval_agent.get_cached_response = AsyncMock(
            return_value=cached_result
        )
        
        # Première requête (mise en cache)
        result1 = await orchestration_agent.process_query(query_request)
        
        # Deuxième requête identique (du cache)
        result2 = await orchestration_agent.process_query(query_request)
        
        # Vérifier que le cache est utilisé
        assert result2.get("from_cache") is True
        assert result1["response"] == result2["response"]
    
    async def test_multi_modal_document_processing(self, orchestration_agent, test_user, test_organization):
        """Test de traitement de documents multi-modaux."""
        
        # Document avec texte et images
        document_metadata = DocumentMetadata(
            filename="presentation.pdf",
            file_path="/tmp/presentation.pdf",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            metadata={"has_images": True, "pages": 20}
        )
        
        document_content = b"PDF avec du texte et des images..."
        
        # Mock du traitement multi-modal
        orchestration_agent.ingestion_agent.process_document = AsyncMock(return_value=ProcessingResult(
            success=True,
            document_id="doc-multimodal-123",
            extracted_text="Texte extrait de la présentation...",
            chunks=["Slide 1: Introduction", "Slide 2: Architecture"],
            metadata={
                "images_processed": 5,
                "text_pages": 20,
                "format": "pdf"
            }
        ))
        
        # Mock de la vectorisation multi-modale
        orchestration_agent.vectorization_agent.generate_embeddings = AsyncMock(
            return_value=[[0.1] * 1536, [0.2] * 1536]  # Embeddings pour texte et images
        )
        
        result = await orchestration_agent.process_document(document_metadata, document_content)
        
        assert result.success is True
        assert result.metadata["images_processed"] == 5
    
    async def test_adaptive_chunking_strategy(self, orchestration_agent, test_user, test_organization):
        """Test de stratégie de chunking adaptatif."""
        
        # Document technique long
        long_technical_doc = DocumentMetadata(
            filename="technical-spec.pdf",
            file_path="/tmp/technical-spec.pdf",
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            metadata={"document_type": "technical", "estimated_length": 50000}
        )
        
        # Mock du chunking adaptatif
        orchestration_agent.ingestion_agent.process_document = AsyncMock(return_value=ProcessingResult(
            success=True,
            document_id="doc-tech-123",
            extracted_text="Documentation technique très détaillée...",
            chunks=["Chunk technique 1", "Chunk technique 2"],  # Chunks plus petits pour doc technique
            metadata={
                "chunking_strategy": "technical",
                "chunk_size": 500,  # Plus petit pour documents techniques
                "overlap": 100
            }
        ))
        
        content = b"Contenu technique très détaillé..."
        result = await orchestration_agent.process_document(long_technical_doc, content)
        
        assert result.metadata["chunking_strategy"] == "technical"
        assert result.metadata["chunk_size"] == 500
