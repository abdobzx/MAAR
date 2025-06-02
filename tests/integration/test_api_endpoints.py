"""
Tests d'intégration pour l'API principale.
"""

import pytest
import json
import asyncio
import tempfile
import os
from typing import Dict, Any
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from api.main import app
from tests.conftest import assert_response_success, assert_response_error


class TestAPIIntegration:
    """Tests d'intégration pour l'API Enterprise RAG."""
    
    @pytest.fixture
    def client(self):
        """Client de test pour l'API."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user):
        """Headers d'authentification pour les tests."""
        # Mock du token JWT
        token = "test-jwt-token"
        return {"Authorization": f"Bearer {token}"}
    
    async def test_health_check_endpoint(self, client):
        """Test du endpoint de health check."""
        
        with patch('database.manager.DatabaseManager.health_check', return_value=True):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "version" in data
            assert "components" in data
    
    async def test_health_check_unhealthy(self, client):
        """Test du health check en cas de problème."""
        
        with patch('database.manager.DatabaseManager.health_check', side_effect=Exception("DB Error")):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
    
    async def test_upload_document_success(self, client, auth_headers):
        """Test d'upload de document réussi."""
        
        # Créer un fichier de test
        test_content = b"Contenu de test pour le document PDF"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(test_content)
            tmp_file_path = tmp_file.name
        
        try:
            with patch('agents.ingestion.agent.IngestionAgent.process_document') as mock_process:
                mock_process.return_value = MagicMock(
                    success=True,
                    document_id="test-doc-123",
                    extracted_text="Contenu extrait",
                    chunks=["Chunk 1", "Chunk 2"]
                )
                
                with open(tmp_file_path, 'rb') as f:
                    files = {"files": ("test.pdf", f, "application/pdf")}
                    
                    response = client.post(
                        "/api/v1/documents/upload",
                        files=files,
                        headers=auth_headers
                    )
                
                await assert_response_success(response)
                data = response.json()
                assert len(data["data"]) == 1
                assert data["data"][0]["document_id"] == "test-doc-123"
                assert data["data"][0]["status"] == "uploaded"
        
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    async def test_upload_document_unauthorized(self, client):
        """Test d'upload sans authentification."""
        
        test_content = b"Contenu de test"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
            tmp_file.write(test_content)
            tmp_file.seek(0)
            
            files = {"files": ("test.pdf", tmp_file, "application/pdf")}
            
            response = client.post("/api/v1/documents/upload", files=files)
            
            await assert_response_error(response, 401)
    
    async def test_upload_large_file(self, client, auth_headers):
        """Test d'upload d'un fichier trop volumineux."""
        
        # Simuler un fichier de 200MB
        large_content = b"x" * (200 * 1024 * 1024)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
            tmp_file.write(large_content)
            tmp_file.seek(0)
            
            files = {"files": ("large.pdf", tmp_file, "application/pdf")}
            
            response = client.post(
                "/api/v1/documents/upload",
                files=files,
                headers=auth_headers
            )
            
            await assert_response_error(response, 400)
    
    async def test_chat_endpoint_success(self, client, auth_headers, mock_llm_response):
        """Test du endpoint de chat réussi."""
        
        chat_request = {
            "message": "Quelle est la politique de congés de l'entreprise?",
            "conversation_id": "test-conv-123",
            "use_rag": True
        }
        
        with patch('agents.orchestration.agent.OrchestrationAgent.process_query') as mock_process:
            mock_process.return_value = {
                "response": "Voici les informations sur la politique de congés...",
                "sources": ["policy-doc-1.pdf", "policy-doc-2.pdf"],
                "confidence": 0.9,
                "tokens_used": 150
            }
            
            response = client.post(
                "/api/v1/chat",
                json=chat_request,
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert "response" in data["data"]
            assert "sources" in data["data"]
            assert "conversation_id" in data["data"]
    
    async def test_chat_streaming_endpoint(self, client, auth_headers):
        """Test du endpoint de chat en streaming."""
        
        chat_request = {
            "message": "Expliquez-moi le processus de recrutement",
            "conversation_id": "test-conv-456",
            "stream": True
        }
        
        with patch('agents.orchestration.agent.OrchestrationAgent.stream_query') as mock_stream:
            # Mock du générateur de streaming
            async def mock_generator():
                yield {"type": "text", "content": "Voici les étapes "}
                yield {"type": "text", "content": "du processus de recrutement..."}
                yield {"type": "sources", "sources": ["hr-policy.pdf"]}
                yield {"type": "done"}
            
            mock_stream.return_value = mock_generator()
            
            response = client.post(
                "/api/v1/chat/stream",
                json=chat_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            # Pour les tests de streaming, vérifier le content-type
            assert "text/event-stream" in response.headers.get("content-type", "")
    
    async def test_search_documents_endpoint(self, client, auth_headers, mock_vector_search_results):
        """Test du endpoint de recherche de documents."""
        
        search_request = {
            "query": "politique de sécurité informatique",
            "filters": {"document_type": "policy"},
            "top_k": 5
        }
        
        with patch('agents.retrieval.agent.RetrievalAgent.search_documents') as mock_search:
            mock_search.return_value = mock_vector_search_results
            
            response = client.post(
                "/api/v1/search",
                json=search_request,
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert len(data["data"]) == 2
            assert all("content" in result for result in data["data"])
    
    async def test_feedback_submission(self, client, auth_headers):
        """Test de soumission de feedback."""
        
        feedback_data = {
            "rating": 4,
            "feedback_type": "quality",
            "content": "La réponse était très utile et précise.",
            "context": {
                "query": "Quelle est la politique de congés?",
                "response_id": "resp-123"
            }
        }
        
        with patch('agents.feedback.agent.FeedbackMemoryAgent.store_feedback') as mock_store:
            mock_store.return_value = "feedback-123"
            
            response = client.post(
                "/api/v1/feedback",
                json=feedback_data,
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert data["data"]["feedback_id"] == "feedback-123"
    
    async def test_get_learning_insights(self, client, auth_headers):
        """Test de récupération des insights d'apprentissage."""
        
        with patch('agents.feedback.agent.FeedbackMemoryAgent.get_learning_insights') as mock_insights:
            mock_insights.return_value = [
                MagicMock(dict=lambda: {
                    "insight_id": "insight-1",
                    "type": "feedback_analysis",
                    "title": "Pattern détecté",
                    "confidence_score": 0.8
                })
            ]
            
            response = client.get(
                "/api/v1/insights?timeframe_days=7",
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert len(data["data"]) == 1
            assert data["data"][0]["type"] == "feedback_analysis"
    
    async def test_get_analytics_data(self, client, auth_headers):
        """Test de récupération des données analytiques."""
        
        analytics_data = {
            "total_queries": 1250,
            "avg_response_time": 2.3,
            "user_satisfaction": 4.2,
            "top_queries": [
                "politique de congés",
                "processus de recrutement",
                "sécurité informatique"
            ]
        }
        
        with patch('agents.feedback.agent.FeedbackMemoryAgent.get_analytics_data') as mock_analytics:
            mock_analytics.return_value = analytics_data
            
            response = client.get(
                "/api/v1/analytics",
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert data["data"]["total_queries"] == 1250
            assert data["data"]["avg_response_time"] == 2.3
    
    async def test_document_status_endpoint(self, client, auth_headers):
        """Test de vérification du statut d'un document."""
        
        document_id = "test-doc-123"
        
        with patch('database.manager.DatabaseManager.get_document_status') as mock_status:
            mock_status.return_value = {
                "document_id": document_id,
                "status": "processed",
                "processing_progress": 100,
                "extracted_text_length": 1500,
                "chunks_count": 10
            }
            
            response = client.get(
                f"/api/v1/documents/{document_id}/status",
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert data["data"]["status"] == "processed"
    
    async def test_conversation_history(self, client, auth_headers):
        """Test de récupération de l'historique de conversation."""
        
        conversation_id = "test-conv-123"
        
        mock_history = [
            {
                "role": "user",
                "content": "Quelle est la politique de congés?",
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "role": "assistant", 
                "content": "Voici les informations sur la politique de congés...",
                "timestamp": "2024-01-01T10:00:05Z",
                "sources": ["policy-doc.pdf"]
            }
        ]
        
        with patch('agents.feedback.agent.FeedbackMemoryAgent.get_conversation_context') as mock_context:
            mock_context.return_value = mock_history
            
            response = client.get(
                f"/api/v1/conversations/{conversation_id}/history",
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert len(data["data"]) == 2
            assert data["data"][0]["role"] == "user"
    
    async def test_rate_limiting(self, client, auth_headers):
        """Test de limitation de taux."""
        
        # Simuler de nombreuses requêtes rapides
        responses = []
        
        for i in range(150):  # Dépasser la limite de 100/min
            response = client.get("/health", headers=auth_headers)
            responses.append(response.status_code)
        
        # Vérifier qu'au moins certaines requêtes sont limitées
        rate_limited = [status for status in responses if status == 429]
        assert len(rate_limited) > 0
    
    async def test_error_handling(self, client, auth_headers):
        """Test de gestion d'erreurs globale."""
        
        # Test avec une requête malformée
        invalid_data = {"invalid": "data structure"}
        
        response = client.post(
            "/api/v1/chat",
            json=invalid_data,
            headers=auth_headers
        )
        
        await assert_response_error(response, 422)  # Validation error
        
        data = response.json()
        assert "detail" in data
    
    async def test_cors_headers(self, client):
        """Test des headers CORS."""
        
        response = client.options("/health")
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
    
    async def test_security_headers(self, client):
        """Test des headers de sécurité."""
        
        response = client.get("/health")
        
        # Vérifier que les headers de sécurité sont présents
        headers = response.headers
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
    
    async def test_concurrent_requests(self, client, auth_headers):
        """Test de requêtes concurrentes."""
        
        async def make_request(index):
            return client.get(f"/health?test={index}", headers=auth_headers)
        
        # Faire 20 requêtes concurrentes
        tasks = [make_request(i) for i in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Vérifier que toutes les requêtes ont abouti
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) == 20
        
        # Vérifier que toutes sont des succès
        status_codes = [r.status_code for r in successful_responses]
        assert all(status == 200 for status in status_codes)
    
    async def test_metrics_endpoint(self, client, auth_headers):
        """Test du endpoint des métriques."""
        
        with patch('api.main.get_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "requests_total": 1000,
                "avg_response_time": 250,
                "active_users": 45,
                "documents_processed": 500
            }
            
            response = client.get("/api/v1/metrics", headers=auth_headers)
            
            await assert_response_success(response)
            data = response.json()
            assert data["data"]["requests_total"] == 1000
    
    async def test_webhook_endpoint(self, client):
        """Test de endpoint webhook pour les intégrations externes."""
        
        webhook_data = {
            "event": "document.processed",
            "document_id": "doc-123",
            "status": "completed",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        # Mock de la signature webhook
        signature = "test-signature"
        headers = {"X-Webhook-Signature": signature}
        
        with patch('api.main.verify_webhook_signature', return_value=True):
            response = client.post(
                "/api/v1/webhooks/document",
                json=webhook_data,
                headers=headers
            )
            
            await assert_response_success(response)
    
    async def test_bulk_operations(self, client, auth_headers):
        """Test d'opérations en lot."""
        
        # Test de suppression en lot de documents
        delete_request = {
            "document_ids": ["doc-1", "doc-2", "doc-3"],
            "reason": "Test cleanup"
        }
        
        with patch('database.manager.DatabaseManager.delete_documents_batch') as mock_delete:
            mock_delete.return_value = {"deleted_count": 3, "failed_count": 0}
            
            response = client.delete(
                "/api/v1/documents/batch",
                json=delete_request,
                headers=auth_headers
            )
            
            await assert_response_success(response)
            data = response.json()
            assert data["data"]["deleted_count"] == 3
