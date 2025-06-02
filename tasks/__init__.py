"""
Package des tâches Celery pour le système RAG Enterprise.
"""

from tasks.analytics import generate_daily_report, analyze_user_behavior, generate_system_performance_report
from tasks.document_processing import process_document_task, batch_process_documents_task, reprocess_failed_documents_task
from tasks.maintenance import cleanup_expired_tasks, health_check_services, optimize_vector_indexes
from tasks.vectorization import rebuild_vector_index_task, optimize_embeddings_task

__all__ = [
    # Document processing
    "process_document_task",
    "batch_process_documents_task", 
    "reprocess_failed_documents_task",
    
    # Vectorization
    "rebuild_vector_index_task",
    "optimize_embeddings_task",
    
    # Maintenance
    "cleanup_expired_tasks",
    "health_check_services",
    "optimize_vector_indexes",
    
    # Analytics
    "generate_daily_report",
    "analyze_user_behavior",
    "generate_system_performance_report",
]
