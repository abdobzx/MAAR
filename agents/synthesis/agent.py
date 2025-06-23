"""
Synthesis agent for the Enterprise RAG System.
Handles LLM-based response generation with citations and source tracking.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union, AsyncIterator
from uuid import UUID, uuid4

# Imports conditionnels pour les fournisseurs (OpenAI supprimé)
try:
    import cohere
except ImportError:
    cohere = None

try:
    import ollama
except ImportError:
    ollama = None

from core.config import settings
from core.exceptions import LLMError, ErrorCodes
from core.logging import LoggerMixin, log_agent_action, log_error, log_performance
from core.models import (
    ChatMessage, QueryRequest, QueryResponse, SearchResult, LLMConfig
)
from core.providers import AIProviderManager
from database.models import Query as DBQuery

# Import SothemaAI provider conditionally
try:
    from core.providers.sothemaai_provider import SothemaAIProvider as CoreSothemaAIProvider
    SOTHEMAAI_AVAILABLE = True
except ImportError:
    CoreSothemaAIProvider = None
    SOTHEMAAI_AVAILABLE = False


class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Generate response from LLM."""
        raise NotImplementedError
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        raise NotImplementedError


class SothemaAILLMProvider(LLMProvider):
    """Wrapper pour SothemaAI provider pour compatibilité avec LLMProvider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not SOTHEMAAI_AVAILABLE or CoreSothemaAIProvider is None:
            raise ImportError("SothemaAI provider not available")
        
        # Créer une instance du provider core
        self.core_provider = CoreSothemaAIProvider()
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Generate response using SothemaAI."""
        try:
            # Convert messages to string format for SothemaAI
            prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
            
            if stream:
                # Return a simple generator for streaming
                async def response_generator():
                    response = await self.core_provider.generate_text(
                        prompt=prompt,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature
                    )
                    yield response
                
                return response_generator()
            else:
                response = await self.core_provider.generate_text(
                    prompt=prompt,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )
                return response
                
        except Exception as e:
            raise LLMError(
                f"SothemaAI API error: {str(e)}",
                error_code=ErrorCodes.LLM_REQUEST_FAILED
            )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        # This would be implemented if needed
        raise NotImplementedError("Embedding generation not implemented for SothemaAI wrapper")


class CohereProvider(LLMProvider):
    """Cohere LLM provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if cohere is None:
            raise ImportError("Cohere library not available")
        
        self.client = cohere.AsyncClient(
            api_key=settings.llm.cohere_api_key
        )
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Generate response using Cohere API."""
        try:
            # Convert messages to Cohere format
            chat_history = []
            message = ""
            
            for msg in messages:
                if msg.role == "user":
                    message = msg.content
                elif msg.role == "assistant":
                    chat_history.append({"role": "CHATBOT", "message": msg.content})
                elif msg.role == "system":
                    chat_history.append({"role": "SYSTEM", "message": msg.content})
            
            response = await self.client.chat(
                model=self.config.model,
                message=message,
                chat_history=chat_history,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs
            )
            
            if stream:
                # Return a simple generator for streaming
                async def response_generator():
                    yield response.text
                
                return response_generator()
            else:
                return response.text
                
        except Exception as e:
            raise LLMError(
                f"Cohere API error: {str(e)}",
                error_code=ErrorCodes.LLM_REQUEST_FAILED
            )


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if ollama is None:
            raise ImportError("Ollama library not available")
            
        self.client = ollama.AsyncClient(
            host=settings.llm.ollama_base_url
        )
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Generate response using Ollama."""
        try:
            # Convert messages to Ollama format
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            response = await self.client.chat(
                model=self.config.model,
                messages=ollama_messages,
                stream=stream,
                options={
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                    "top_p": self.config.top_p,
                    **kwargs
                }
            )
            
            if stream:
                # Return a simple generator for streaming  
                async def response_generator():
                    # Handle different response types from Ollama
                    if isinstance(response, dict) and 'message' in response:
                        yield response['message']['content']
                    else:
                        yield str(response)
                
                return response_generator()
            else:
                # Handle different response types from Ollama
                if isinstance(response, dict) and 'message' in response:
                    return response['message']['content']
                else:
                    return str(response)
                
        except Exception as e:
            raise LLMError(
                f"Ollama API error: {str(e)}",
                error_code=ErrorCodes.LLM_REQUEST_FAILED
            )


class PromptTemplate:
    """Template for generating prompts."""
    
    SYSTEM_PROMPT = """You are an intelligent assistant helping users find information from a knowledge base. 
Your task is to provide accurate, helpful, and well-structured answers based on the provided context.

Guidelines:
1. Answer the question using only the information provided in the context
2. If the context doesn't contain enough information, say so clearly
3. Always cite your sources using the provided source IDs
4. Be concise but comprehensive
5. Maintain a professional and helpful tone
6. If asked about something not in the context, explain that you can only answer based on the provided documents

Format your response as follows:
- Start with a direct answer to the question
- Provide supporting details from the context
- End with source citations in the format [Source: ID]
"""
    
    CONTEXT_TEMPLATE = """Context from relevant documents:

{context}

Question: {question}

Please provide a comprehensive answer based on the context above."""
    
    RAG_PROMPT_TEMPLATE = """Based on the following context from the knowledge base, please answer the user's question.

Context:
{context}

Question: {question}

Instructions:
- Use only the information provided in the context
- Cite sources using [Source: {source_id}] format
- If the context is insufficient, clearly state this
- Provide a helpful and accurate response

Answer:"""
    
    SUMMARY_PROMPT = """Please provide a concise summary of the following text, highlighting the key points:

{text}

Summary:"""
    
    @classmethod
    def format_rag_prompt(
        cls,
        question: str,
        search_results: List[SearchResult],
        max_context_length: int = 4000
    ) -> str:
        """Format a RAG prompt with context and question."""
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(search_results):
            # Safe access to document filename - DocumentMetadata doesn't have filename
            # We need to use the metadata field or document_metadata dict
            doc_filename = "Unknown"
            if result.document_metadata:
                # DocumentMetadata is a Pydantic model, check for custom_fields or metadata
                if hasattr(result.document_metadata, 'custom_fields') and result.document_metadata.custom_fields:
                    doc_filename = result.document_metadata.custom_fields.get('filename', 'Unknown')
                elif hasattr(result.document_metadata, 'source') and result.document_metadata.source:
                    doc_filename = result.document_metadata.source
                elif hasattr(result.document_metadata, 'title') and result.document_metadata.title:
                    doc_filename = result.document_metadata.title
            
            # Also check result.metadata for filename information
            if doc_filename == "Unknown" and result.metadata:
                doc_filename = result.metadata.get('filename', result.metadata.get('source', 'Unknown'))
            
            source_info = f"[Source: {i+1}] Document: {doc_filename}\n"
            content = f"{source_info}{result.content}\n\n"
            
            if current_length + len(content) > max_context_length:
                break
            
            context_parts.append(content)
            current_length += len(content)
        
        context = "".join(context_parts)
        
        return cls.RAG_PROMPT_TEMPLATE.format(
            context=context,
            question=question
        )
    
    @classmethod
    def format_chat_prompt(
        cls,
        messages: List[ChatMessage],
        search_results: List[SearchResult]
    ) -> List[ChatMessage]:
        """Format chat messages with context."""
        if not search_results:
            return messages
        
        # Get the last user message
        last_user_message = None
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_message = msg
                break
        
        if not last_user_message:
            return messages
        
        # Format context
        context_parts = []
        for i, result in enumerate(search_results):
            source_info = f"[Source: {i+1}]"
            content = f"{source_info} {result.content}\n"
            context_parts.append(content)
        
        context = "\n".join(context_parts)
        
        # Create new messages with context
        formatted_messages = messages[:-1]  # All except last user message
        
        # Add system message with context
        system_message = ChatMessage(
            role="system",
            content=f"{cls.SYSTEM_PROMPT}\n\nRelevant context:\n{context}"
        )
        
        # Add user question
        user_message = ChatMessage(
            role="user",
            content=last_user_message.content
        )
        
        return [system_message] + formatted_messages + [user_message]


class ResponseGenerator:
    """Handles response generation and streaming."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        stream: bool = False
    ) -> Union[str, AsyncIterator[str]]:
        """Generate response using the LLM provider."""
        return await self.provider.generate_response(messages, stream)
    
    async def generate_with_fallback(
        self,
        messages: List[ChatMessage],
        fallback_providers: List[LLMProvider],
        stream: bool = False
    ) -> Union[str, AsyncIterator[str]]:
        """Generate response with fallback providers."""
        providers = [self.provider] + fallback_providers
        
        for provider in providers:
            try:
                result = await provider.generate_response(messages, stream)
                return result
            except Exception as e:
                log_error(e, {
                    "provider": provider.__class__.__name__,
                    "operation": "generate_response"
                })
                if provider == providers[-1]:  # Last provider
                    raise
                continue
        
        # This should never be reached due to the raise above, but for type safety
        raise LLMError(
            "All providers failed",
            error_code=ErrorCodes.LLM_REQUEST_FAILED
        )


