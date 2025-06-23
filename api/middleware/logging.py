"""
Middleware de logging pour l'API MAR.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time
import json
import uuid
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

# Configuration du logger spécialisé pour les requêtes API
api_logger = logging.getLogger("api_requests")
api_logger.setLevel(logging.INFO)

# Handler pour les logs structurés (JSON)
class JSONFormatter(logging.Formatter):
    """Formateur JSON pour les logs structurés"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Ajouter les données custom si disponibles
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, ensure_ascii=False)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de logging avancé pour tracer les requêtes API
    """
    
    def __init__(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        sensitive_headers: Optional[list] = None,
        max_body_size: int = 10000  # 10KB max pour les bodies
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        
        # Headers sensibles à masquer
        self.sensitive_headers = set(sensitive_headers or [
            "authorization", "cookie", "x-api-key", "x-auth-token"
        ])
        
        # Endpoints à exclure du logging détaillé
        self.excluded_paths = {"/health", "/metrics"}
        
        # Setup du formateur JSON
        json_handler = logging.StreamHandler()
        json_handler.setFormatter(JSONFormatter())
        api_logger.addHandler(json_handler)
    
    async def dispatch(self, request: Request, call_next):
        """Traite le logging des requêtes"""
        
        # Générer un ID unique pour cette requête
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Marquer le début
        start_time = time.time()
        request.state.start_time = start_time
        
        # Logger la requête entrante
        if self.log_requests and not self._is_excluded_path(request.url.path):
            await self._log_request(request, request_id)
        
        # Traiter la requête
        try:
            response = await call_next(request)
            
            # Logger la réponse
            if self.log_responses and not self._is_excluded_path(request.url.path):
                await self._log_response(request, response, request_id, start_time)
            
            # Ajouter l'ID de requête dans les headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Logger l'erreur
            await self._log_error(request, e, request_id, start_time)
            raise
    
    def _is_excluded_path(self, path: str) -> bool:
        """Vérifie si le path est exclu du logging"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    async def _log_request(self, request: Request, request_id: str):
        """Log les détails de la requête"""
        
        try:
            # Informations de base
            log_data = {
                "event_type": "request_start",
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
                "headers": self._sanitize_headers(dict(request.headers))
            }
            
            # Informations utilisateur si disponible
            user = getattr(request.state, "user", None)
            if user:
                log_data["user_id"] = user.get("user_id")
                log_data["username"] = user.get("username")
            
            # Body de la requête si activé
            if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
                body = await self._get_request_body(request)
                if body:
                    log_data["request_body"] = body
            
            # Logger avec niveau INFO
            api_logger.info(
                f"Request {request.method} {request.url.path}",
                extra={"extra_data": log_data}
            )
            
        except Exception as e:
            logging.error(f"Erreur logging requête: {e}")
    
    async def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        start_time: float
    ):
        """Log les détails de la réponse"""
        
        try:
            # Calculer la durée
            duration = time.time() - start_time
            
            # Informations de base
            log_data = {
                "event_type": "request_complete",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "response_headers": self._sanitize_headers(dict(response.headers))
            }
            
            # Informations utilisateur
            user = getattr(request.state, "user", None)
            if user:
                log_data["user_id"] = user.get("user_id")
            
            # Body de la réponse si activé
            if self.log_response_body and hasattr(response, "body"):
                body = await self._get_response_body(response)
                if body:
                    log_data["response_body"] = body
            
            # Niveau de log selon le status code
            if response.status_code >= 500:
                level = logging.ERROR
                message = f"Server error {response.status_code} for {request.method} {request.url.path}"
            elif response.status_code >= 400:
                level = logging.WARNING
                message = f"Client error {response.status_code} for {request.method} {request.url.path}"
            else:
                level = logging.INFO
                message = f"Request completed {response.status_code} for {request.method} {request.url.path}"
            
            api_logger.log(
                level,
                message,
                extra={"extra_data": log_data}
            )
            
        except Exception as e:
            logging.error(f"Erreur logging réponse: {e}")
    
    async def _log_error(
        self,
        request: Request,
        error: Exception,
        request_id: str,
        start_time: float
    ):
        """Log les erreurs de traitement"""
        
        try:
            duration = time.time() - start_time
            
            log_data = {
                "event_type": "request_error",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration * 1000, 2),
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
            
            # Informations utilisateur
            user = getattr(request.state, "user", None)
            if user:
                log_data["user_id"] = user.get("user_id")
            
            api_logger.error(
                f"Request error for {request.method} {request.url.path}: {error}",
                extra={"extra_data": log_data},
                exc_info=True
            )
            
        except Exception as e:
            logging.error(f"Erreur logging erreur: {e}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrait l'IP du client en tenant compte des proxys"""
        
        # Vérifier les headers de proxy
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Prendre la première IP (client original)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback sur l'IP directe
        return request.client.host if request.client else "unknown"
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Masque les headers sensibles"""
        
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "***MASKED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Récupère le body de la requête"""
        
        try:
            body = await request.body()
            
            if not body:
                return None
            
            # Limiter la taille
            if len(body) > self.max_body_size:
                return f"Body too large ({len(body)} bytes, max {self.max_body_size})"
            
            # Essayer de décoder en JSON pour un affichage propre
            try:
                decoded = body.decode("utf-8")
                json_data = json.loads(decoded)
                return self._sanitize_json_body(json_data)
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Si ce n'est pas du JSON valide, retourner tel quel (tronqué)
                return body.decode("utf-8", errors="ignore")[:self.max_body_size]
                
        except Exception as e:
            logging.warning(f"Erreur lecture body requête: {e}")
            return None
    
    async def _get_response_body(self, response: Response) -> Optional[str]:
        """Récupère le body de la réponse"""
        
        try:
            if not hasattr(response, "body") or not response.body:
                return None
            
            body = response.body
            
            # Limiter la taille
            if len(body) > self.max_body_size:
                return f"Body too large ({len(body)} bytes, max {self.max_body_size})"
            
            # Décoder et sanitizer
            try:
                decoded = body.decode("utf-8")
                json_data = json.loads(decoded)
                return self._sanitize_json_body(json_data)
            except (UnicodeDecodeError, json.JSONDecodeError):
                return body.decode("utf-8", errors="ignore")[:self.max_body_size]
                
        except Exception as e:
            logging.warning(f"Erreur lecture body réponse: {e}")
            return None
    
    def _sanitize_json_body(self, json_data: Any) -> Any:
        """Masque les champs sensibles dans un JSON"""
        
        if isinstance(json_data, dict):
            sanitized = {}
            for key, value in json_data.items():
                if key.lower() in {"password", "token", "secret", "key", "auth"}:
                    sanitized[key] = "***MASKED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_json_body(value)
                else:
                    sanitized[key] = value
            return sanitized
        
        elif isinstance(json_data, list):
            return [self._sanitize_json_body(item) for item in json_data]
        
        else:
            return json_data


class PerformanceLogger:
    """Logger spécialisé pour les métriques de performance"""
    
    def __init__(self):
        self.perf_logger = logging.getLogger("performance")
        self.perf_logger.setLevel(logging.INFO)
        
        # Handler séparé pour les métriques de performance
        perf_handler = logging.StreamHandler()
        perf_handler.setFormatter(JSONFormatter())
        self.perf_logger.addHandler(perf_handler)
    
    def log_workflow_performance(
        self,
        workflow_type: str,
        execution_time: float,
        success: bool,
        user_id: Optional[str] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ):
        """Log les métriques de performance d'un workflow"""
        
        metrics = {
            "event_type": "workflow_performance",
            "workflow_type": workflow_type,
            "execution_time_ms": round(execution_time * 1000, 2),
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if user_id:
            metrics["user_id"] = user_id
        
        if additional_metrics:
            metrics.update(additional_metrics)
        
        self.perf_logger.info(
            f"Workflow {workflow_type} performance",
            extra={"extra_data": metrics}
        )
    
    def log_agent_performance(
        self,
        agent_type: str,
        operation: str,
        execution_time: float,
        success: bool,
        quality_score: Optional[float] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ):
        """Log les métriques de performance d'un agent"""
        
        metrics = {
            "event_type": "agent_performance",
            "agent_type": agent_type,
            "operation": operation,
            "execution_time_ms": round(execution_time * 1000, 2),
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if quality_score is not None:
            metrics["quality_score"] = quality_score
        
        if additional_metrics:
            metrics.update(additional_metrics)
        
        self.perf_logger.info(
            f"Agent {agent_type} {operation} performance",
            extra={"extra_data": metrics}
        )


# Instance globale du logger de performance
performance_logger = PerformanceLogger()


def log_function_performance(func_name: str):
    """Décorateur pour logger automatiquement les performances d'une fonction"""
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                
                log_data = {
                    "event_type": "function_performance",
                    "function_name": func_name,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                }
                
                if error:
                    log_data["error"] = error
                
                performance_logger.perf_logger.info(
                    f"Function {func_name} performance",
                    extra={"extra_data": log_data}
                )
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                
                log_data = {
                    "event_type": "function_performance",
                    "function_name": func_name,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                }
                
                if error:
                    log_data["error"] = error
                
                performance_logger.perf_logger.info(
                    f"Function {func_name} performance",
                    extra={"extra_data": log_data}
                )
        
        # Retourner le wrapper approprié selon si c'est async ou non
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
