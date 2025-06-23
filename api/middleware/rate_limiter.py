"""
Middleware de limitation de taux (rate limiting) pour l'API MAR.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
import hashlib
import json

logger = logging.getLogger(__name__)


class RateLimitRule:
    """Règle de limitation de taux"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
        cooldown_seconds: int = 60
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.cooldown_seconds = cooldown_seconds


class TokenBucket:
    """Implémentation d'un token bucket pour rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Capacité maximale du bucket
            refill_rate: Taux de remplissage (tokens par seconde)
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Consomme des tokens du bucket
        
        Args:
            tokens: Nombre de tokens à consommer
            
        Returns:
            True si les tokens sont disponibles
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Remplit le bucket selon le taux de remplissage"""
        now = time.time()
        time_passed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + time_passed * self.refill_rate
        )
        self.last_refill = now


class SlidingWindowCounter:
    """Compteur à fenêtre glissante pour rate limiting"""
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Args:
            window_size: Taille de la fenêtre en secondes
            max_requests: Nombre maximum de requêtes dans la fenêtre
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
    
    def is_allowed(self) -> bool:
        """
        Vérifie si une nouvelle requête est autorisée
        
        Returns:
            True si la requête est autorisée
        """
        now = time.time()
        
        # Nettoyer les anciennes requêtes
        while self.requests and self.requests[0] <= now - self.window_size:
            self.requests.popleft()
        
        # Vérifier la limite
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def get_retry_after(self) -> int:
        """
        Retourne le délai avant la prochaine tentative possible
        
        Returns:
            Délai en secondes
        """
        if not self.requests:
            return 0
        
        oldest_request = self.requests[0]
        return max(0, int(oldest_request + self.window_size - time.time()))


