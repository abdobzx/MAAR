"""
Core configuration module for the Enterprise RAG System.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(default="postgresql://user:password@localhost:5432/mar_test")
    echo: bool = Field(default=False)
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    
    model_config = {
        "env_prefix": "DATABASE_",
        "case_sensitive": False
    }


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field(default="redis://localhost:6379/0")
    password: Optional[str] = Field(default=None)
    db: int = Field(default=0)
    max_connections: int = Field(default=20)
    
    model_config = {
        "env_prefix": "REDIS_",
        "case_sensitive": False
    }


class VectorDBSettings(BaseSettings):
    """Vector database configuration settings."""
    
    # Qdrant settings
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_api_key: Optional[str] = Field(default=None)
    qdrant_collection_name: str = Field(default="documents")
    
    # Weaviate settings
    weaviate_url: str = Field(default="http://localhost:8080")
    weaviate_api_key: Optional[str] = Field(default=None)
    weaviate_class_name: str = Field(default="Document")
    
    # Default vector database
    default_provider: str = Field(default="qdrant")
    
    @field_validator("default_provider")
    @classmethod
    def validate_provider(cls, v):
        allowed = ["qdrant", "weaviate"]
        if v not in allowed:
            raise ValueError(f"Vector DB provider must be one of {allowed}")
        return v

    model_config = {
        "env_prefix": "VECTOR_DB_",
        "case_sensitive": False
    }


class LLMSettings(BaseSettings):
    """LLM configuration settings."""
    
    # Cohere settings
    cohere_api_key: Optional[str] = Field(default=None)
    cohere_model: str = Field(default="command-r-plus")
    
    # Ollama settings
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3:8b")
    
    # Embedding settings
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)
    
    # Default LLM provider
    default_provider: str = Field(default="sothemaai")
    
    @field_validator("default_provider")
    @classmethod
    def validate_llm_provider(cls, v):
        allowed = ["sothemaai", "cohere", "ollama"]
        if v not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}")
        return v
    
    # Configuration SothemaAI
    sothemaai_base_url: Optional[str] = Field(default=None)
    sothemaai_api_key: Optional[str] = Field(default=None)
    sothemaai_timeout: int = Field(default=30)
    
    model_config = {
        "env_prefix": "LLM_",
        "case_sensitive": False
    }


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(...)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    
    # Keycloak settings
    keycloak_server_url: Optional[str] = Field(default=None)
    keycloak_realm: Optional[str] = Field(default=None)
    keycloak_client_id: Optional[str] = Field(default=None)
    keycloak_client_secret: Optional[str] = Field(default=None)
    
    # CORS settings
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8080"])
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {
        "env_prefix": "SECURITY_",
        "case_sensitive": False
    }


class StorageSettings(BaseSettings):
    """Storage configuration settings."""
    
    # MinIO/S3 settings
    endpoint: str = Field(default="localhost:9000")
    access_key: str = Field(default="minioadmin")
    secret_key: str = Field(default="minioadmin")
    bucket_name: str = Field(default="rag-documents")
    secure: bool = Field(default=False)
    
    # File processing settings
    max_file_size_mb: int = Field(default=100)
    allowed_extensions: List[str] = Field(default=[".pdf", ".docx", ".txt", ".md", ".html", ".mp3", ".wav", ".m4a"])
    
    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    model_config = {
        "env_prefix": "STORAGE_",
        "case_sensitive": False
    }


class ProcessingSettings(BaseSettings):
    """Processing configuration settings."""
    
    # Document processing
    max_workers: int = Field(default=4)
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    
    # Audio processing
    whisper_model: str = Field(default="tiny")
    audio_sample_rate: int = Field(default=16000)
    
    # OCR settings
    tesseract_lang: str = Field(default="fra+eng")
    
    model_config = {
        "env_prefix": "PROCESSING_",
        "case_sensitive": False
    }


class CelerySettings(BaseSettings):
    """Celery configuration settings."""
    
    broker_url: str = Field(default="redis://localhost:6379/1")
    result_backend: str = Field(default="redis://localhost:6379/1")
    task_serializer: str = Field(default="json")
    result_serializer: str = Field(default="json")
    accept_content: List[str] = Field(default=["json"])
    timezone: str = Field(default="UTC")
    enable_utc: bool = Field(default=True)
    
    model_config = {
        "env_prefix": "CELERY_",
        "case_sensitive": False
    }


class MonitoringSettings(BaseSettings):
    """Monitoring configuration settings."""
    
    # Prometheus settings
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=8090)
    
    # Grafana settings
    grafana_url: str = Field(default="http://localhost:3000")
    grafana_api_key: Optional[str] = Field(default=None)
    
    # ELK settings
    elasticsearch_url: str = Field(default="http://localhost:9200")
    kibana_url: str = Field(default="http://localhost:5601")
    
    # Health check settings
    health_check_interval: int = Field(default=30)
    
    model_config = {
        "env_prefix": "MONITORING_",
        "case_sensitive": False
    }


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application settings
    app_name: str = Field(default="Enterprise RAG System")
    version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    environment: str = Field(default="development")
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8", 
        "case_sensitive": False
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Export settings instance


# Export settings instance - lazy initialization
settings = None

def get_app_settings() -> Settings:
    """Get application settings with lazy initialization."""
    global settings
    if settings is None:
        settings = get_settings()
    return settings
