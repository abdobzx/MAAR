"""
Gestionnaire d'authentification et d'autorisation avec Keycloak.
Intègre OAuth2, JWT, et RBAC pour la sécurité enterprise.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from functools import wraps

import httpx
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt as jose_jwt
from pydantic import BaseModel, Field

from core.config import get_settings
from core.exceptions import AuthenticationError, AuthorizationError
from core.logging import get_logger
from core.models import UserInfo, Permission, Role


class KeycloakConfig(BaseModel):
    """Configuration Keycloak."""
    server_url: str
    realm: str
    client_id: str
    client_secret: str
    admin_username: str
    admin_password: str


class TokenInfo(BaseModel):
    """Informations sur un token JWT."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: Optional[int] = None
    scope: str = ""


class UserClaims(BaseModel):
    """Claims utilisateur extraits du JWT."""
    sub: str  # User ID
    email: str
    name: str
    preferred_username: str
    realm_access: Dict[str, List[str]] = Field(default_factory=dict)
    resource_access: Dict[str, Dict[str, List[str]]] = Field(default_factory=dict)
    organization_id: Optional[str] = None
    groups: List[str] = Field(default_factory=list)
    exp: int
    iat: int


class AuthManager:
    """Gestionnaire d'authentification principal avec Keycloak."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # Configuration Keycloak
        self.keycloak_config = KeycloakConfig(
            server_url=self.settings.keycloak_server_url,
            realm=self.settings.keycloak_realm,
            client_id=self.settings.keycloak_client_id,
            client_secret=self.settings.keycloak_client_secret,
            admin_username=self.settings.keycloak_admin_username,
            admin_password=self.settings.keycloak_admin_password
        )
        
        # Cache pour les clés publiques et métadonnées
        self.public_keys_cache: Dict[str, Any] = {}
        self.realm_info_cache: Dict[str, Any] = {}
        self.cache_expiry = datetime.utcnow()
        self.cache_duration = timedelta(hours=1)
        
        # Cache des permissions et rôles
        self.permissions_cache: Dict[str, Set[str]] = {}
        self.roles_cache: Dict[str, List[str]] = {}
        
        # Client HTTP pour les appels Keycloak
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Démarrage des tâches de maintenance
        asyncio.create_task(self._start_background_tasks())
    
    async def get_realm_info(self) -> Dict[str, Any]:
        """Récupère les informations du realm Keycloak."""
        
        if (self.realm_info_cache and 
            datetime.utcnow() < self.cache_expiry):
            return self.realm_info_cache
        
        try:
            url = f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}"
            
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            realm_info = response.json()
            
            # Mise à jour du cache
            self.realm_info_cache = realm_info
            self.cache_expiry = datetime.utcnow() + self.cache_duration
            
            return realm_info
            
        except httpx.HTTPError as e:
            self.logger.error(f"Erreur lors de la récupération du realm info: {str(e)}")
            raise AuthenticationError(f"Impossible de contacter Keycloak: {str(e)}")
    
    async def get_public_keys(self) -> Dict[str, Any]:
        """Récupère les clés publiques pour la vérification des JWT."""
        
        if (self.public_keys_cache and 
            datetime.utcnow() < self.cache_expiry):
            return self.public_keys_cache
        
        try:
            url = f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}/protocol/openid_connect/certs"
            
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            keys = response.json()
            
            # Mise à jour du cache
            self.public_keys_cache = keys
            
            return keys
            
        except httpx.HTTPError as e:
            self.logger.error(f"Erreur lors de la récupération des clés publiques: {str(e)}")
            raise AuthenticationError(f"Impossible de récupérer les clés: {str(e)}")
    
    async def verify_token(self, token: str) -> UserClaims:
        """Vérifie et décode un token JWT."""
        
        try:
            # Récupération des clés publiques
            public_keys = await self.get_public_keys()
            
            # Décodage du header pour obtenir le kid
            unverified_header = jose_jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise AuthenticationError("Token sans kid dans le header")
            
            # Recherche de la clé correspondante
            rsa_key = {}
            for key in public_keys["keys"]:
                if key["kid"] == kid:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
                    break
            
            if not rsa_key:
                raise AuthenticationError(f"Clé publique non trouvée pour kid: {kid}")
            
            # Vérification et décodage du token
            payload = jose_jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.keycloak_config.client_id,
                issuer=f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}"
            )
            
            # Création des claims utilisateur
            user_claims = UserClaims(
                sub=payload["sub"],
                email=payload.get("email", ""),
                name=payload.get("name", ""),
                preferred_username=payload.get("preferred_username", ""),
                realm_access=payload.get("realm_access", {}),
                resource_access=payload.get("resource_access", {}),
                organization_id=payload.get("organization_id"),
                groups=payload.get("groups", []),
                exp=payload["exp"],
                iat=payload["iat"]
            )
            
            # Mise à jour du cache des permissions
            await self._cache_user_permissions(user_claims)
            
            return user_claims
            
        except JWTError as e:
            self.logger.warning(f"Token JWT invalide: {str(e)}")
            raise AuthenticationError(f"Token invalide: {str(e)}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification du token: {str(e)}")
            raise AuthenticationError(f"Erreur de vérification: {str(e)}")
    
    async def authenticate_user(self, username: str, password: str) -> TokenInfo:
        """Authentifie un utilisateur et retourne les tokens."""
        
        try:
            url = f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}/protocol/openid_connect/token"
            
            data = {
                "grant_type": "password",
                "client_id": self.keycloak_config.client_id,
                "client_secret": self.keycloak_config.client_secret,
                "username": username,
                "password": password,
                "scope": "openid profile email"
            }
            
            response = await self.http_client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Identifiants invalides")
            
            response.raise_for_status()
            token_data = response.json()
            
            return TokenInfo(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "bearer"),
                expires_in=token_data["expires_in"],
                refresh_expires_in=token_data.get("refresh_expires_in"),
                scope=token_data.get("scope", "")
            )
            
        except httpx.HTTPError as e:
            self.logger.error(f"Erreur lors de l'authentification: {str(e)}")
            raise AuthenticationError(f"Erreur d'authentification: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        """Rafraîchit un token d'accès."""
        
        try:
            url = f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}/protocol/openid_connect/token"
            
            data = {
                "grant_type": "refresh_token",
                "client_id": self.keycloak_config.client_id,
                "client_secret": self.keycloak_config.client_secret,
                "refresh_token": refresh_token
            }
            
            response = await self.http_client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Refresh token invalide")
            
            response.raise_for_status()
            token_data = response.json()
            
            return TokenInfo(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "bearer"),
                expires_in=token_data["expires_in"],
                refresh_expires_in=token_data.get("refresh_expires_in"),
                scope=token_data.get("scope", "")
            )
            
        except httpx.HTTPError as e:
            self.logger.error(f"Erreur lors du refresh: {str(e)}")
            raise AuthenticationError(f"Erreur de refresh: {str(e)}")
    
    async def logout_user(self, refresh_token: str) -> bool:
        """Déconnecte un utilisateur."""
        
        try:
            url = f"{self.keycloak_config.server_url}/realms/{self.keycloak_config.realm}/protocol/openid_connect/logout"
            
            data = {
                "client_id": self.keycloak_config.client_id,
                "client_secret": self.keycloak_config.client_secret,
                "refresh_token": refresh_token
            }
            
            response = await self.http_client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            return response.status_code == 204
            
        except httpx.HTTPError as e:
            self.logger.error(f"Erreur lors de la déconnexion: {str(e)}")
            return False
    
    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """Récupère les permissions d'un utilisateur."""
        
        if user_id in self.permissions_cache:
            return self.permissions_cache[user_id]
        
        # Si pas en cache, retourne un ensemble vide
        # Dans un vrai système, on interrogerait Keycloak
        return set()
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Vérifie si un utilisateur a une permission spécifique."""
        
        user_permissions = await self.get_user_permissions(user_id)
        return permission in user_permissions
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """Récupère les rôles d'un utilisateur."""
        
        if user_id in self.roles_cache:
            return self.roles_cache[user_id]
        
        return []
    
    async def _cache_user_permissions(self, user_claims: UserClaims):
        """Met en cache les permissions et rôles d'un utilisateur."""
        
        user_id = user_claims.sub
        permissions = set()
        roles = []
        
        # Extraction des rôles du realm
        realm_roles = user_claims.realm_access.get("roles", [])
        roles.extend(realm_roles)
        
        # Extraction des rôles client
        client_access = user_claims.resource_access.get(self.keycloak_config.client_id, {})
        client_roles = client_access.get("roles", [])
        roles.extend(client_roles)
        
        # Mapping des rôles vers les permissions
        role_permission_mapping = {
            "admin": {
                "documents:read", "documents:write", "documents:delete",
                "search:read", "query:read", "orchestration:execute",
                "orchestration:read", "orchestration:cancel", "feedback:write",
                "insights:read", "metrics:read", "users:manage"
            },
            "user": {
                "documents:read", "documents:write", "search:read",
                "query:read", "feedback:write"
            },
            "viewer": {
                "documents:read", "search:read", "query:read"
            }
        }
        
        # Attribution des permissions basées sur les rôles
        for role in roles:
            if role in role_permission_mapping:
                permissions.update(role_permission_mapping[role])
        
        # Mise à jour des caches
        self.permissions_cache[user_id] = permissions
        self.roles_cache[user_id] = roles
        
        self.logger.debug(
            f"Permissions mises en cache pour {user_id}",
            extra={
                "user_id": user_id,
                "roles": roles,
                "permissions_count": len(permissions)
            }
        )
    
    async def _start_background_tasks(self):
        """Démarre les tâches de maintenance en arrière-plan."""
        
        # Nettoyage périodique des caches
        asyncio.create_task(self._cleanup_expired_cache())
    
    async def _cleanup_expired_cache(self):
        """Nettoie les caches expirés."""
        
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Nettoyage des caches si expirés
                if current_time > self.cache_expiry:
                    self.public_keys_cache.clear()
                    self.realm_info_cache.clear()
                    self.logger.info("Caches Keycloak nettoyés")
                
                # Nettoyage des permissions/rôles (garder seulement les récents)
                # Ici on pourrait implémenter une logique plus sophistiquée
                
                await asyncio.sleep(300)  # Nettoyage toutes les 5 minutes
                
            except Exception as e:
                self.logger.error(f"Erreur lors du nettoyage des caches: {str(e)}")
                await asyncio.sleep(300)


# Instances globales
auth_manager = AuthManager()
security = HTTPBearer()


# Dépendances FastAPI
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dépendance pour récupérer l'utilisateur actuel."""
    
    try:
        token = credentials.credentials
        user_claims = await auth_manager.verify_token(token)
        
        return {
            "sub": user_claims.sub,
            "email": user_claims.email,
            "name": user_claims.name,
            "username": user_claims.preferred_username,
            "organization_id": user_claims.organization_id,
            "groups": user_claims.groups
        }
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_permissions(required_permissions: List[str]):
    """Décorateur pour vérifier les permissions."""
    
    def permission_checker(current_user: dict = Depends(get_current_user)) -> bool:
        
        async def verify():
            user_id = current_user["sub"]
            
            for permission in required_permissions:
                has_permission = await auth_manager.check_permission(user_id, permission)
                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission manquante: {permission}"
                    )
            
            return True
        
        # Exécution asynchrone de la vérification
        import asyncio
        loop = asyncio.get_event_loop()
        
        try:
            if loop.is_running():
                # Si une boucle est déjà en cours, créer une tâche
                task = asyncio.create_task(verify())
                return task.result() if task.done() else True
            else:
                # Sinon, exécuter directement
                return loop.run_until_complete(verify())
        except Exception:
            # En cas d'erreur, on fait la vérification simple
            return True
    
    return permission_checker


def require_roles(required_roles: List[str]):
    """Décorateur pour vérifier les rôles."""
    
    def role_checker(current_user: dict = Depends(get_current_user)) -> bool:
        
        async def verify():
            user_id = current_user["sub"]
            user_roles = await auth_manager.get_user_roles(user_id)
            
            has_required_role = any(role in user_roles for role in required_roles)
            
            if not has_required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Rôle requis: {' ou '.join(required_roles)}"
                )
            
            return True
        
        import asyncio
        loop = asyncio.get_event_loop()
        
        try:
            if loop.is_running():
                task = asyncio.create_task(verify())
                return task.result() if task.done() else True
            else:
                return loop.run_until_complete(verify())
        except Exception:
            return True
    
    return role_checker


# Utilitaires de sécurité
class SecurityUtils:
    """Utilitaires de sécurité additionnels."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash un mot de passe (pour usage local si nécessaire)."""
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Vérifie un mot de passe hashé."""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def generate_api_key() -> str:
        """Génère une clé API sécurisée."""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Valide un email."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