class RateLimitStore:
    """Store en mémoire pour les données de rate limiting"""
    
    def __init__(self):
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        self.blocked_clients: Dict[str, float] = {}  # client_id -> unblock_time
        self.request_history: Dict[str, deque] = defaultdict(deque)
        
        # Nettoyage périodique
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def get_token_bucket(self, client_id: str, capacity: int, refill_rate: float) -> TokenBucket:
        """Récupère ou crée un token bucket pour un client"""
        if client_id not in self.token_buckets:
            self.token_buckets[client_id] = TokenBucket(capacity, refill_rate)
        return self.token_buckets[client_id]
    
    def get_sliding_window(self, client_id: str, window_size: int, max_requests: int) -> SlidingWindowCounter:
        """Récupère ou crée un compteur à fenêtre glissante"""
        key = f"{client_id}:{window_size}"
        if key not in self.sliding_windows:
            self.sliding_windows[key] = SlidingWindowCounter(window_size, max_requests)
        return self.sliding_windows[key]
    
    def is_blocked(self, client_id: str) -> bool:
        """Vérifie si un client est bloqué"""
        if client_id in self.blocked_clients:
            unblock_time = self.blocked_clients[client_id]
            if time.time() < unblock_time:
                return True
            else:
                del self.blocked_clients[client_id]
        return False
    
    def block_client(self, client_id: str, duration: int):
        """Bloque un client pour une durée donnée"""
        self.blocked_clients[client_id] = time.time() + duration
        logger.warning(f"Client {client_id} bloqué pour {duration} secondes")
    
    def record_request(self, client_id: str, endpoint: str, status_code: int):
        """Enregistre une requête dans l'historique"""
        now = time.time()
        
        # Ajouter à l'historique
        self.request_history[client_id].append({
            "timestamp": now,
            "endpoint": endpoint,
            "status_code": status_code
        })
        
        # Limiter la taille de l'historique
        max_history = 1000
        if len(self.request_history[client_id]) > max_history:
            self.request_history[client_id].popleft()
        
        # Nettoyage périodique
        self._periodic_cleanup()
    
    def _periodic_cleanup(self):
        """Nettoyage périodique des données obsolètes"""
        now = time.time()
        
        if now - self._last_cleanup > self._cleanup_interval:
            # Nettoyer les buckets inactifs
            inactive_buckets = []
            for client_id, bucket in self.token_buckets.items():
                if now - bucket.last_refill > 3600:  # 1 heure d'inactivité
                    inactive_buckets.append(client_id)
            
            for client_id in inactive_buckets:
                del self.token_buckets[client_id]
            
            # Nettoyer l'historique des requêtes
            for client_id in list(self.request_history.keys()):
                history = self.request_history[client_id]
                # Garder seulement les requêtes des 24 dernières heures
                cutoff = now - 86400
                while history and history[0]["timestamp"] < cutoff:
                    history.popleft()
                
                if not history:
                    del self.request_history[client_id]
            
            self._last_cleanup = now
            logger.info("Nettoyage rate limiting effectué")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de limitation de taux avec support multi-niveaux
    """
    
    def __init__(
        self,
        app,
        default_rule: Optional[RateLimitRule] = None,
        endpoint_rules: Optional[Dict[str, RateLimitRule]] = None,
        user_type_rules: Optional[Dict[str, RateLimitRule]] = None
    ):
        super().__init__(app)
        
        # Règles par défaut
        self.default_rule = default_rule or RateLimitRule()
        
        # Règles spécifiques par endpoint
        self.endpoint_rules = endpoint_rules or {
            "/api/v1/chat/simple": RateLimitRule(requests_per_minute=30, burst_limit=5),
            "/api/v1/chat/comparative": RateLimitRule(requests_per_minute=20, burst_limit=3),
            "/api/v1/chat/workflow": RateLimitRule(requests_per_minute=10, burst_limit=2),
            "/api/v1/documents/upload": RateLimitRule(requests_per_minute=10, burst_limit=2),
        }
        
        # Règles par type d'utilisateur
        self.user_type_rules = user_type_rules or {
            "premium": RateLimitRule(requests_per_minute=120, requests_per_hour=5000),
            "standard": RateLimitRule(requests_per_minute=60, requests_per_hour=1000),
            "free": RateLimitRule(requests_per_minute=20, requests_per_hour=200),
        }
        
        # Store pour les données de rate limiting
        self.store = RateLimitStore()
        
        # Endpoints exclus du rate limiting
        self.excluded_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next):
        """Traite la limitation de taux"""
        
        # Vérifier si le path est exclu
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Identifier le client
        client_id = self._get_client_id(request)
        
        # Vérifier si le client est bloqué
        if self.store.is_blocked(client_id):
            return self._create_blocked_response()
        
        # Obtenir les règles applicables
        rule = self._get_applicable_rule(request)
        
        # Vérifier les limites
        rate_limit_result = self._check_rate_limits(client_id, request.url.path, rule)
        
        if not rate_limit_result["allowed"]:
            # Enregistrer la tentative
            self.store.record_request(client_id, request.url.path, 429)
            
            # Bloquer temporairement si trop de tentatives
            if self._should_block_client(client_id):
                self.store.block_client(client_id, rule.cooldown_seconds)
            
            return self._create_rate_limit_response(rate_limit_result)
        
        # Traiter la requête
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Enregistrer la requête réussie
            self.store.record_request(client_id, request.url.path, response.status_code)
            
            # Ajouter headers de rate limiting
            self._add_rate_limit_headers(response, rate_limit_result)
            
            return response
            
        except Exception as e:
            # Enregistrer l'erreur
            self.store.record_request(client_id, request.url.path, 500)
            raise
    
    def _get_client_id(self, request: Request) -> str:
        """Génère un ID unique pour le client"""
        
        # Essayer d'utiliser l'ID utilisateur si authentifié
        user = getattr(request.state, "user", None)
        if user and user.get("user_id"):
            return f"user:{user['user_id']}"
        
        # Utiliser l'IP client comme fallback
        client_ip = request.client.host if request.client else "unknown"
        
        # Inclure User-Agent pour plus de spécificité
        user_agent = request.headers.get("user-agent", "")
        
        # Créer un hash pour l'anonymat
        client_string = f"{client_ip}:{user_agent}"
        client_hash = hashlib.md5(client_string.encode()).hexdigest()[:16]
        
        return f"ip:{client_hash}"
    
    def _get_applicable_rule(self, request: Request) -> RateLimitRule:
        """Détermine la règle applicable pour cette requête"""
        
        # Vérifier les règles spécifiques à l'endpoint
        endpoint_path = request.url.path
        for path, rule in self.endpoint_rules.items():
            if endpoint_path.startswith(path):
                return rule
        
        # Vérifier les règles par type d'utilisateur
        user = getattr(request.state, "user", None)
        if user:
            user_roles = user.get("roles", [])
            for role in ["premium", "standard", "free"]:
                if role in user_roles and role in self.user_type_rules:
                    return self.user_type_rules[role]
        
        # Retourner la règle par défaut
        return self.default_rule
    
    def _check_rate_limits(self, client_id: str, endpoint: str, rule: RateLimitRule) -> Dict[str, Any]:
        """Vérifie les limites de taux pour un client"""
        
        result = {
            "allowed": True,
            "retry_after": 0,
            "limit_minute": rule.requests_per_minute,
            "limit_hour": rule.requests_per_hour,
            "remaining_minute": 0,
            "remaining_hour": 0
        }
        
        # Vérifier limite par minute avec token bucket
        minute_bucket = self.store.get_token_bucket(
            f"{client_id}:minute",
            rule.requests_per_minute,
            rule.requests_per_minute / 60.0  # refill rate per second
        )
        
        if not minute_bucket.consume():
            result["allowed"] = False
            result["retry_after"] = 60
            result["limit_type"] = "minute"
        
        result["remaining_minute"] = int(minute_bucket.tokens)
        
        # Vérifier limite par heure avec sliding window
        hour_window = self.store.get_sliding_window(
            f"{client_id}:hour",
            3600,  # 1 heure
            rule.requests_per_hour
        )
        
        if result["allowed"] and not hour_window.is_allowed():
            result["allowed"] = False
            result["retry_after"] = hour_window.get_retry_after()
            result["limit_type"] = "hour"
        
        result["remaining_hour"] = rule.requests_per_hour - len(hour_window.requests)
        
        # Vérifier limite de burst
        burst_window = self.store.get_sliding_window(
            f"{client_id}:burst",
            10,  # 10 secondes
            rule.burst_limit
        )
        
        if result["allowed"] and not burst_window.is_allowed():
            result["allowed"] = False
            result["retry_after"] = 10
            result["limit_type"] = "burst"
        
        return result
    
    def _should_block_client(self, client_id: str) -> bool:
        """Détermine si un client doit être bloqué temporairement"""
        
        history = self.store.request_history.get(client_id, deque())
        
        # Compter les erreurs 429 récentes (dernières 5 minutes)
        now = time.time()
        recent_429_count = sum(
            1 for req in history
            if req["timestamp"] > now - 300 and req["status_code"] == 429
        )
        
        # Bloquer si plus de 10 erreurs 429 en 5 minutes
        return recent_429_count > 10
    
    def _create_rate_limit_response(self, rate_limit_result: Dict[str, Any]) -> JSONResponse:
        """Crée une réponse de limitation de taux"""
        
        response_data = {
            "error": "rate_limit_exceeded",
            "message": f"Taux de requêtes dépassé ({rate_limit_result.get('limit_type', 'unknown')})",
            "retry_after": rate_limit_result["retry_after"],
            "timestamp": time.time()
        }
        
        headers = {
            "Retry-After": str(rate_limit_result["retry_after"]),
            "X-RateLimit-Limit-Minute": str(rate_limit_result["limit_minute"]),
            "X-RateLimit-Limit-Hour": str(rate_limit_result["limit_hour"]),
            "X-RateLimit-Remaining-Minute": str(rate_limit_result["remaining_minute"]),
            "X-RateLimit-Remaining-Hour": str(rate_limit_result["remaining_hour"])
        }
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=response_data,
            headers=headers
        )
    
    def _create_blocked_response(self) -> JSONResponse:
        """Crée une réponse pour client bloqué"""
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "client_blocked",
                "message": "Client temporairement bloqué pour abus",
                "timestamp": time.time()
            }
        )
    
    def _add_rate_limit_headers(self, response, rate_limit_result: Dict[str, Any]):
        """Ajoute les headers de rate limiting à la réponse"""
        
        response.headers["X-RateLimit-Limit-Minute"] = str(rate_limit_result["limit_minute"])
        response.headers["X-RateLimit-Limit-Hour"] = str(rate_limit_result["limit_hour"])
        response.headers["X-RateLimit-Remaining-Minute"] = str(rate_limit_result["remaining_minute"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(rate_limit_result["remaining_hour"])
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Retourne les statistiques d'un client"""
        
        history = self.store.request_history.get(client_id, deque())
        
        if not history:
            return {"requests": 0, "errors": 0, "last_request": None}
        
        now = time.time()
        last_hour = [req for req in history if req["timestamp"] > now - 3600]
        
        return {
            "total_requests": len(history),
            "requests_last_hour": len(last_hour),
            "error_rate": len([req for req in last_hour if req["status_code"] >= 400]) / len(last_hour) if last_hour else 0,
            "last_request": max(req["timestamp"] for req in history),
            "is_blocked": self.store.is_blocked(client_id),
            "endpoints": list(set(req["endpoint"] for req in last_hour))
        }
