"""
Core configuration module for the Enterprise RAG System.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field("postgresql://user:password@localhost:5432/mar_test", env="DATABASE_URL")
    echo: bool = Field(False, env="DATABASE_ECHO")
    pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")
    
    model_config = {
        "env_prefix": "DATABASE_",
        "case_sensitive": False
    }


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")
    max_connections: int = Field(20, env="REDIS_MAX_CONNECTIONS")
    
    model_config = {
        "env_prefix": "REDIS_",
        "case_sensitive": False
    }


class VectorDBSettings(BaseSettings):
    """Vector database configuration settings."""
    
    # Qdrant settings
    qdrant_host: str = Field("localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(None, env="QDRANT_API_KEY")
    qdrant_collection_name: str = Field("documents", env="QDRANT_COLLECTION_NAME")
    
    # Weaviate settings
    weaviate_url: str = Field("http://localhost:8080", env="WEAVIATE_URL")
    weaviate_api_key: Optional[str] = Field(None, env="WEAVIATE_API_KEY")
    weaviate_class_name: str = Field("Document", env="WEAVIATE_CLASS_NAME")
    
    # Default vector database
    default_provider: str = Field("qdrant", env="VECTOR_DB_PROVIDER")
    
    @field_validator("default_provider")
    @classmethod
    def validate_provider(cls, v):
        allowed = ["qdrant", "weaviate"]
        if v not in allowed:
            raise ValueError(f"Vector DB provider must be one of {allowed}")
        return v


class LLMSettings(BaseSettings):
    """LLM configuration settings."""
    
    # Cohere settings
    cohere_api_key: Optional[str] = Field(None, env="COHERE_API_KEY")
    cohere_model: str = Field("command-r-plus", env="COHERE_MODEL")
    
    # Ollama settings
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3:8b", env="OLLAMA_MODEL")
    
    # Embedding settings (using sentence-transformers as default)
    embedding_model: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(384, env="EMBEDDING_DIMENSION")
    
    # Default LLM provider (SothemaAI focused)
    default_provider: str = Field("sothemaai", env="LLM_PROVIDER")
    
    @field_validator("default_provider")
    @classmethod
    def validate_llm_provider(cls, v):
        allowed = ["sothemaai", "cohere", "ollama"]  # OpenAI removed
        if v not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}")
        return v
    
    # Configuration SothemaAI
    sothemaai_base_url: Optional[str] = Field(None, env="SOTHEMAAI_BASE_URL")
    sothemaai_api_key: Optional[str] = Field(None, env="SOTHEMAAI_API_KEY")
    sothemaai_timeout: int = Field(30, env="SOTHEMAAI_TIMEOUT")
    
    model_config = {
        "env_prefix": "LLM_",
        "case_sensitive": False
    }


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="JWT_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="JWT_REFRESH_EXPIRE_DAYS")
    
    # Keycloak settings
    keycloak_server_url: Optional[str] = Field(None, env="KEYCLOAK_SERVER_URL")
    keycloak_realm: Optional[str] = Field(None, env="KEYCLOAK_REALM")
    keycloak_client_id: Optional[str] = Field(None, env="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: Optional[str] = Field(None, env="KEYCLOAK_CLIENT_SECRET")
    
    # CORS settings
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class StorageSettings(BaseSettings):
    """Storage configuration settings."""
    
    # MinIO/S3 settings
    endpoint: str = Field("localhost:9000", env="MINIO_ENDPOINT")
    access_key: str = Field("minioadmin", env="MINIO_ACCESS_KEY")
    secret_key: str = Field("minioadmin", env="MINIO_SECRET_KEY")
    bucket_name: str = Field("rag-documents", env="MINIO_BUCKET_NAME")
    secure: bool = Field(False, env="MINIO_SECURE")
    
    # File processing settings
    max_file_size_mb: int = Field(100, env="MAX_FILE_SIZE_MB")
    allowed_extensions: List[str] = Field(
        [".pdf", ".docx", ".txt", ".md", ".html", ".mp3", ".wav", ".m4a"],
        env="ALLOWED_EXTENSIONS"
    )
    
    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v


class ProcessingSettings(BaseSettings):
    """Document processing configuration settings."""
    
    # Chunking settings
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")
    
    # OCR settings
    ocr_language: str = Field("eng", env="OCR_LANGUAGE")
    ocr_confidence_threshold: float = Field(0.7, env="OCR_CONFIDENCE_THRESHOLD")
    
    # Audio processing settings
    whisper_model: str = Field("base", env="WHISPER_MODEL")
    audio_chunk_duration: int = Field(30, env="AUDIO_CHUNK_DURATION")
    
    # Concurrency settings
    max_concurrent_requests: int = Field(10, env="MAX_CONCURRENT_REQUESTS")
    max_workers: int = Field(4, env="MAX_WORKERS")


class CelerySettings(BaseSettings):
    """Celery configuration settings."""
    
    broker_url: str = Field("redis://localhost:6379/1", env="CELERY_BROKER_URL")
    result_backend: str = Field("redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # Worker settings
    worker_concurrency: int = Field(4, env="CELERY_WORKER_CONCURRENCY")
    worker_prefetch_multiplier: int = Field(1, env="CELERY_WORKER_PREFETCH_MULTIPLIER")
    
    # Task settings
    task_soft_time_limit: int = Field(300, env="CELERY_TASK_SOFT_TIME_LIMIT")
    task_time_limit: int = Field(600, env="CELERY_TASK_TIME_LIMIT")
    task_max_retries: int = Field(3, env="CELERY_TASK_MAX_RETRIES")
    task_default_retry_delay: int = Field(60, env="CELERY_TASK_DEFAULT_RETRY_DELAY")
    
    # Result settings
    result_expires: int = Field(3600, env="CELERY_RESULT_EXPIRES")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""
    
    # Prometheus settings
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    
    # Tracing settings
    jaeger_endpoint: Optional[str] = Field(None, env="JAEGER_ENDPOINT")
    tracing_enabled: bool = Field(True, env="TRACING_ENABLED")
    
    # Logging settings
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    
    # LangSmith settings
    langsmith_api_key: Optional[str] = Field(None, env="LANGSMITH_API_KEY")
    langsmith_project: str = Field("enterprise-rag", env="LANGSMITH_PROJECT")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application settings
    app_name: str = Field("Enterprise RAG System", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # API settings
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_prefix: str = Field("/api/v1", env="API_PREFIX")
    
    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    vector_db: VectorDBSettings = VectorDBSettings()
    llm: LLMSettings = LLMSettings()
    security: SecuritySettings = SecuritySettings()
    storage: StorageSettings = StorageSettings()
    processing: ProcessingSettings = ProcessingSettings()
    celery: CelerySettings = CelerySettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
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
settings = get_settings()
