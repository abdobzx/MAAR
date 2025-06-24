"""
Module de gestion de la plateforme MAR.
Évite les importations circulaires en centralisant l'accès à la plateforme.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class MARPlatform:
    """Gestionnaire de la plateforme MAR"""
    
    def __init__(self):
        self.vector_store = None
        self.llm_client = None
        self.mar_crew = None
        self.initialized = False
    
    async def initialize(self):
        """Initialise les composants de la plateforme"""
        try:
            logger.info("Initialisation de la plateforme MAR...")
            
            # Initialiser le vector store
            from vector_store.factory import create_vector_store
            self.vector_store = await create_vector_store(
                store_type=os.getenv("VECTOR_STORE_TYPE", "faiss"),
                config={
                    "persist_directory": os.getenv("VECTOR_STORE_PATH", "./data/vector_store"),
                    "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
                }
            )
            logger.info("Vector store initialisé")
            
            # Initialiser le client LLM
            from llm.ollama.client import OllamaClient
            self.llm_client = OllamaClient(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
            await self.llm_client.health_check()
            logger.info("Client LLM initialisé")
            
            # Initialiser le crew MAR
            from orchestrator.crew.mar_crew import MARCrew
            self.mar_crew = MARCrew(
                vector_store=self.vector_store,
                llm_client=self.llm_client
            )
            logger.info("MAR Crew initialisé")
            
            self.initialized = True
            logger.info("Plateforme MAR initialisée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur initialisation plateforme: {e}")
            # En mode développement, on peut continuer sans tous les composants
            if os.getenv("DEV_MODE", "false").lower() == "true":
                logger.warning("Mode développement: initialisation partielle")
                self.initialized = True
            else:
                raise
    
    async def shutdown(self):
        """Arrêt propre de la plateforme"""
        try:
            logger.info("Arrêt de la plateforme MAR...")
            
            # Fermeture des connexions
            if self.vector_store:
                # await self.vector_store.close()
                pass
            
            if self.llm_client:
                # await self.llm_client.close()
                pass
            
            logger.info("Plateforme MAR arrêtée proprement")
            
        except Exception as e:
            logger.error(f"Erreur arrêt plateforme: {e}")


# Instance globale de la plateforme
_platform_instance: Optional[MARPlatform] = None


def get_platform() -> MARPlatform:
    """
    Dependency pour récupérer l'instance de la plateforme
    
    Returns:
        Instance de MARPlatform
    """
    global _platform_instance
    if _platform_instance is None:
        _platform_instance = MARPlatform()
    return _platform_instance


async def initialize_platform():
    """Initialise la plateforme globale"""
    platform = get_platform()
    if not platform.initialized:
        await platform.initialize()


async def shutdown_platform():
    """Arrête la plateforme globale"""
    global _platform_instance
    if _platform_instance:
        await _platform_instance.shutdown()
        _platform_instance = None
