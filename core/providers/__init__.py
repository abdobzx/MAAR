"""
Gestionnaire des fournisseurs d'IA pour le système RAG multi-agents
"""
import logging
import os
from typing import Dict, List, Optional, AsyncGenerator, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """Interface abstraite pour les fournisseurs d'IA"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du fournisseur"""
        pass
    
    @abstractmethod
    async def initialize(self):
        """Initialise le fournisseur"""
        pass
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Génère du texte"""
        pass
    
    @abstractmethod
    async def generate_streaming(
        self, 
        prompt: str, 
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Génère du texte en streaming"""
        pass
    
    @abstractmethod
    async def generate_embeddings(
        self, 
        texts: List[str], 
        **kwargs
    ) -> List[List[float]]:
        """Génère des embeddings"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations sur les modèles"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Vérifie la santé du service"""
        pass

class AIProviderManager:
    """Gestionnaire des fournisseurs d'IA"""
    
    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self.default_provider: Optional[str] = None
        
    async def register_provider(self, provider: AIProvider):
        """Enregistre un fournisseur d'IA"""
        try:
            await provider.initialize()
            self.providers[provider.name] = provider
            logger.info(f"Fournisseur {provider.name} enregistré avec succès")
            
            # Si c'est le premier fournisseur, le définir comme par défaut
            if not self.default_provider:
                self.default_provider = provider.name
                logger.info(f"Fournisseur par défaut défini: {provider.name}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du fournisseur {provider.name}: {e}")
            raise
            
    def set_default_provider(self, provider_name: str):
        """Définit le fournisseur par défaut"""
        if provider_name not in self.providers:
            raise ValueError(f"Fournisseur {provider_name} non trouvé")
        
        self.default_provider = provider_name
        logger.info(f"Fournisseur par défaut changé: {provider_name}")
        
    def get_provider(self, provider_name: Optional[str] = None) -> AIProvider:
        """Retourne un fournisseur spécifique ou le fournisseur par défaut"""
        target_provider = provider_name or self.default_provider
        
        if not target_provider:
            raise ValueError("Aucun fournisseur spécifié et aucun fournisseur par défaut")
            
        if target_provider not in self.providers:
            raise ValueError(f"Fournisseur {target_provider} non trouvé")
            
        return self.providers[target_provider]
        
    async def generate_text(
        self, 
        prompt: str, 
        provider_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """Génère du texte via un fournisseur"""
        provider = self.get_provider(provider_name)
        return await provider.generate_text(prompt, **kwargs)
        
    async def generate_streaming(
        self, 
        prompt: str, 
        provider_name: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Génère du texte en streaming via un fournisseur"""
        provider = self.get_provider(provider_name)
        async for chunk in provider.generate_streaming(prompt, **kwargs):
            yield chunk
            
    async def generate_embeddings(
        self, 
        texts: List[str], 
        provider_name: Optional[str] = None,
        **kwargs
    ) -> List[List[float]]:
        """Génère des embeddings via un fournisseur"""
        provider = self.get_provider(provider_name)
        return await provider.generate_embeddings(texts, **kwargs)
        
    def list_providers(self) -> List[Dict[str, Any]]:
        """Liste tous les fournisseurs enregistrés"""
        providers_info = []
        for name, provider in self.providers.items():
            info = provider.get_model_info()
            info["is_default"] = (name == self.default_provider)
            providers_info.append(info)
        return providers_info
        
    async def health_check_all(self) -> Dict[str, bool]:
        """Vérifie la santé de tous les fournisseurs"""
        health_status = {}
        for name, provider in self.providers.items():
            try:
                health_status[name] = await provider.health_check()
            except Exception as e:
                logger.error(f"Health check échoué pour {name}: {e}")
                health_status[name] = False
        return health_status

# Instance globale du gestionnaire
provider_manager = AIProviderManager()

async def get_provider_manager() -> AIProviderManager:
    """Retourne l'instance du gestionnaire de fournisseurs"""
    return provider_manager

async def initialize_providers():
    """Initialise tous les fournisseurs disponibles"""
    # Import conditionnel pour éviter les erreurs si les dépendances ne sont pas installées
    
    # Tentative d'initialisation de SothemaAI en priorité
    sothemaai_enabled = os.getenv("USE_SOTHEMAAI_ONLY", "false").lower() == "true"
    sothemaai_api_key = os.getenv("SOTHEMAAI_API_KEY")
    
    if sothemaai_api_key and (sothemaai_enabled or not any([
        os.getenv("COHERE_API_KEY"),
        os.getenv("OLLAMA_BASE_URL")
    ])):
        try:
            from .sothemaai_provider import SothemaAIProvider
            sothema_provider = SothemaAIProvider()
            await provider_manager.register_provider(sothema_provider)
            logger.info("SothemaAI configuré comme fournisseur principal")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de SothemaAI: {e}")
    
    # Tentative d'initialisation des autres fournisseurs si pas en mode SothemaAI uniquement
    if not sothemaai_enabled:
        
        # Cohere
        if os.getenv("COHERE_API_KEY"):
            try:
                from .cohere_provider import CohereProvider
                cohere_provider = CohereProvider()
                await provider_manager.register_provider(cohere_provider)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Cohere: {e}")
        
        # Ollama
        if os.getenv("OLLAMA_BASE_URL"):
            try:
                from .ollama_provider import OllamaProvider
                ollama_provider = OllamaProvider()
                await provider_manager.register_provider(ollama_provider)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Ollama: {e}")
    
    if not provider_manager.providers:
        raise RuntimeError(
            "Aucun fournisseur d'IA n'a pu être initialisé. "
            "Vérifiez vos clés API et variables d'environnement."
        )
    
    logger.info(f"Fournisseurs initialisés: {list(provider_manager.providers.keys())}")