class CitationManager:
    """Manages source citations and tracking."""
    
    def __init__(self):
        self.sources = {}
        self.citation_map = {}
    
    def add_sources(self, search_results: List[SearchResult]) -> None:
        """Add search results as sources."""
        for i, result in enumerate(search_results):
            source_id = i + 1
            self.sources[source_id] = {
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "content": result.content,
                "score": result.score,
                "metadata": result.metadata,
                "document_metadata": result.document_metadata
            }
            self.citation_map[str(result.chunk_id)] = source_id
    
    def get_citations(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract citations from response text."""
        import re
        
        citations = []
        # Find all citation patterns like [Source: 1] or [Source: ID]
        citation_pattern = r'\[Source:\s*(\d+)\]'
        matches = re.findall(citation_pattern, response_text)
        
        for match in matches:
            source_id = int(match)
            if source_id in self.sources:
                citations.append({
                    "source_id": source_id,
                    "chunk_id": self.sources[source_id]["chunk_id"],
                    "document_id": self.sources[source_id]["document_id"],
                    "document_metadata": self.sources[source_id]["document_metadata"],
                    "confidence": self.sources[source_id]["score"]
                })
        
        return citations
    
    def format_citations(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations for display."""
        if not citations:
            return ""
        
        formatted = "\n\nSources:\n"
        for citation in citations:
            doc_name = "Unknown Document"
            if citation.get("document_metadata"):
                doc_name = citation["document_metadata"].get("filename", doc_name)
            
            formatted += f"[{citation['source_id']}] {doc_name} (Confidence: {citation['confidence']:.2f})\n"
        
        return formatted


class SynthesisAgent(LoggerMixin):
    """Synthesis agent for LLM-based response generation."""
    
    def __init__(self):
        super().__init__()  # Initialize LoggerMixin
        
        # Initialisation du gestionnaire de fournisseurs AI
        self.provider_manager = AIProviderManager()
        
        # Configuration des fournisseurs traditionnels
        self.providers = self._initialize_providers()
        
        # Configuration du fournisseur SothemaAI si disponible
        self._setup_sothemaai_provider()
        
        # Sélection du fournisseur par défaut
        self.default_provider = self._get_default_provider()
        self.fallback_providers = self._get_fallback_providers()
        
        # Composants de génération
        self.response_generator = ResponseGenerator(self.default_provider)
        self.citation_manager = CitationManager()
    
    def _setup_sothemaai_provider(self):
        """Configure le fournisseur SothemaAI si les paramètres sont disponibles."""
        try:
            # Vérifier si SothemaAI est configuré et disponible
            if (SOTHEMAAI_AVAILABLE and
                hasattr(settings.llm, 'sothemaai_base_url') and 
                hasattr(settings.llm, 'sothemaai_api_key') and
                settings.llm.sothemaai_base_url and 
                settings.llm.sothemaai_api_key):
                
                # Créer la configuration pour SothemaAI
                config = LLMConfig(
                    model="default",  # SothemaAI utilise un modèle par défaut
                    provider="sothemaai",
                    temperature=0.1,
                    max_tokens=4000,
                    top_p=1.0,  # Add required top_p parameter
                    sothemaai_base_url=settings.llm.sothemaai_base_url,
                    sothemaai_api_key=settings.llm.sothemaai_api_key
                )
                
                # Créer le fournisseur SothemaAI
                sothemaai_provider = SothemaAILLMProvider(config)
                self.providers["sothemaai"] = sothemaai_provider
                
                self.logger.info("SothemaAI provider configured successfully")
                
        except Exception as e:
            self.logger.warning(f"Failed to setup SothemaAI provider: {str(e)}")

    def _initialize_providers(self) -> Dict[str, LLMProvider]:
        """Initialize available LLM providers (SothemaAI focused)."""
        providers = {}
        
        # Cohere
        if settings.llm.cohere_api_key:
            config = LLMConfig(
                model=settings.llm.cohere_model,
                provider="cohere",
                temperature=0.1,
                max_tokens=4000,
                top_p=1.0
            )
            providers["cohere"] = CohereProvider(config)
        
        # Ollama
        config = LLMConfig(
            model=settings.llm.ollama_model,
            provider="ollama",
            temperature=0.1,
            max_tokens=4000,
            top_p=1.0
        )
        providers["ollama"] = OllamaProvider(config)
        
        return providers
    
    def _get_default_provider(self) -> LLMProvider:
        """Get the default LLM provider."""
        provider_name = settings.llm.default_provider
        
        # Priorité à SothemaAI si USE_SOTHEMAAI_ONLY est activé
        use_sothemaai_only = getattr(settings, 'USE_SOTHEMAAI_ONLY', False)
        if use_sothemaai_only and "sothemaai" in self.providers:
            return self.providers["sothemaai"]
        
        # Vérifier si le fournisseur configuré est disponible
        if provider_name in self.providers:
            return self.providers[provider_name]
        
        # Fallback vers SothemaAI si disponible
        if "sothemaai" in self.providers:
            self.logger.info("Falling back to SothemaAI provider")
            return self.providers["sothemaai"]
        
        # Fallback to first available provider
        if self.providers:
            return next(iter(self.providers.values()))
        
        raise LLMError(
            "No LLM providers available",
            error_code=ErrorCodes.LLM_REQUEST_FAILED
        )
    
    def _get_fallback_providers(self) -> List[LLMProvider]:
        """Get fallback providers in order of preference."""
        fallback_order = ["sothemaai", "ollama", "cohere"]  # OpenAI supprimé
        fallbacks = []
        
        for provider_name in fallback_order:
            if (provider_name in self.providers and 
                self.providers[provider_name] != self.default_provider):
                fallbacks.append(self.providers[provider_name])
        
        return fallbacks
    
    async def generate_response(
        self,
        query_request: QueryRequest,
        search_results: List[SearchResult],
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> QueryResponse:
        """Generate a response based on query and search results."""
        
        log_agent_action(
            agent_name="SynthesisAgent",
            action="generate_response",
            query=query_request.query,
            num_sources=len(search_results),
            stream=query_request.stream
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Set up citation manager
            self.citation_manager.add_sources(search_results)
            
            # Prepare messages
            messages = []
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Format prompt with context
            if search_results:
                formatted_messages = PromptTemplate.format_chat_prompt(
                    messages + [ChatMessage(role="user", content=query_request.query)],
                    search_results
                )
            else:
                formatted_messages = messages + [
                    ChatMessage(role="user", content=query_request.query)
                ]
            
            # Generate response
            if query_request.stream:
                response_stream = await self.response_generator.generate_with_fallback(
                    formatted_messages,
                    self.fallback_providers,
                    stream=True
                )
                
                # For streaming, collect the response and return it
                response_parts = []
                try:
                    # Handle different types of response streams
                    if response_stream is None:
                        response_text = ""
                    elif isinstance(response_stream, str):
                        response_text = response_stream
                    elif hasattr(response_stream, '__aiter__'):
                        # Async iterator
                        try:
                            async for part in response_stream:
                                if part:
                                    response_parts.append(str(part))
                        except TypeError:
                            # If async iteration fails, treat as single value
                            response_parts.append(str(response_stream))
                        response_text = "".join(response_parts) if response_parts else str(response_stream)
                    else:
                        # Single response value
                        response_text = str(response_stream)
                        
                except Exception as e:
                    # If streaming fails, fallback to single response
                    self.logger.warning(f"Streaming failed, using single response: {e}")
                    response_text = str(response_stream) if response_stream else ""
            else:
                response_result = await self.response_generator.generate_with_fallback(
                    formatted_messages,
                    self.fallback_providers,
                    stream=False
                )
                response_text = str(response_result)
            
            # Extract citations
            citations = self.citation_manager.get_citations(response_text)
            
            # Create response object
            execution_time = asyncio.get_event_loop().time() - start_time
            
            query_response = QueryResponse(
                response=response_text,
                sources=search_results,
                conversation_id=query_request.conversation_id or uuid4(),
                confidence=self._calculate_confidence(search_results, response_text),
                tokens_used=self._estimate_tokens(formatted_messages, response_text),
                execution_time=execution_time
            )
            
            self.logger.info(
                "Response generated successfully",
                query=query_request.query,
                response_length=len(response_text),
                num_citations=len(citations),
                execution_time=execution_time
            )
            
            log_performance(
                operation="response_generation",
                duration=execution_time,
                tokens_used=query_response.tokens_used,
                num_sources=len(search_results)
            )
            
            return query_response
            
        except Exception as e:
            log_error(e, {
                "agent": "SynthesisAgent",
                "query": query_request.query,
                "num_sources": len(search_results)
            })
            raise
    
    async def save_query_response(
        self,
        query_request: QueryRequest,
        query_response: QueryResponse,
        db_session
    ):
        """Save query and response to database."""
        try:
            db_query = DBQuery(
                id=query_response.message_id,
                user_id=query_request.user_id,
                conversation_id=query_response.conversation_id,
                query_text=query_request.query,
                response_text=query_response.response,
                search_results=[result.dict() for result in query_response.sources],
                confidence=query_response.confidence,
                tokens_used=query_response.tokens_used,
                execution_time=query_response.execution_time,
                context=query_request.context
            )
            
            db_session.add(db_query)
            await db_session.commit()
            await db_session.refresh(db_query)
            
            return db_query
            
        except Exception as e:
            await db_session.rollback()
            log_error(e, {
                "agent": "SynthesisAgent",
                "operation": "save_query_response"
            })
            raise
    
    def _calculate_confidence(
        self,
        search_results: List[SearchResult],
        response_text: str
    ) -> float:
        """Calculate confidence score for the response."""
        if not search_results:
            return 0.1
        
        # Simple confidence calculation based on search result scores
        avg_score = sum(result.score for result in search_results) / len(search_results)
        
        # Adjust based on response length (longer responses might be more comprehensive)
        length_factor = min(1.0, len(response_text) / 500)
        
        # Adjust based on number of sources
        source_factor = min(1.0, len(search_results) / 3)
        
        confidence = avg_score * 0.6 + length_factor * 0.2 + source_factor * 0.2
        
        return min(1.0, confidence)
    
    def _estimate_tokens(
        self,
        messages: List[ChatMessage],
        response: str
    ) -> int:
        """Estimate token usage (simple approximation)."""
        # Simple estimation: ~4 characters per token
        total_chars = sum(len(msg.content) for msg in messages) + len(response)
        return total_chars // 4
    
    async def summarize_document(
        self,
        content: str,
        max_length: int = 200
    ) -> str:
        """Generate a summary of document content."""
        try:
            messages = [
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that creates concise summaries."
                ),
                ChatMessage(
                    role="user",
                    content=PromptTemplate.SUMMARY_PROMPT.format(text=content[:4000])
                )
            ]
            
            summary_result = await self.response_generator.generate_response(messages)
            summary = str(summary_result)
            
            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + "..."
            
            return summary
            
        except Exception as e:
            log_error(e, {"agent": "SynthesisAgent", "operation": "summarize_document"})
            return "Summary not available"
