"""
Base Provider pour le système MAR
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

class BaseProvider(ABC):
    """Classe de base pour tous les fournisseurs d'IA"""
    
    def __init__(self, provider_name: str, model: str):
        self.provider_name = provider_name
        self.model = model
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Génère une réponse textuelle"""
        pass
    
    @abstractmethod
    async def generate_streaming_response(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Génère une réponse en streaming"""
        pass
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Génère des embeddings pour les textes donnés"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le fournisseur est disponible"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Effectue un contrôle de santé du fournisseur"""
        pass
    
    def get_model_info(self) -> Dict[str, str]:
        """Retourne les informations sur le modèle"""
        return {
            "provider": self.provider_name,
            "model": self.model
        }
    
    def __str__(self) -> str:
        return f"{self.provider_name}:{self.model}"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(provider='{self.provider_name}', model='{self.model}')>"
