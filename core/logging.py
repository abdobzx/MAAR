"""
Structured logging configuration for the Enterprise RAG System.
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog

def configure_logging() -> None:
    """Configure structured logging."""
    
    # Configure structlog with basic setup
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.monitoring.log_level)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.monitoring.log_level),
    )
    
    # Configure OpenTelemetry tracing if enabled
    if settings.monitoring.tracing_enabled and settings.monitoring.jaeger_endpoint:
        configure_tracing()


def configure_tracing() -> None:
    """Configure OpenTelemetry tracing."""
    
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        endpoint=settings.monitoring.jaeger_endpoint,
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Instrument logging
    LoggingInstrumentor().instrument(set_logging_format=True)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_function_call(func_name: str, **kwargs) -> None:
    """Log function call with parameters."""
    logger = get_logger("function_calls")
    logger.info(
        "Function called",
        function=func_name,
        **kwargs
    )


def log_agent_action(agent_name: str, action: str, **kwargs) -> None:
    """Log agent action with context."""
    logger = get_logger("agent_actions")
    logger.info(
        "Agent action",
        agent=agent_name,
        action=action,
        **kwargs
    )


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log error with context."""
    logger = get_logger("errors")
    logger.error(
        "Error occurred",
        error=str(error),
        error_type=type(error).__name__,
        **(context or {})
    )


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """Log performance metrics."""
    logger = get_logger("performance")
    logger.info(
        "Performance metric",
        operation=operation,
        duration_seconds=duration,
        **kwargs
    )


def log_security_event(event_type: str, user_id: Optional[str] = None, **kwargs) -> None:
    """Log security-related events."""
    logger = get_logger("security")
    logger.warning(
        "Security event",
        event_type=event_type,
        user_id=user_id,
        **kwargs
    )
