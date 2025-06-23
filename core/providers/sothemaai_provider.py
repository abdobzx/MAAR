"""
Adaptateur SothemaAI pour le système RAG multi-agents
"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from .sothemaai_client import create_sothemaai_client, SothemaAIError
from . import AIProvider

logger = logging.getLogger(__name__)

class SothemaAIProvider(AIProvider):
    """Adaptateur pour utiliser SothemaAI comme fournisseur d'IA dans le système RAG"""
    
    @property
    def name(self) -> str:
        return "SothemaAI"
        
    def __init__(self):
        self.client = None
        
    async def initialize(self):
        """Initialise le client SothemaAI"""
        try:
            self.client = create_sothemaai_client()
            logger.info("Fournisseur SothemaAI initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de SothemaAI: {e}")
            raise
            
    async def generate_text(
        self, 
        prompt: str, 
        max_tokens: int = 4096, 
        temperature: float = 0.7,
        context_chunks: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Génère du texte via SothemaAI
        
        Args:
            prompt: Le prompt pour la génération
            max_tokens: Nombre maximum de tokens (mappé vers max_length)
            temperature: Température (ignorée par SothemaAI pour l'instant)
            context_chunks: Contexte RAG (optionnel)
            **kwargs: Autres paramètres (ignorés)
            
        Returns:
            Le texte généré
        """
        if not self.client:
            raise SothemaAIError("Client SothemaAI non initialisé")
            
        try:
            async with self.client as client:
                response = await client.generate_text(
                    prompt=prompt,
                    max_length=max_tokens,
                    context_chunks=context_chunks
                )
                logger.info(f"Génération réussie via SothemaAI: {len(response)} caractères")
                return response
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération via SothemaAI: {e}")
            raise
            
    async def generate_streaming(
        self, 
        prompt: str, 
        max_tokens: int = 4096,
        temperature: float = 0.7,
        context_chunks: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Génère du texte en streaming via SothemaAI
        
        Args:
            prompt: Le prompt pour la génération
            max_tokens: Nombre maximum de tokens
            temperature: Température (ignorée)
            context_chunks: Contexte RAG (optionnel)
            **kwargs: Autres paramètres (ignorés)
            
        Yields:
            Chunks de texte généré
        """
        if not self.client:
            raise SothemaAIError("Client SothemaAI non initialisé")
            
        try:
            async with self.client as client:
                async for chunk in client.stream_generate_text(
                    prompt=prompt,
                    max_length=max_tokens,
                    context_chunks=context_chunks
                ):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Erreur lors du streaming via SothemaAI: {e}")
            raise
            
    async def generate_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """
        Génère des embeddings via SothemaAI
        
        Args:
            texts: Liste des textes à vectoriser
            **kwargs: Autres paramètres (ignorés)
            
        Returns:
            Liste des vecteurs d'embeddings
        """
        if not self.client:
            raise SothemaAIError("Client SothemaAI non initialisé")
            
        try:
            async with self.client as client:
                embeddings = await client.generate_embeddings(texts)
                logger.info(f"Embeddings générés via SothemaAI: {len(embeddings)} vecteurs")
                return embeddings
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération d'embeddings via SothemaAI: {e}")
            raise
            
    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations sur les modèles SothemaAI"""
        return {
            "provider": "SothemaAI",
            "llm_model": "mistralai/Mistral-7B-Instruct-v0.2",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "supports_streaming": True,  # Émulé
            "supports_rag": True,
            "max_context_length": 8192,
            "max_output_tokens": 4096
        }
        
    async def health_check(self) -> bool:
        """Vérifie la santé du service SothemaAI"""
        try:
            async with self.client as client:
                # Test simple avec un prompt court
                response = await client.generate_text(
                    prompt="Test", 
                    max_length=10
                )
                return len(response) > 0
                
        except Exception as e:
            logger.warning(f"Health check SothemaAI échoué: {e}")
            return False
