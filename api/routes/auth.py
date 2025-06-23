"""
Routes d'authentification et d'autorisation pour l'API.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from core.models import APIResponse
from security.auth import AuthManager, TokenInfo, SecurityUtils


class LoginRequest(BaseModel):
    """Requête de connexion."""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    """Requête de rafraîchissement de token."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Requête de déconnexion."""
    refresh_token: str


class UserProfile(BaseModel):
    """Profil utilisateur."""
    id: str
    email: EmailStr
    name: str
    username: str
    organization_id: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


# Router pour les routes d'authentification
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_manager = AuthManager()
security = HTTPBearer()


@auth_router.post("/login", response_model=APIResponse[TokenInfo])
async def login(request: LoginRequest):
    """Authentifie un utilisateur et retourne les tokens."""
    
    try:
        # Validation basique
        if not request.username.strip() or not request.password.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nom d'utilisateur et mot de passe requis"
            )
        
        # Authentification via Keycloak
        token_info = await auth_manager.authenticate_user(
            request.username, 
            request.password
        )
        
        return APIResponse(
            success=True,
            data=token_info,
            message="Connexion réussie"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Échec de l'authentification: {str(e)}"
        )


@auth_router.post("/refresh", response_model=APIResponse[TokenInfo])
async def refresh_token(request: RefreshRequest):
    """Rafraîchit un token d'accès."""
    
    try:
        if not request.refresh_token.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token requis"
            )
        
        token_info = await auth_manager.refresh_token(request.refresh_token)
        
        return APIResponse(
            success=True,
            data=token_info,
            message="Token rafraîchi avec succès"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Impossible de rafraîchir le token: {str(e)}"
        )


@auth_router.post("/logout", response_model=APIResponse[bool])
async def logout(request: LogoutRequest):
    """Déconnecte un utilisateur."""
    
    try:
        success = await auth_manager.logout_user(request.refresh_token)
        
        return APIResponse(
            success=True,
            data=success,
            message="Déconnexion réussie" if success else "Déconnexion partielle"
        )
        
    except Exception as e:
        # Ne pas lever d'erreur pour la déconnexion
        return APIResponse(
            success=False,
            data=False,
            message=f"Erreur lors de la déconnexion: {str(e)}"
        )


@auth_router.get("/profile", response_model=APIResponse[UserProfile])
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Récupère le profil de l'utilisateur connecté."""
    
    try:
        user_id = current_user["sub"]
        
        # Récupération des rôles et permissions
        roles = await auth_manager.get_user_roles(user_id)
        permissions = list(await auth_manager.get_user_permissions(user_id))
        
        profile = UserProfile(
            id=user_id,
            email=current_user["email"],
            name=current_user["name"],
            username=current_user["username"],
            organization_id=current_user.get("organization_id"),
            roles=roles,
            permissions=permissions
        )
        
        return APIResponse(
            success=True,
            data=profile,
            message="Profil récupéré avec succès"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du profil: {str(e)}"
        )


@auth_router.get("/permissions")
async def get_user_permissions(current_user: dict = Depends(get_current_user)):
    """Récupère les permissions de l'utilisateur connecté."""
    
    try:
        user_id = current_user["sub"]
        permissions = list(await auth_manager.get_user_permissions(user_id))
        
        return APIResponse(
            success=True,
            data=permissions,
            message=f"{len(permissions)} permission(s) trouvée(s)"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des permissions: {str(e)}"
        )


@auth_router.get("/roles")
async def get_user_roles(current_user: dict = Depends(get_current_user)):
    """Récupère les rôles de l'utilisateur connecté."""
    
    try:
        user_id = current_user["sub"]
        roles = await auth_manager.get_user_roles(user_id)
        
        return APIResponse(
            success=True,
            data=roles,
            message=f"{len(roles)} rôle(s) trouvé(s)"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des rôles: {str(e)}"
        )


# Import pour éviter les dépendances circulaires
from security.auth import get_current_user
