"""
Middleware d'authentification pour l'API MAR.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import logging
import time
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

# Configuration JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", 3600))  # 1 heure par défaut

# Bearer token handler
security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware d'authentification JWT
    """
    
    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/metrics"  # Pour Prometheus
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Traite la requête d'authentification"""
        
        # Vérifier si le path est exclu
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Extraire le token d'autorisation
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Token manquant pour {request.url.path}")
            return self._unauthorized_response("Token d'authentification requis")
        
        token = auth_header.split(" ")[1]
        
        try:
            # Valider le token JWT
            payload = self._validate_token(token)
            
            # Ajouter les informations utilisateur à la requête
            request.state.user = payload
            
            # Continuer le traitement
            response = await call_next(request)
            
            # Ajouter headers de sécurité
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            return response
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expiré pour {request.url.path}")
            return self._unauthorized_response("Token expiré")
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token invalide pour {request.url.path}: {e}")
            return self._unauthorized_response("Token invalide")
            
        except Exception as e:
            logger.error(f"Erreur authentification: {e}")
            return self._server_error_response("Erreur d'authentification")
    
    def _is_excluded_path(self, path: str) -> bool:
        """Vérifie si le path est exclu de l'authentification"""
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False
    
    def _validate_token(self, token: str) -> Dict[str, Any]:
        """Valide un token JWT et retourne le payload"""
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            
            # Vérifier l'expiration
            if payload.get("exp", 0) < time.time():
                raise jwt.ExpiredSignatureError("Token expired")
            
            return payload
            
        except Exception as e:
            logger.error(f"Erreur validation token: {e}")
            raise
    
    def _unauthorized_response(self, message: str):
        """Retourne une réponse 401"""
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "unauthorized",
                "message": message,
                "timestamp": time.time()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    def _server_error_response(self, message: str):
        """Retourne une réponse 500"""
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": message,
                "timestamp": time.time()
            }
        )


class TokenManager:
    """
    Gestionnaire de tokens JWT
    """
    
    @staticmethod
    def create_token(user_data: Dict[str, Any], expires_in: Optional[int] = None) -> str:
        """
        Crée un token JWT
        
        Args:
            user_data: Données utilisateur à inclure
            expires_in: Durée d'expiration en secondes
            
        Returns:
            Token JWT signé
        """
        try:
            now = time.time()
            exp_time = now + (expires_in or JWT_EXPIRATION)
            
            payload = {
                "user_id": user_data.get("user_id"),
                "username": user_data.get("username"),
                "email": user_data.get("email"),
                "roles": user_data.get("roles", []),
                "iat": now,
                "exp": exp_time,
                "iss": "mar-platform"
            }
            
            token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            
            logger.info(f"Token créé pour utilisateur {user_data.get('username')}")
            return token
            
        except Exception as e:
            logger.error(f"Erreur création token: {e}")
            raise
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Décode un token JWT
        
        Args:
            token: Token à décoder
            
        Returns:
            Payload décodé
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            return payload
            
        except Exception as e:
            logger.error(f"Erreur décodage token: {e}")
            raise
    
    @staticmethod
    def refresh_token(token: str) -> str:
        """
        Rafraîchit un token JWT
        
        Args:
            token: Token existant
            
        Returns:
            Nouveau token
        """
        try:
            # Décoder le token existant (même s'il est expiré)
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False}  # Ignorer l'expiration
            )
            
            # Créer un nouveau token avec les mêmes données
            user_data = {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "email": payload.get("email"),
                "roles": payload.get("roles", [])
            }
            
            return TokenManager.create_token(user_data)
            
        except Exception as e:
            logger.error(f"Erreur rafraîchissement token: {e}")
            raise


class APIKeyAuth:
    """
    Authentification par clé API (pour services externes)
    """
    
    def __init__(self):
        # En production, stocker les clés dans une base de données
        self.api_keys = {
            os.getenv("ADMIN_API_KEY", "admin-key-change-in-production"): {
                "name": "admin",
                "permissions": ["read", "write", "admin"],
                "rate_limit": 1000
            },
            os.getenv("SERVICE_API_KEY", "service-key-change-in-production"): {
                "name": "service",
                "permissions": ["read", "write"],
                "rate_limit": 500
            },
            os.getenv("READONLY_API_KEY", "readonly-key-change-in-production"): {
                "name": "readonly",
                "permissions": ["read"],
                "rate_limit": 200
            }
        }
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Valide une clé API
        
        Args:
            api_key: Clé API à valider
            
        Returns:
            Informations de la clé si valide, None sinon
        """
        if api_key in self.api_keys:
            key_info = self.api_keys[api_key].copy()
            key_info["api_key"] = api_key
            return key_info
        return None
    
    def has_permission(self, api_key: str, permission: str) -> bool:
        """
        Vérifie si une clé API a une permission
        
        Args:
            api_key: Clé API
            permission: Permission à vérifier
            
        Returns:
            True si la permission est accordée
        """
        key_info = self.validate_api_key(api_key)
        if not key_info:
            return False
        
        return permission in key_info.get("permissions", [])


# Instance globale pour l'authentification par clé API
api_key_auth = APIKeyAuth()


def get_current_user_from_token(token: str) -> Dict[str, Any]:
    """
    Extrait les informations utilisateur d'un token
    
    Args:
        token: Token JWT
        
    Returns:
        Informations utilisateur
    """
    try:
        payload = TokenManager.decode_token(token)
        
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "token_iat": payload.get("iat"),
            "token_exp": payload.get("exp")
        }
        
    except Exception as e:
        logger.error(f"Erreur extraction utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )


def require_permission(permission: str):
    """
    Décorateur pour vérifier les permissions
    
    Args:
        permission: Permission requise
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Vérifier les permissions ici
            # (implémentation dépendante du contexte)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def create_development_token() -> str:
    """
    Crée un token de développement pour les tests
    
    Returns:
        Token de développement
    """
    user_data = {
        "user_id": "dev-user-001",
        "username": "developer",
        "email": "dev@mar-platform.com",
        "roles": ["user", "developer"]
    }
    
    return TokenManager.create_token(user_data, expires_in=86400)  # 24h
