"""
Configuration centralisée du logging pour la plateforme MAR.
"""

import os
import logging
import logging.config
import json
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """Formateur JSON pour les logs structurés"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formate un record de log en JSON"""
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread
        }
        
        # Ajouter des champs supplémentaires si présents
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        
        # Ajouter l'exception si présente
        if record.exc_info:
            log_entry['exception'] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)


def get_log_config() -> Dict[str, Any]:
    """
    Retourne la configuration de logging
    
    Returns:
        Configuration dictionnaire pour logging.config.dictConfig
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = os.getenv("LOG_DIR", "./logs")
    
    # Créer le répertoire de logs s'il n'existe pas
    os.makedirs(log_dir, exist_ok=True)
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
                "datefmt": "%H:%M:%S"
            },
            "uvicorn": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "file_json": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": os.path.join(log_dir, "mar_platform.json"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "file_detailed": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "mar_platform.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "errors.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            },
            "access_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": os.path.join(log_dir, "access.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            }
        },
        "loggers": {
            # Logger racine de la plateforme MAR
            "": {
                "level": log_level,
                "handlers": ["console", "file_json", "error_file"],
                "propagate": False
            },
            
            # API et FastAPI
            "api": {
                "level": log_level,
                "handlers": ["console", "file_detailed", "error_file"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["file_detailed"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file_detailed"],
                "propagate": False,
                "formatter": "uvicorn"
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["access_file"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "error_file"],
                "propagate": False
            },
            
            # Agents et orchestrateur
            "agents": {
                "level": log_level,
                "handlers": ["console", "file_detailed"],
                "propagate": False
            },
            "orchestrator": {
                "level": log_level,
                "handlers": ["console", "file_detailed"],
                "propagate": False
            },
            
            # Vector store
            "vector_store": {
                "level": log_level,
                "handlers": ["console", "file_detailed"],
                "propagate": False
            },
            
            # LLM
            "llm": {
                "level": log_level,
                "handlers": ["console", "file_detailed"],
                "propagate": False
            },
            
            # Middleware
            "middleware": {
                "level": log_level,
                "handlers": ["file_detailed", "access_file"],
                "propagate": False
            },
            
            # Interface utilisateur
            "ui": {
                "level": log_level,
                "handlers": ["console", "file_detailed"],
                "propagate": False
            },
            "streamlit": {
                "level": "WARNING",
                "handlers": ["file_detailed"],
                "propagate": False
            },
            
            # Bibliothèques externes (niveau réduit)
            "urllib3": {
                "level": "WARNING",
                "handlers": ["error_file"],
                "propagate": False
            },
            "requests": {
                "level": "WARNING",
                "handlers": ["error_file"],
                "propagate": False
            },
            "sentence_transformers": {
                "level": "WARNING",
                "handlers": ["file_detailed"],
                "propagate": False
            },
            "transformers": {
                "level": "WARNING",
                "handlers": ["error_file"],
                "propagate": False
            },
            "chromadb": {
                "level": "WARNING",
                "handlers": ["file_detailed"],
                "propagate": False
            },
            "faiss": {
                "level": "WARNING",
                "handlers": ["file_detailed"],
                "propagate": False
            }
        }
    }
    
    # En mode développement, activer plus de logs
    if os.getenv("DEV_MODE", "false").lower() == "true":
        config["loggers"][""]["level"] = "DEBUG"
        config["handlers"]["console"]["formatter"] = "detailed"
    
    return config


def setup_logging():
    """Configure le logging pour toute la plateforme"""
    config = get_log_config()
    logging.config.dictConfig(config)
    
    # Logger de base pour tester la configuration
    logger = logging.getLogger("mar.logging")
    logger.info("Configuration de logging initialisée")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour un module
    
    Args:
        name: Nom du module/logger
        
    Returns:
        Logger configuré
    """
    return logging.getLogger(name)


