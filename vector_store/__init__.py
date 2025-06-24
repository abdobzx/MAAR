"""
Module Vector Store pour la plateforme MAR
Support FAISS et Chroma pour la recherche vectorielle
"""

from .faiss_store import FAISSVectorStore
from .chroma_store import ChromaVectorStore
from .base import BaseVectorStore
from .ingestion import DocumentIngestion
from .models import Document, QueryResult
from .factory import create_vector_store

__all__ = [
    "BaseVectorStore",
    "FAISSVectorStore", 
    "ChromaVectorStore",
    "DocumentIngestion",
    "Document",
    "QueryResult",
    "create_vector_store"
]
