"""
Pydantic models for the Enterprise RAG System.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


# Enums
class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document type."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    AUDIO = "audio"
    IMAGE = "image"


class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchType(str, Enum):
    """Search type."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


# Base models
class TimestampedModel(BaseModel):
    """Base model with timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UUIDModel(BaseModel):
    """Base model with UUID."""
    id: UUID = Field(default_factory=uuid4)


# Document models
class DocumentMetadata(BaseModel):
    """Document metadata."""
    title: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    page_count: Optional[int] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(UUIDModel, TimestampedModel):
    """Document chunk with embeddings."""
    document_id: UUID
    content: str
    chunk_index: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Document(UUIDModel, TimestampedModel):
    """Document model."""
    filename: str
    original_filename: str
    file_path: str
    document_type: DocumentType
    status: DocumentStatus = DocumentStatus.PENDING
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    content: Optional[str] = None
    chunks: List[DocumentChunk] = Field(default_factory=list)
    processing_error: Optional[str] = None
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None


# Agent models
class AgentTask(UUIDModel, TimestampedModel):
    """Agent task model."""
    agent_name: str
    task_type: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: AgentStatus = AgentStatus.IDLE
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    parent_task_id: Optional[UUID] = None


class AgentResponse(BaseModel):
    """Agent response model."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    agent_name: str


# Search models
class SearchQuery(BaseModel):
    """Search query model."""
    query: str
    search_type: SearchType = SearchType.HYBRID
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    rerank: bool = True
    user_id: Optional[UUID] = None


class SearchResult(BaseModel):
    """Search result model."""
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    document_metadata: Optional[DocumentMetadata] = None


class SearchResponse(BaseModel):
    """Search response model."""
    results: List[SearchResult]
    total_results: int
    query: str
    search_type: SearchType
    execution_time: float


# Query models
class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., regex="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QueryRequest(BaseModel):
    """Query request model."""
    query: str
    conversation_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    search_params: Optional[SearchQuery] = None
    stream: bool = False


class QueryResponse(BaseModel):
    """Query response model."""
    response: str
    sources: List[SearchResult] = Field(default_factory=list)
    conversation_id: UUID
    message_id: UUID = Field(default_factory=uuid4)
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None
    execution_time: float


# User and permission models
class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(UUIDModel, TimestampedModel):
    """User model."""
    username: str
    email: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    organization_id: Optional[UUID] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)


class Organization(UUIDModel, TimestampedModel):
    """Organization model."""
    name: str
    description: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


# Feedback models
class FeedbackType(str, Enum):
    """Feedback type."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class Feedback(UUIDModel, TimestampedModel):
    """Feedback model."""
    user_id: UUID
    query_id: UUID
    feedback_type: FeedbackType
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Configuration models
class EmbeddingConfig(BaseModel):
    """Embedding configuration."""
    model: str
    dimension: int
    provider: str = "openai"  # Supporté: openai, cohere, sothemaai
    batch_size: int = 100
    # Configuration spécifique SothemaAI
    sothemaai_base_url: Optional[str] = None
    sothemaai_api_key: Optional[str] = None


class LLMConfig(BaseModel):
    """LLM configuration."""
    model: str
    provider: str = "openai"  # Supporté: openai, cohere, ollama, sothemaai
    temperature: float = Field(0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(4000, ge=1)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    # Configuration spécifique SothemaAI
    sothemaai_base_url: Optional[str] = None
    sothemaai_api_key: Optional[str] = None


class ProcessingConfig(BaseModel):
    """Document processing configuration."""
    chunk_size: int = Field(1000, ge=100)
    chunk_overlap: int = Field(200, ge=0)
    enable_ocr: bool = True
    ocr_language: str = "eng"
    enable_audio_transcription: bool = True


# API models
class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    components: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Success response model."""
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# File upload models
class FileUploadResponse(BaseModel):
    """File upload response."""
    document_id: UUID
    filename: str
    status: DocumentStatus
    message: str


# Analytics models
class AnalyticsMetric(BaseModel):
    """Analytics metric."""
    metric_name: str
    value: Union[int, float, str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = Field(default_factory=dict)


class SystemStats(BaseModel):
    """System statistics."""
    total_documents: int
    total_chunks: int
    total_queries: int
    avg_response_time: float
    active_users: int
    storage_used_mb: float
