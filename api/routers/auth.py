"""
Router pour l'authentification (login, logout, register).
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from ..auth.dependencies import (
    TokenManager, authenticate_user, verify_api_key, 
    get_current_user, DEMO_USERS, DEMO_API_KEYS
)

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    """Requête de connexion"""
    username: str = Field(..., description="Nom d'utilisateur")
    password: str = Field(..., description="Mot de passe")


class LoginResponse(BaseModel):
    """Réponse de connexion"""
    access_token: str = Field(..., description="Token d'accès JWT")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_in: int = Field(..., description="Durée de validité en secondes")
    user: Dict[str, Any] = Field(..., description="Informations utilisateur")


class RegisterRequest(BaseModel):
    """Requête d'inscription"""
    username: str = Field(..., min_length=3, max_length=50, description="Nom d'utilisateur")
    email: EmailStr = Field(..., description="Adresse email")
    password: str = Field(..., min_length=6, description="Mot de passe")
    full_name: Optional[str] = Field(None, description="Nom complet")


class RegisterResponse(BaseModel):
    """Réponse d'inscription"""
    user_id: str = Field(..., description="ID de l'utilisateur créé")
    username: str = Field(..., description="Nom d'utilisateur")
    email: str = Field(..., description="Adresse email")
    message: str = Field(..., description="Message de confirmation")


class RefreshTokenRequest(BaseModel):
    """Requête de rafraîchissement de token"""
    refresh_token: str = Field(..., description="Token de rafraîchissement")


class ApiKeyRequest(BaseModel):
    """Requête de création de clé API"""
    name: str = Field(..., description="Nom de la clé API")
    permissions: list = Field(default=["read"], description="Permissions de la clé")
    expires_days: Optional[int] = Field(default=30, description="Durée de validité en jours")


class ApiKeyResponse(BaseModel):
    """Réponse de création de clé API"""
    api_key: str = Field(..., description="Clé API générée")
    key_id: str = Field(..., description="ID de la clé")
    name: str = Field(..., description="Nom de la clé")
    permissions: list = Field(..., description="Permissions")
    expires_at: datetime = Field(..., description="Date d'expiration")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authentifie un utilisateur et retourne un token JWT
    """
    try:
        logger.info(f"Tentative de connexion pour: {request.username}")
        
        # Authentifier l'utilisateur
        user = authenticate_user(request.username, request.password)
        
        if not user:
            logger.warning(f"Échec de connexion pour: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect"
            )
        
        # Créer le token JWT
        token_data = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"]
        }
        
        access_token = TokenManager.create_access_token(data=token_data)
        
        # Informations utilisateur (sans le hash du mot de passe)
        user_info = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"],
            "is_active": user["is_active"]
        }
        
        logger.info(f"Connexion réussie pour: {request.username}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint OAuth2 compatible pour l'authentification
    """
    try:
        # Utiliser le même processus que login
        request = LoginRequest(username=form_data.username, password=form_data.password)
        return await login(request)
        
    except Exception as e:
        logger.error(f"Erreur OAuth2 login: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    Inscrit un nouvel utilisateur
    """
    try:
        logger.info(f"Tentative d'inscription pour: {request.username}")
        
        # Vérifier si l'utilisateur existe déjà
        if request.username in DEMO_USERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nom d'utilisateur déjà pris"
            )
        
        # Vérifier si l'email existe déjà
        for user in DEMO_USERS.values():
            if user["email"] == request.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Adresse email déjà utilisée"
                )
        
        # TODO: En production, hasher le mot de passe avec bcrypt
        import hashlib
        password_hash = hashlib.sha256(request.password.encode()).hexdigest()
        
        # Créer le nouvel utilisateur
        new_user_id = str(len(DEMO_USERS) + 1)
        new_user = {
            "user_id": new_user_id,
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "roles": ["user"],  # Rôle par défaut
            "is_active": True,
            "created_at": datetime.utcnow(),
            "full_name": request.full_name
        }
        
        # Ajouter à la "base de données" de démo
        DEMO_USERS[request.username] = new_user
        
        logger.info(f"Utilisateur créé: {request.username}")
        
        return RegisterResponse(
            user_id=new_user_id,
            username=request.username,
            email=request.email,
            message="Utilisateur créé avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'inscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Déconnecte un utilisateur (invalidation du token)
    """
    try:
        logger.info(f"Déconnexion de: {current_user.get('username')}")
        
        # TODO: En production, ajouter le token à une blacklist
        # ou utiliser Redis pour gérer l'invalidation des tokens
        
        return {
            "message": "Déconnexion réussie",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Récupère les informations de l'utilisateur connecté
    """
    try:
        return {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
            "email": current_user.get("email"),
            "roles": current_user.get("roles", []),
            "token_expires_at": current_user.get("token_exp"),
            "auth_type": "jwt"
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération infos utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Crée une nouvelle clé API pour l'utilisateur
    """
    try:
        logger.info(f"Création clé API '{request.name}' pour: {current_user.get('username')}")
        
        # Générer une clé API unique
        import secrets
        api_key = f"sk-mar-{secrets.token_urlsafe(32)}"
        key_id = str(len(DEMO_API_KEYS) + 1)
        
        # Calculer la date d'expiration
        expires_at = datetime.utcnow() + timedelta(days=request.expires_days or 30)
        
        # Créer l'entrée de clé API
        api_key_data = {
            "key_id": key_id,
            "name": request.name,
            "user_id": current_user["user_id"],
            "roles": request.permissions,  # Utiliser les permissions comme rôles
            "is_active": True,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_used": None
        }
        
        # Ajouter à la "base de données" de démo
        DEMO_API_KEYS[api_key] = api_key_data
        
        logger.info(f"Clé API créée: {key_id}")
        
        return ApiKeyResponse(
            api_key=api_key,
            key_id=key_id,
            name=request.name,
            permissions=request.permissions,
            expires_at=expires_at
        )
        
    except Exception as e:
        logger.error(f"Erreur création clé API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.get("/api-keys")
async def list_api_keys(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Liste les clés API de l'utilisateur
    """
    try:
        user_keys = []
        
        for api_key, key_data in DEMO_API_KEYS.items():
            if key_data["user_id"] == current_user["user_id"]:
                user_keys.append({
                    "key_id": key_data["key_id"],
                    "name": key_data["name"],
                    "permissions": key_data["roles"],
                    "is_active": key_data["is_active"],
                    "created_at": key_data["created_at"],
                    "expires_at": key_data["expires_at"],
                    "last_used": key_data["last_used"],
                    "api_key": f"{api_key[:12]}..." + "*" * 20  # Masquer la clé
                })
        
        return {"api_keys": user_keys}
        
    except Exception as e:
        logger.error(f"Erreur liste clés API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Révoque une clé API
    """
    try:
        # Trouver la clé à révoquer
        key_to_revoke = None
        api_key_to_delete = None
        
        for api_key, key_data in DEMO_API_KEYS.items():
            if key_data["key_id"] == key_id and key_data["user_id"] == current_user["user_id"]:
                key_to_revoke = key_data
                api_key_to_delete = api_key
                break
        
        if not key_to_revoke:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clé API non trouvée"
            )
        
        # Supprimer la clé
        del DEMO_API_KEYS[api_key_to_delete]
        
        logger.info(f"Clé API révoquée: {key_id}")
        
        return {
            "message": "Clé API révoquée avec succès",
            "key_id": key_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur révocation clé API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )
