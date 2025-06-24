from typing import Optional
from .faiss_store import FAISSVectorStore
from .chroma_store import ChromaVectorStore
from .base import BaseVectorStore
import os

async def create_vector_store(config: dict, store_type: Optional[str] = None) -> BaseVectorStore:
    """
    Factory function to create a vector store instance.
    """
    if store_type is None:
        store_type = os.getenv("VECTOR_STORE_TYPE", "faiss")

    persist_directory = config.get("persist_directory")
    if not persist_directory:
        raise ValueError("persist_directory must be set in the vector store config")

    if store_type == "faiss":
        store = FAISSVectorStore(
            storage_path=persist_directory,
            embedding_dim=config.get("embedding_dim", 384)
        )
    elif store_type == "chroma":
        store = ChromaVectorStore(
            storage_path=persist_directory,
            # embedding_function might be needed here
        )
    else:
        raise ValueError(f"Unsupported vector store type: {store_type}")
    
    await store.initialize()
    return store
