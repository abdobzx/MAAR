"""
Configuration et fixtures pour les tests
"""

import pytest
import asyncio
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
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
