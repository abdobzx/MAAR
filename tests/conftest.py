"""
<<<<<<< HEAD
Configuration et fixtures pour les tests
=======
Configuration and fixtures for testing the Enterprise RAG System.
>>>>>>> origin/main
"""

import pytest
import asyncio
<<<<<<< HEAD
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

# Import des modules à tester
from vector_store.models import Document, DocumentChunk
from vector_store.faiss_store import FAISSVectorStore
from vector_store.chroma_store import ChromaVectorStore
from vector_store.ingestion import DocumentIngestion


@pytest.fixture(scope="session")
def event_loop():
    """Fixture pour la boucle d'événements asyncio"""
=======
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
>>>>>>> origin/main
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


<<<<<<< HEAD
@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Fixture pour un répertoire temporaire"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_document() -> Document:
    """Fixture pour un document de test"""
    return Document(
        id="test_doc_001",
        content="Ceci est un document de test pour la plateforme MAR. " * 10,
        metadata={
            "source": "test",
            "category": "unit_test",
            "priority": "high"
        },
        title="Document de Test",
        source="tests/sample.txt"
    )


@pytest.fixture
def sample_chunks(sample_document) -> list[DocumentChunk]:
    """Fixture pour des chunks de test"""
    return [
        DocumentChunk(
            id=f"{sample_document.id}_chunk_0",
            document_id=sample_document.id,
            content="Premier chunk du document de test.",
            chunk_index=0,
            start_char=0,
            end_char=35,
            metadata=sample_document.metadata,
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 76  # 384 dimensions
        ),
        DocumentChunk(
            id=f"{sample_document.id}_chunk_1",
            document_id=sample_document.id,
            content="Deuxième chunk du document de test.",
            chunk_index=1,
            start_char=35,
            end_char=70,
            metadata=sample_document.metadata,
            embedding=[0.2, 0.3, 0.4, 0.5, 0.6] * 76  # 384 dimensions
        )
    ]


@pytest.fixture
async def faiss_store(temp_dir) -> AsyncGenerator[FAISSVectorStore, None]:
    """Fixture pour un FAISS vector store de test"""
    store = FAISSVectorStore(
        storage_path=temp_dir,
        embedding_dim=384,
        index_type="flat"
    )
    
    await store.initialize()
    yield store
    await store.cleanup()


@pytest.fixture
async def chroma_store(temp_dir) -> AsyncGenerator[ChromaVectorStore, None]:
    """Fixture pour un Chroma vector store de test"""
    try:
        store = ChromaVectorStore(
            storage_path=temp_dir,
            collection_name="test_collection"
        )
        
        await store.initialize()
        yield store
        await store.cleanup()
    except ImportError:
        pytest.skip("ChromaDB non installé")


@pytest.fixture
def document_ingestion() -> DocumentIngestion:
    """Fixture pour le système d'ingestion"""
    return DocumentIngestion({
        "chunk_size": 100,
        "chunk_overlap": 20,
        "min_chunk_size": 10
    })


@pytest.fixture
def mock_llm_client():
    """Mock du client LLM"""
    mock = AsyncMock()
    mock.generate.return_value = {
        "text": "Réponse simulée du LLM",
        "usage": {"prompt_tokens": 50, "completion_tokens": 25}
    }
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock du vector store"""
    mock = AsyncMock()
    mock.search.return_value = []
    mock.add_chunks.return_value = True
    mock.get_stats.return_value = {
        "total_chunks": 0,
        "total_documents": 0
    }
    return mock


@pytest.fixture
def sample_files(temp_dir) -> dict[str, str]:
    """Crée des fichiers de test"""
    files = {}
    
    # Fichier texte
    txt_path = os.path.join(temp_dir, "test.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("Contenu du fichier texte de test.\nDeuxième ligne.")
    files['txt'] = txt_path
    
    # Fichier JSON
    json_path = os.path.join(temp_dir, "test.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write('{"test": "data", "number": 42, "nested": {"key": "value"}}')
    files['json'] = json_path
    
    # Fichier Markdown
    md_path = os.path.join(temp_dir, "test.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Titre\n\nContenu markdown de test.\n\n## Sous-titre\n\nAutre contenu.")
    files['md'] = md_path
    
    return files


# Utilitaires pour les tests

def assert_document_valid(document: Document):
    """Valide qu'un document est bien formé"""
    assert document.id is not None
    assert len(document.content) > 0
    assert isinstance(document.metadata, dict)
    assert document.status is not None


def assert_chunk_valid(chunk: DocumentChunk):
    """Valide qu'un chunk est bien formé"""
    assert chunk.id is not None
    assert chunk.document_id is not None
    assert len(chunk.content) > 0
    assert chunk.start_char >= 0
    assert chunk.end_char > chunk.start_char
    assert isinstance(chunk.metadata, dict)


def assert_vector_store_functional(store):
    """Valide qu'un vector store est fonctionnel"""
    assert store.is_initialized
    assert hasattr(store, 'search')
    assert hasattr(store, 'add_chunks')
    assert hasattr(store, 'get_stats')
=======
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
>>>>>>> origin/main
