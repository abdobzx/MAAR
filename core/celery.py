"""
Configuration Celery pour les tâches asynchrones du système RAG.
"""

import os
from celery import Celery
from kombu import Queue

from core.config import settings

# Configuration Celery
celery_app = Celery(
    "enterprise_rag",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=[
        "tasks.document_processing",
        "tasks.vectorization",
        "tasks.maintenance",
        "tasks.analytics",
    ]
)

# Configuration des tâches
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "tasks.document_processing.*": {"queue": "document_processing"},
        "tasks.vectorization.*": {"queue": "vectorization"},
        "tasks.maintenance.*": {"queue": "maintenance"},
        "tasks.analytics.*": {"queue": "analytics"},
    },
    
    # Queues definition
    task_queues=(
        Queue("document_processing", routing_key="document_processing"),
        Queue("vectorization", routing_key="vectorization"),
        Queue("maintenance", routing_key="maintenance"),
        Queue("analytics", routing_key="analytics"),
        Queue("default", routing_key="default"),
    ),
    
    # Task execution
    task_default_queue="default",
    task_default_exchange="default",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Task timeouts
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    task_max_retries=3,
    task_default_retry_delay=60,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-tasks": {
            "task": "tasks.maintenance.cleanup_expired_tasks",
            "schedule": 3600.0,  # Every hour
        },
        "generate-analytics-report": {
            "task": "tasks.analytics.generate_daily_report",
            "schedule": 86400.0,  # Daily
        },
        "health-check-services": {
            "task": "tasks.maintenance.health_check_services",
            "schedule": 300.0,  # Every 5 minutes
        },
        "optimize-vector-indexes": {
            "task": "tasks.maintenance.optimize_vector_indexes",
            "schedule": 3600.0 * 6,  # Every 6 hours
        },
    },
)

# Configuration de monitoring
if settings.monitoring.metrics_enabled:
    celery_app.conf.update(
        worker_send_task_events=True,
        task_send_sent_event=True,
    )

# Auto-discovery des tâches
celery_app.autodiscover_tasks()

@celery_app.task(bind=True)
def debug_task(self):
    """Tâche de débogage."""
    print(f"Request: {self.request!r}")
