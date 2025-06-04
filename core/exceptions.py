"""
Custom exceptions for the Enterprise RAG System.
"""

from typing import Any, Dict, Optional


class RAGSystemException(Exception):
    """Base exception for RAG system errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)


class ConfigurationError(RAGSystemException):
    """Raised when there's a configuration error."""
    pass


class DatabaseError(RAGSystemException):
    """Raised when there's a database error."""
    pass


class VectorDBError(RAGSystemException):
    """Raised when there's a vector database error."""
    pass


class DocumentProcessingError(RAGSystemException):
    """Raised when document processing fails."""
    pass


class EmbeddingError(RAGSystemException):
    """Raised when embedding generation fails."""
    pass


class LLMError(RAGSystemException):
    """Raised when LLM operations fail."""
    pass


class AuthenticationError(RAGSystemException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(RAGSystemException):
    """Raised when authorization fails."""
    pass


class ValidationError(RAGSystemException):
    """Raised when validation fails."""
    pass


class ProcessingError(RAGSystemException):
    """Raised when processing operations fail."""
    pass


class StorageError(RAGSystemException):
    """Raised when storage operations fail."""
    pass


class AgentError(RAGSystemException):
    """Raised when agent operations fail."""
    pass


class RetryableError(RAGSystemException):
    """Raised for errors that can be retried."""
    pass


class RateLimitError(RAGSystemException):
    """Raised when rate limits are exceeded."""
    pass


class ResourceNotFoundError(RAGSystemException):
    """Raised when a requested resource is not found."""
    pass


class DuplicateResourceError(RAGSystemException):
    """Raised when trying to create a duplicate resource."""
    pass


class OrchestrationError(RAGSystemException):
    """Raised when orchestration operations fail."""
    pass


# Error code constants
class ErrorCodes:
    """Error codes for different types of failures."""
    
    # Configuration errors
    INVALID_CONFIG = "INVALID_CONFIG"
    MISSING_CONFIG = "MISSING_CONFIG"
    
    # Database errors
    CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    QUERY_FAILED = "DB_QUERY_FAILED"
    TRANSACTION_FAILED = "DB_TRANSACTION_FAILED"
    
    # Vector database errors
    VECTOR_DB_CONNECTION_FAILED = "VECTOR_DB_CONNECTION_FAILED"
    VECTOR_SEARCH_FAILED = "VECTOR_SEARCH_FAILED"
    VECTOR_INSERT_FAILED = "VECTOR_INSERT_FAILED"
    VECTOR_DELETE_FAILED = "VECTOR_DELETE_FAILED"
    
    # Document processing errors
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    OCR_FAILED = "OCR_FAILED"
    AUDIO_TRANSCRIPTION_FAILED = "AUDIO_TRANSCRIPTION_FAILED"
    
    # Embedding errors
    EMBEDDING_GENERATION_FAILED = "EMBEDDING_GENERATION_FAILED"
    EMBEDDING_MODEL_UNAVAILABLE = "EMBEDDING_MODEL_UNAVAILABLE"
    
    # LLM errors
    LLM_REQUEST_FAILED = "LLM_REQUEST_FAILED"
    LLM_RESPONSE_INVALID = "LLM_RESPONSE_INVALID"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_CONTEXT_TOO_LONG = "LLM_CONTEXT_TOO_LONG"
    
    # Authentication/Authorization errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    
    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Storage errors
    STORAGE_CONNECTION_FAILED = "STORAGE_CONNECTION_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    
    # Agent errors
    AGENT_INITIALIZATION_FAILED = "AGENT_INITIALIZATION_FAILED"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"
    AGENT_COMMUNICATION_FAILED = "AGENT_COMMUNICATION_FAILED"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
