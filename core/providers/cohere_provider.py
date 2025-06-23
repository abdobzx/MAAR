"""
Cohere Provider pour le système MAR
"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import cohere
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class CohereProvider(BaseProvider):
    """Fournisseur Cohere pour le système MAR"""
    
    def __init__(self, api_key: str, model: str = "command", **kwargs):
        super().__init__(provider_name="cohere", model=model)
        self.client = cohere.AsyncClient(api_key)
        self.model = model
        self.max_tokens = kwargs.get('max_tokens', 1000)
        self.temperature = kwargs.get('temperature', 0.7)
        
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Génère une réponse en utilisant Cohere"""
        try:
            # Préparer le prompt avec le contexte système si fourni
            full_prompt = prompt
            if "system_prompt" in kwargs:
                full_prompt = f"{kwargs['system_prompt']}\n\n{prompt}"
            
            response = await self.client.generate(
                model=self.model,
                prompt=full_prompt,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                k=0,
                stop_sequences=[],
                return_likelihoods='NONE'
            )
            
            return response.generations[0].text.strip()
            
        except Exception as e:
            logger.error(f"Erreur Cohere: {e}")
            raise
    
    async def generate_streaming_response(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Génère une réponse en streaming avec Cohere"""
        try:
            full_prompt = prompt
            if "system_prompt" in kwargs:
                full_prompt = f"{kwargs['system_prompt']}\n\n{prompt}"
            
            stream = await self.client.generate(
                model=self.model,
                prompt=full_prompt,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                stream=True
            )
            
            async for token in stream:
                if token.event_type == 'text-generation':
                    yield token.text
                    
        except Exception as e:
            logger.error(f"Erreur streaming Cohere: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Génère des embeddings avec Cohere"""
        try:
            embedding_model = kwargs.get('embedding_model', 'embed-english-v3.0')
            
            response = await self.client.embed(
                model=embedding_model,
                texts=texts,
                input_type='search_document'
            )
            
            return response.embeddings
            
        except Exception as e:
            logger.error(f"Erreur embeddings Cohere: {e}")
            raise
    
    def is_available(self) -> bool:
        """Vérifie si le fournisseur est disponible"""
        try:
            return self.client is not None
        except:
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé du fournisseur"""
        try:
            # Test simple avec le modèle
            response = await self.client.generate(
                model=self.model,
                prompt="test",
                max_tokens=5
            )
            
            return {
                "status": "healthy",
                "provider": "cohere",
                "model": self.model,
                "response_received": bool(response.generations[0].text)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "cohere",
                "error": str(e)
            }
