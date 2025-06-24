"""
Dependencies d'authentification pour l'API MAR.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from typing import Dict, Any, Optional
import logging
import jwt
import os
from datetime import datetime, timedelta
import hashlib
import secrets

logger = logging.getLogger(__name__)

# Configuration JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security schemes
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenManager:
    """Gestionnaire de tokens JWT"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Crée un token d'accès JWT
        
        Args:
            data: Données à encoder dans le token
            expires_delta: Durée de validité du token
            
        Returns:
            Token JWT encodé
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access_token"
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Décode et valide un token JWT
        
        Args:
            token: Token JWT à décoder
            
        Returns:
            Payload du token
            
        Raises:
            HTTPException: Si le token est invalide
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Vérifier le type de token
            if payload.get("type") != "access_token":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


# Utilisateurs de démo (en production, utiliser une vraie base de données)
DEMO_USERS = {
    "admin": {
        "user_id": "1",
        "username": "admin",
        "email": "admin@mar-platform.com",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "roles": ["admin", "user"],
        "is_active": True
    },
    "user": {
        "user_id": "2", 
        "username": "user",
        "email": "user@mar-platform.com",
        "password_hash": hashlib.sha256("user123".encode()).hexdigest(),
        "roles": ["user"],
        "is_active": True
    }
}

# API Keys de démo (en production, stocker dans une base de données)
DEMO_API_KEYS = {
    "sk-mar-demo-key-123": {
        "key_id": "1",
        "name": "Demo Key",
        "user_id": "1",
        "roles": ["admin", "user"],
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_used": None
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authentifie un utilisateur avec username/password
    
    Args:
        username: Nom d'utilisateur
        password: Mot de passe
        
    Returns:
        Données utilisateur si authentification réussie, None sinon
    """
    user = DEMO_USERS.get(username)
    if not user:
        return None
    
    if not verify_password(password, user["password_hash"]):
        return None
    
    if not user["is_active"]:
        return None
    
    return user


def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Vérifie une clé API
    
    Args:
        api_key: Clé API à vérifier
        
    Returns:
        Données de la clé si valide, None sinon
    """
    key_data = DEMO_API_KEYS.get(api_key)
    if not key_data:
        return None
    
    if not key_data["is_active"]:
        return None
    
    # Mettre à jour la dernière utilisation
    key_data["last_used"] = datetime.utcnow()
    
    # Récupérer l'utilisateur associé
    user_id = key_data["user_id"]
    user = next((u for u in DEMO_USERS.values() if u["user_id"] == user_id), None)
    
    if not user or not user["is_active"]:
        return None
    
    return {
        **user,
        "api_key_id": key_data["key_id"],
        "api_key_name": key_data["name"]
    }


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency pour obtenir l'utilisateur authentifié via JWT
    
    Args:
        request: Requête FastAPI
        credentials: Credentials JWT
        
    Returns:
        Informations utilisateur
        
    Raises:
        HTTPException: Si l'authentification échoue
    """
    try:
        # Vérifier si l'utilisateur est déjà dans le state (middleware)
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user
        
        # Sinon, décoder le token manuellement
        token = credentials.credentials
        payload = TokenManager.decode_token(token)
        
        user_data = {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "token_iat": payload.get("iat"),
            "token_exp": payload.get("exp")
        }
        
        # Vérifier que les données essentielles sont présentes
        if not user_data["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide: user_id manquant"
            )
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur authentification: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Échec de l'authentification"
        )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    Dependency pour obtenir l'utilisateur si authentifié (optionnel)
    
    Args:
        request: Requête FastAPI
        credentials: Credentials JWT optionnels
        
    Returns:
        Informations utilisateur ou None
    """
    try:
        if not credentials:
            return None
        
        return await get_current_user(request, credentials)
        
    except HTTPException:
        # En cas d'erreur, retourner None plutôt que lever l'exception
        return None
    except Exception as e:
        logger.warning(f"Erreur authentification optionnelle: {e}")
        return None


async def get_api_key_user(
    request: Request,
    x_api_key: Optional[str] = Depends(api_key_header)
) -> Dict[str, Any]:
    """
    Dependency pour authentification par clé API
    
    Args:
        request: Requête FastAPI
        x_api_key: Clé API depuis header X-API-Key
        
    Returns:
        Informations de la clé API
        
    Raises:
        HTTPException: Si la clé API est invalide
    """
    try:
        # Récupérer la clé API depuis le header
        api_key = x_api_key or request.headers.get("X-API-Key")
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clé API requise"
            )
        
        # Valider la clé API
        key_info = verify_api_key(api_key)
        
        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clé API invalide"
            )
        
        return key_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur authentification clé API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur validation clé API"
        )


def require_roles(required_roles: list):
    """
    Dependency factory pour vérifier les rôles utilisateur
    
    Args:
        required_roles: Liste des rôles requis
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_roles = set(current_user.get("roles", []))
        required_roles_set = set(required_roles)
        
        if not user_roles.intersection(required_roles_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôles requis: {required_roles}. Rôles utilisateur: {list(user_roles)}"
            )
        
        return current_user
    
    return role_checker


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Dependency pour vérifier les droits admin
    
    Args:
        current_user: Utilisateur courant
        
    Returns:
        Utilisateur courant
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas admin
    """
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis"
        )
    
    return current_user


