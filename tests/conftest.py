"""
Configuration and fixtures for testing the Enterprise RAG System.
"""

import pytest
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import Settings
from core.models import Base
from database.manager import DatabaseManager
from api.main import app


# Configuration de test
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Créer une boucle d'événements pour la session de test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Paramètres de configuration pour les tests."""
    return Settings(
        environment="testing",
        debug=True,
        database_url=TEST_DATABASE_URL,
        redis_url="redis://localhost:6379/15",  # Base de test Redis
        secret_key="test-secret-key-for-testing-only",
        jwt_expire_minutes=30
    )


@pytest.fixture(scope="session")
async def test_engine(test_settings):
    """Moteur de base de données pour les tests."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        future=True
    )
    
    # Créer les tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Nettoyage
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session de base de données pour les tests."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Client de test pour l'API."""
    return TestClient(app)


@pytest.fixture(scope="function")
async def test_user() -> Dict[str, Any]:
    """Utilisateur de test."""
    return {
        "user_id": "test-user-123",
        "email": "test@enterprise-rag.com",
        "organization_id": "test-org-123",
        "roles": ["user"],
        "permissions": ["documents:read", "documents:write", "chat:access"]
    }


@pytest.fixture(scope="function")
async def test_organization() -> Dict[str, Any]:
    """Organisation de test."""
    return {
        "organization_id": "test-org-123",
        "name": "Test Organization",
        "settings": {
            "max_documents": 1000,
            "retention_days": 365
        }
    }


@pytest.fixture(scope="function")
async def mock_llm_response():
    """Mock de réponse LLM."""
    return {
        "content": "Ceci est une réponse de test du modèle LLM.",
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        },
        "model": "gpt-4"
    }


@pytest.fixture(scope="function")
async def mock_vector_search_results():
    """Mock de résultats de recherche vectorielle."""
    return [
        {
            "id": "doc-1",
            "content": "Premier document pertinent",
            "metadata": {"source": "test1.pdf", "page": 1},
            "score": 0.95
        },
        {
            "id": "doc-2", 
            "content": "Deuxième document pertinent",
            "metadata": {"source": "test2.pdf", "page": 1},
            "score": 0.85
        }
    ]


@pytest.fixture(scope="function")
def temp_file():
    """Fichier temporaire pour les tests."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(b"Contenu de test PDF")
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Nettoyage
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture(scope="function")
async def mock_document():
    """Document de test."""
    return {
        "id": "test-doc-123",
        "filename": "test-document.pdf",
        "content": "Ceci est le contenu d'un document de test.",
        "metadata": {
            "size": 1024,
            "type": "pdf",
            "pages": 1
        },
        "created_at": "2024-01-01T00:00:00Z",
        "organization_id": "test-org-123",
        "user_id": "test-user-123"
    }


@pytest.fixture(scope="function")
async def mock_chat_conversation():
    """Conversation de chat de test."""
    return {
        "conversation_id": "test-conv-123",
        "messages": [
            {
                "role": "user",
                "content": "Quelle est la politique de congés de l'entreprise?",
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "role": "assistant",
                "content": "Voici les informations sur la politique de congés...",
                "timestamp": "2024-01-01T10:00:05Z",
                "sources": ["policy-doc-1", "policy-doc-2"]
            }
        ],
        "user_id": "test-user-123",
        "organization_id": "test-org-123"
    }


@pytest.fixture(scope="function")
def mock_celery_task():
    """Mock de tâche Celery."""
    task_mock = MagicMock()
    task_mock.id = "test-task-123"
    task_mock.status = "SUCCESS"
    task_mock.result = {"status": "completed"}
    return task_mock


# Mocks pour les services externes
@pytest.fixture(scope="function")
def mock_openai_client():
    """Mock du client OpenAI."""
    mock = AsyncMock()
    mock.embeddings.create.return_value.data = [
        MagicMock(embedding=[0.1] * 1536)
    ]
    mock.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="Réponse de test"))
    ]
    return mock


@pytest.fixture(scope="function")
def mock_qdrant_client():
    """Mock du client Qdrant."""
    mock = AsyncMock()
    mock.search.return_value = [
        MagicMock(id="doc-1", score=0.95, payload={"content": "Contenu test 1"}),
        MagicMock(id="doc-2", score=0.85, payload={"content": "Contenu test 2"})
    ]
    mock.upsert.return_value = MagicMock(operation_id="test-op-123")
    return mock


@pytest.fixture(scope="function")
def mock_redis_client():
    """Mock du client Redis."""
    mock = AsyncMock()
    mock.get.return_value = json.dumps({"cached": "data"})
    mock.set.return_value = True
    mock.exists.return_value = True
    return mock


@pytest.fixture(scope="function")
def mock_minio_client():
    """Mock du client MinIO."""
    mock = MagicMock()
    mock.put_object.return_value = MagicMock(etag="test-etag")
    mock.get_object.return_value = MagicMock(data=b"test file content")
    return mock


# Helpers pour les tests
def create_test_file(content: str, filename: str = "test.txt") -> str:
    """Créer un fichier de test temporaire."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f"-{filename}") as tmp:
        tmp.write(content)
        return tmp.name


async def assert_response_success(response, expected_data=None):
    """Vérifier qu'une réponse API est un succès."""
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    if expected_data:
        assert data["data"] == expected_data


async def assert_response_error(response, expected_status=400):
    """Vérifier qu'une réponse API est une erreur."""
    assert response.status_code == expected_status
    data = response.json()
    assert "detail" in data or "message" in data


# Markers personnalisés pour pytest
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.filterwarnings("ignore::DeprecationWarning")
]