class RequestLoggerAdapter(logging.LoggerAdapter):
    """Adaptateur de logger pour ajouter le contexte de requête"""
    
    def __init__(self, logger: logging.Logger, request_id: str = None, user_id: str = None):
        super().__init__(logger, {})
        self.request_id = request_id
        self.user_id = user_id
    
    def process(self, msg, kwargs):
        """Ajoute le contexte de requête à chaque log"""
        extra = kwargs.get("extra", {})
        
        if self.request_id:
            extra["request_id"] = self.request_id
        
        if self.user_id:
            extra["user_id"] = self.user_id
        
        kwargs["extra"] = extra
        return msg, kwargs


def get_request_logger(name: str, request_id: str = None, user_id: str = None) -> RequestLoggerAdapter:
    """
    Retourne un logger avec contexte de requête
    
    Args:
        name: Nom du module/logger
        request_id: ID de la requête
        user_id: ID de l'utilisateur
        
    Returns:
        Logger avec contexte
    """
    base_logger = get_logger(name)
    return RequestLoggerAdapter(base_logger, request_id, user_id)


class PerformanceLogger:
    """Logger pour les métriques de performance"""
    
    def __init__(self, logger_name: str):
        self.logger = get_logger(f"{logger_name}.performance")
    
    def log_request_duration(self, endpoint: str, method: str, duration: float, status_code: int):
        """Log la durée d'une requête"""
        self.logger.info(
            f"Request completed",
            extra={
                "endpoint": endpoint,
                "method": method,
                "duration": duration,
                "status_code": status_code,
                "metric_type": "request_duration"
            }
        )
    
    def log_operation_duration(self, operation: str, duration: float, success: bool = True):
        """Log la durée d'une opération"""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            f"Operation {operation} completed",
            extra={
                "operation": operation,
                "duration": duration,
                "success": success,
                "metric_type": "operation_duration"
            }
        )
    
    def log_agent_performance(self, agent_name: str, task: str, duration: float, tokens_used: int = None):
        """Log les performances d'un agent"""
        extra = {
            "agent": agent_name,
            "task": task,
            "duration": duration,
            "metric_type": "agent_performance"
        }
        
        if tokens_used is not None:
            extra["tokens_used"] = tokens_used
        
        self.logger.info(f"Agent {agent_name} completed {task}", extra=extra)


class SecurityLogger:
    """Logger pour les événements de sécurité"""
    
    def __init__(self):
        self.logger = get_logger("security")
    
    def log_auth_attempt(self, username: str, success: bool, ip_address: str = None):
        """Log une tentative d'authentification"""
        level = logging.INFO if success else logging.WARNING
        message = f"Authentication {'succeeded' if success else 'failed'} for {username}"
        
        extra = {
            "username": username,
            "auth_success": success,
            "event_type": "authentication"
        }
        
        if ip_address:
            extra["ip_address"] = ip_address
        
        self.logger.log(level, message, extra=extra)
    
    def log_rate_limit_exceeded(self, ip_address: str, endpoint: str):
        """Log un dépassement de rate limit"""
        self.logger.warning(
            f"Rate limit exceeded for {ip_address} on {endpoint}",
            extra={
                "ip_address": ip_address,
                "endpoint": endpoint,
                "event_type": "rate_limit_exceeded"
            }
        )
    
    def log_suspicious_activity(self, description: str, user_id: str = None, ip_address: str = None):
        """Log une activité suspecte"""
        extra = {
            "description": description,
            "event_type": "suspicious_activity"
        }
        
        if user_id:
            extra["user_id"] = user_id
        
        if ip_address:
            extra["ip_address"] = ip_address
        
        self.logger.error(f"Suspicious activity detected: {description}", extra=extra)


# Fonction d'initialisation pour la plateforme
def init_platform_logging():
    """Initialise le logging pour toute la plateforme"""
    logger = setup_logging()
    
    # Configurer les loggers spécialisés
    performance_logger = PerformanceLogger("mar.platform")
    security_logger = SecurityLogger()
    
    logger.info("Plateforme MAR - Logging initialisé")
    logger.info(f"Niveau de log: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"Répertoire de logs: {os.getenv('LOG_DIR', './logs')}")
    
    return {
        "main": logger,
        "performance": performance_logger,
        "security": security_logger
    }