def require_permissions(required_permissions: list):
    """
    Dependency factory pour vérifier les permissions utilisateur
    
    Args:
        required_permissions: Liste des permissions requises
        
    Returns:
        Dependency function
    """
    async def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        # En production, récupérer les permissions depuis la base de données
        # Pour l'instant, utiliser les rôles comme permissions
        user_permissions = set(current_user.get("roles", []))
        
        # Mapping des rôles vers des permissions
        role_permissions = {
            "admin": ["read", "write", "delete", "admin"],
            "premium": ["read", "write"],
            "standard": ["read", "write"],
            "free": ["read"]
        }
        
        # Calculer les permissions effectives
        effective_permissions = set()
        for role in current_user.get("roles", []):
            effective_permissions.update(role_permissions.get(role, []))
        
        # Vérifier les permissions requises
        required_permissions_set = set(required_permissions)
        if not effective_permissions.intersection(required_permissions_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissions requises: {required_permissions}"
            )
        
        return current_user
    
    return permission_checker


def require_api_key_permission(required_permission: str):
    """
    Dependency factory pour vérifier les permissions des clés API
    
    Args:
        required_permission: Permission requise pour la clé API
        
    Returns:
        Dependency function
    """
    async def api_permission_checker(
        api_key: Dict[str, Any] = Depends(get_api_key_user)
    ):
        # Vérifier si la clé API a la permission requise
        api_key_permissions = set(api_key.get("permissions", []))
        
        if required_permission not in api_key_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission API requise: {required_permission}"
            )
        
        return api_key
    
    return api_permission_checker


async def get_user_or_api_key(
    request: Request,
    jwt_credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    x_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Dependency qui accepte soit JWT soit clé API
    
    Args:
        request: Requête FastAPI
        jwt_credentials: Credentials JWT
        x_api_key: Clé API
        
    Returns:
        Informations utilisateur ou clé API
        
    Raises:
        HTTPException: Si aucune authentification valide
    """
    try:
        # Essayer d'abord l'authentification JWT
        if jwt_credentials:
            try:
                return await get_current_user(request, jwt_credentials)
            except HTTPException:
                pass  # Continuer avec la clé API
        
        # Essayer l'authentification par clé API
        api_key = x_api_key or request.headers.get("X-API-Key")
        if api_key:
            try:
                return await get_api_key_user(request, api_key)
            except HTTPException:
                pass  # Continuer
        
        # Aucune authentification valide
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification JWT ou clé API requise"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur authentification mixte: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur d'authentification"
        )


class RateLimitChecker:
    """Vérificateur de limites de taux pour utilisateurs authentifiés"""
    
    def __init__(self, requests_per_minute: int, requests_per_hour: int):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
    
    async def __call__(self, current_user: Dict[str, Any] = Depends(get_current_user)):
        """
        Vérifie les limites de taux pour l'utilisateur
        
        Args:
            current_user: Utilisateur actuel
            
        Returns:
            Utilisateur si les limites ne sont pas dépassées
            
        Raises:
            HTTPException: Si les limites sont dépassées
        """
        # Cette logique sera intégrée avec le middleware de rate limiting
        # Pour l'instant, retourner l'utilisateur tel quel
        return current_user


# Instances prédéfinies des vérificateurs de rôles
require_admin = require_roles(["admin"])
require_premium = require_roles(["premium", "admin"])
require_standard = require_roles(["standard", "premium", "admin"])

# Instances prédéfinies des vérificateurs de permissions
require_read = require_permissions(["read"])
require_write = require_permissions(["write"])
require_admin_permission = require_permissions(["admin"])

# Instances prédéfinies pour clés API
require_api_read = require_api_key_permission("read")
require_api_write = require_api_key_permission("write")
require_api_admin = require_api_key_permission("admin")

# Rate limiters prédéfinis
standard_rate_limit = RateLimitChecker(requests_per_minute=60, requests_per_hour=1000)
premium_rate_limit = RateLimitChecker(requests_per_minute=120, requests_per_hour=5000)
admin_rate_limit = RateLimitChecker(requests_per_minute=200, requests_per_hour=10000)


def get_user_context(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait le contexte utilisateur pour logging et analytics
    
    Args:
        current_user: Informations utilisateur
        
    Returns:
        Contexte utilisateur simplifié
    """
    return {
        "user_id": current_user.get("user_id"),
        "username": current_user.get("username"),
        "roles": current_user.get("roles", []),
        "auth_type": current_user.get("auth_type", "jwt"),
        "permissions": current_user.get("permissions", [])
    }


async def validate_session(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Valide la session utilisateur et vérifie la fraîcheur du token
    
    Args:
        request: Requête FastAPI
        current_user: Utilisateur actuel
        
    Returns:
        Utilisateur validé
        
    Raises:
        HTTPException: Si la session est invalide
    """
    try:
        import time
        
        # Vérifier l'expiration du token
        token_exp = current_user.get("token_exp", 0)
        current_time = time.time()
        
        # Avertir si le token expire bientôt (moins de 10 minutes)
        if token_exp - current_time < 600:
            logger.warning(f"Token expiring soon for user {current_user['user_id']}")
            # Optionnel: ajouter un header d'avertissement
            # response.headers["X-Token-Expires-Soon"] = "true"
        
        # Vérifier si le token est expiré
        if token_exp <= current_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expiré"
            )
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur validation session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur validation session"
        )
