"""
Vectorization agent for the Enterprise RAG System.
Handles text chunking, embedding generation, and vector database storage.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Imports conditionnels pour les fournisseurs (OpenAI supprimé)
try:
    import cohere
except ImportError:
    cohere = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from langdetect import detect as detect_language
except ImportError:
    detect_language = None

from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.exceptions import EmbeddingError, ErrorCodes
from core.logging import LoggerMixin, log_agent_action, log_error
from core.models import Document, DocumentChunk
from core.providers import SothemaAIProvider


class TextChunker:
    """Advanced text chunking with semantic awareness."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Find the best split point
            chunk_end = self._find_split_point(text, start, end)
            chunk = text[start:chunk_end]
            
            if chunk.strip():
                chunks.append(chunk)
            
            start = chunk_end - self.chunk_overlap
            if start < 0:
                start = 0
        
        return chunks
    
    def _find_split_point(self, text: str, start: int, max_end: int) -> int:
        """Find the best point to split the text."""
        for separator in self.separators:
            # Look for separator near the end
            sep_pos = text.rfind(separator, start, max_end)
            if sep_pos != -1:
                return sep_pos + len(separator)
        
        return max_end
    
    def semantic_chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """Split text using semantic boundaries (paragraphs, sentences)."""
        # First split by paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= self.chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # If paragraph is too long, split it further
                if len(paragraph) > self.chunk_size:
                    paragraph_chunks = self.chunk_text(paragraph)
                    chunks.extend(paragraph_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get model name."""
        pass


class SothemaAIEmbeddingProvider(EmbeddingProvider):
    """SothemaAI embedding provider - Compatible with Mistral 7B and LLAMA 4."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self._dimension = 1536  # Standard embedding dimension
        
        from core.models import LLMConfig
        config = LLMConfig(
            model="default",
            provider="sothemaai",
            sothemaai_base_url=base_url,
            sothemaai_api_key=api_key
        )
        self.provider = SothemaAIProvider(config)
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using SothemaAI API."""
        try:
            embeddings = []
            for text in texts:
                embedding = await self.provider.generate_embedding(text)
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate SothemaAI embeddings: {str(e)}",
                error_code=ErrorCodes.EMBEDDING_GENERATION_FAILED
            )
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def model_name(self) -> str:
        return "sothemaai-embeddings"


class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere embedding provider."""
    
    def __init__(self, model: str = "embed-multilingual-v3.0", api_key: Optional[str] = None):
        if not cohere:
            raise ImportError("Cohere library not available")
        
        self.model = model
        self.client = cohere.AsyncClient(api_key=api_key or settings.llm.cohere_api_key)
        self._dimension = 1024  # Cohere embedding dimension
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Cohere API."""
        try:
            response = await self.client.embed(
                texts=texts,
                model=self.model,
                input_type="search_document"
            )
            return response.embeddings
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate Cohere embeddings: {str(e)}",
                error_code=ErrorCodes.EMBEDDING_GENERATION_FAILED
            )
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def model_name(self) -> str:
        return self.model


class SentenceTransformerProvider(EmbeddingProvider):
    """Local sentence transformer embedding provider."""
    
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        if not SentenceTransformer:
            raise ImportError("SentenceTransformers library not available")
        
        self.model_name_str = model
        self.model = SentenceTransformer(model)
        self._dimension = self.model.get_sentence_embedding_dimension()
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.model.encode,
                texts
            )
            return embeddings.tolist()
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate SentenceTransformer embeddings: {str(e)}",
                error_code=ErrorCodes.EMBEDDING_GENERATION_FAILED
            )
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def model_name(self) -> str:
        return self.model_name_str


class VectorizationAgent(LoggerMixin):
    """Vectorization agent for document chunking and embedding generation."""
    
    def __init__(self):
        self.chunker = TextChunker(
            chunk_size=settings.processing.chunk_size,
            chunk_overlap=settings.processing.chunk_overlap
        )
        self.embedding_providers = self._initialize_providers()
        self.default_provider = self._get_default_provider()
    
    def _initialize_providers(self) -> Dict[str, EmbeddingProvider]:
        """Initialize available embedding providers."""
        providers = {}
        
        # SothemaAI provider (priorité si configuré)
        if (hasattr(settings.llm, 'sothemaai_base_url') and 
            hasattr(settings.llm, 'sothemaai_api_key') and
            settings.llm.sothemaai_base_url and 
            settings.llm.sothemaai_api_key):
            try:
                providers["sothemaai"] = SothemaAIEmbeddingProvider(
                    base_url=settings.llm.sothemaai_base_url,
                    api_key=settings.llm.sothemaai_api_key
                )
                self.logger.info("SothemaAI embedding provider initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize SothemaAI embedding provider: {str(e)}")
        
        # Cohere provider
        if settings.llm.cohere_api_key and cohere:
            try:
                providers["cohere"] = CohereEmbeddingProvider()
                self.logger.info("Cohere embedding provider initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Cohere embedding provider: {str(e)}")
        
        # Local sentence transformer
        if SentenceTransformer:
            try:
                providers["sentence-transformer"] = SentenceTransformerProvider()
                self.logger.info("SentenceTransformer provider initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize SentenceTransformer provider: {str(e)}")
        
        return providers
    
    def _get_default_provider(self) -> EmbeddingProvider:
        """Get the default embedding provider."""
        # Priorité à SothemaAI si USE_SOTHEMAAI_ONLY est activé
        use_sothemaai_only = getattr(settings, 'USE_SOTHEMAAI_ONLY', False)
        if use_sothemaai_only and "sothemaai" in self.embedding_providers:
            self.logger.info("Using SothemaAI as default provider (USE_SOTHEMAAI_ONLY enabled)")
            return self.embedding_providers["sothemaai"]
        
        # Sinon utiliser le fournisseur configuré
        provider_name = getattr(settings.llm, 'embedding_provider', 'openai')
        
        if provider_name in self.embedding_providers:
            self.logger.info(f"Using {provider_name} as default provider")
            return self.embedding_providers[provider_name]
        
        # Fallback vers SothemaAI si disponible
        if "sothemaai" in self.embedding_providers:
            self.logger.info("Falling back to SothemaAI provider")
            return self.embedding_providers["sothemaai"]
        
        # Fallback to first available provider
        if self.embedding_providers:
            provider_name = next(iter(self.embedding_providers.keys()))
            self.logger.info(f"Falling back to first available provider: {provider_name}")
            return next(iter(self.embedding_providers.values()))
        
        raise EmbeddingError(
            "No embedding providers available",
            error_code=ErrorCodes.EMBEDDING_MODEL_UNAVAILABLE
        )
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of the text."""
        if not detect_language:
            return None
        
        try:
            return detect_language(text)
        except:
            return None
    
    def _select_optimal_provider(self, text: str, metadata: Dict[str, Any]) -> EmbeddingProvider:
        """Select the optimal embedding provider based on text characteristics."""
        language = self._detect_language(text)
        
        # Language-specific provider selection
        if language and language != 'en':
            # Prefer multilingual models for non-English text
            if "cohere" in self.embedding_providers:
                return self.embedding_providers["cohere"]
            elif "sothemaai" in self.embedding_providers:
                return self.embedding_providers["sothemaai"]
        
        # Default to configured provider
        return self.default_provider
    
    async def vectorize_document(
        self,
        document: Document,
        use_semantic_chunking: bool = True
    ) -> List[DocumentChunk]:
        """Vectorize a document into chunks with embeddings."""
        
        log_agent_action(
            agent_name="VectorizationAgent",
            action="vectorize_document",
            document_id=str(document.id),
            content_length=len(document.content or "")
        )
        
        try:
            if not document.content:
                raise EmbeddingError(
                    "Document has no content to vectorize",
                    error_code=ErrorCodes.EMBEDDING_GENERATION_FAILED
                )
            
            # Choose chunking strategy
            if use_semantic_chunking:
                chunks_text = self.chunker.semantic_chunk_text(
                    document.content,
                    document.metadata.dict()
                )
            else:
                chunks_text = self.chunker.chunk_text(
                    document.content,
                    document.metadata.dict()
                )
            
            # Select optimal embedding provider
            provider = self._select_optimal_provider(
                document.content,
                document.metadata.dict()
            )
            
            # Generate embeddings in batches
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(chunks_text), batch_size):
                batch = chunks_text[i:i + batch_size]
                embeddings = await provider.generate_embeddings(batch)
                all_embeddings.extend(embeddings)
            
            # Create DocumentChunk objects
            document_chunks = []
            
            for i, (chunk_text, embedding) in enumerate(zip(chunks_text, all_embeddings)):
                chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk_text,
                    chunk_index=i,
                    embedding=embedding,
                    metadata={
                        "embedding_model": provider.model_name,
                        "embedding_dimension": provider.dimension,
                        "language": self._detect_language(chunk_text),
                        "chunk_length": len(chunk_text),
                        "chunking_strategy": "semantic" if use_semantic_chunking else "fixed"
                    }
                )
                document_chunks.append(chunk)
            
            self.logger.info(
                "Document vectorized successfully",
                document_id=str(document.id),
                num_chunks=len(document_chunks),
                embedding_model=provider.model_name
            )
            
            return document_chunks
            
        except Exception as e:
            log_error(e, {
                "agent": "VectorizationAgent",
                "document_id": str(document.id)
            })
            raise
    
    async def vectorize_batch(
        self,
        documents: List[Document],
        max_workers: int = 4
    ) -> Dict[UUID, List[DocumentChunk]]:
        """Vectorize multiple documents concurrently."""
        
        semaphore = asyncio.Semaphore(max_workers)
        
        async def vectorize_single(doc: Document) -> Tuple[UUID, List[DocumentChunk]]:
            async with semaphore:
                chunks = await self.vectorize_document(doc)
                return doc.id, chunks
        
        tasks = [vectorize_single(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        vectorized_docs = {}
        for result in results:
            if isinstance(result, Exception):
                log_error(result, {
                    "agent": "VectorizationAgent",
                    "operation": "batch_vectorization"
                })
            else:
                doc_id, chunks = result
                vectorized_docs[doc_id] = chunks
        
        return vectorized_docs
    
    async def re_vectorize_document(
        self,
        document: Document,
        new_provider: Optional[str] = None
    ) -> List[DocumentChunk]:
        """Re-vectorize a document with a different provider or updated content."""
        
        # Use specific provider if requested
        if new_provider and new_provider in self.embedding_providers:
            original_provider = self.default_provider
            self.default_provider = self.embedding_providers[new_provider]
            
            try:
                chunks = await self.vectorize_document(document)
                return chunks
            finally:
                self.default_provider = original_provider
        else:
            return await self.vectorize_document(document)
