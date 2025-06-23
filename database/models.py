"""
Database models and connection management.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

from core.config import settings
from core.models import DocumentStatus, DocumentType, UserRole

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Organization(Base, UUIDMixin, TimestampMixin):
    """Organization table."""
    
    __tablename__ = "organizations"
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    settings = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")


class User(Base, UUIDMixin, TimestampMixin):
    """User table."""
    
    __tablename__ = "users"
    
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    preferences = Column(JSON, default=dict)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    documents = relationship("Document", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")
    queries = relationship("Query", back_populates="user")


class Document(Base, UUIDMixin, TimestampMixin):
    """Document table."""
    
    __tablename__ = "documents"
    
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    content = Column(Text)
    doc_metadata = Column(JSON, default=dict)
    processing_error = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    
    # Relationships
    user = relationship("User", back_populates="documents")
    organization = relationship("Organization", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base, UUIDMixin, TimestampMixin):
    """Document chunk table."""
    
    __tablename__ = "document_chunks"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_char = Column(Integer)
    end_char = Column(Integer)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


class Query(Base, UUIDMixin, TimestampMixin):
    """Query table for storing user queries and responses."""
    
    __tablename__ = "queries"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    conversation_id = Column(UUID(as_uuid=True))
    query_text = Column(Text, nullable=False)
    response_text = Column(Text)
    search_results = Column(JSON, default=list)
    confidence = Column(Float)
    tokens_used = Column(Integer)
    execution_time = Column(Float)
    context = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="queries")
    feedback = relationship("Feedback", back_populates="query")


class Feedback(Base, UUIDMixin, TimestampMixin):
    """Feedback table."""
    
    __tablename__ = "feedback"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id"), nullable=False)
    feedback_type = Column(String(50), nullable=False)
    rating = Column(Integer)
    comment = Column(Text)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    query = relationship("Query", back_populates="feedback")


class AgentTask(Base, UUIDMixin, TimestampMixin):
    """Agent task table."""
    
    __tablename__ = "agent_tasks"
    
    agent_name = Column(String(255), nullable=False, index=True)
    task_type = Column(String(255), nullable=False, index=True)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON)
    status = Column(String(50), default="idle", index=True)
    error_message = Column(Text)
    execution_time = Column(Float)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("agent_tasks.id"))
    
    # Self-referential relationship for parent-child tasks
    children = relationship("AgentTask", backref="parent", remote_side="AgentTask.id")


class SystemMetrics(Base, UUIDMixin, TimestampMixin):
    """System metrics table."""
    
    __tablename__ = "system_metrics"
    
    metric_name = Column(String(255), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# Database connection and session management
class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        self.engine = create_async_engine(
            settings.database.url,
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def create_tables(self):
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self):
        """Drop all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def get_session(self) -> AsyncSession:
        """Get an async database session."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close the database connection."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
async def get_db_session():
    """Dependency to get database session in FastAPI routes."""
    async for session in db_manager.get_session():
        yield session
