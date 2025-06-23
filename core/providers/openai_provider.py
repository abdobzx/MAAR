"""
OpenAI Provider pour le système MAR
"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseProvider):
    """Fournisseur OpenAI pour le système MAR"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", **kwargs):
        super().__init__(provider_name="openai", model=model)
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = kwargs.get('max_tokens', 1000)
        self.temperature = kwargs.get('temperature', 0.7)
        
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Génère une réponse en utilisant OpenAI"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Ajouter le contexte système si fourni
            if "system_prompt" in kwargs:
                messages.insert(0, {"role": "system", "content": kwargs["system_prompt"]})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature)
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erreur OpenAI: {e}")
            raise
    
    async def generate_streaming_response(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Génère une réponse en streaming avec OpenAI"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            if "system_prompt" in kwargs:
                messages.insert(0, {"role": "system", "content": kwargs["system_prompt"]})
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Erreur streaming OpenAI: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Génère des embeddings avec OpenAI"""
        try:
            embedding_model = kwargs.get('embedding_model', 'text-embedding-ada-002')
            
            response = await self.client.embeddings.create(
                model=embedding_model,
                input=texts
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Erreur embeddings OpenAI: {e}")
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            return {
                "status": "healthy",
                "provider": "openai",
                "model": self.model,
                "response_received": bool(response.choices[0].message.content)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "openai",
                "error": str(e)
            }
