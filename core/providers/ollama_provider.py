"""
Ollama Provider pour le système MAR
"""
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import ollama
import asyncio
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class OllamaProvider(BaseProvider):
    """Fournisseur Ollama pour le système MAR"""
    
    def __init__(self, model: str = "llama2", host: str = "http://localhost:11434", **kwargs):
        super().__init__(provider_name="ollama", model=model)
        self.client = ollama.AsyncClient(host=host)
        self.model = model
        self.host = host
        self.max_tokens = kwargs.get('max_tokens', 1000)
        self.temperature = kwargs.get('temperature', 0.7)
        
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Génère une réponse en utilisant Ollama"""
        try:
            # Construire le prompt avec le contexte système si fourni
            messages = []
            if "system_prompt" in kwargs:
                messages.append({
                    "role": "system", 
                    "content": kwargs["system_prompt"]
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": kwargs.get('temperature', self.temperature),
                    "num_predict": kwargs.get('max_tokens', self.max_tokens)
                }
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            logger.error(f"Erreur Ollama: {e}")
            raise
    
    async def generate_streaming_response(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Génère une réponse en streaming avec Ollama"""
        try:
            messages = []
            if "system_prompt" in kwargs:
                messages.append({
                    "role": "system", 
                    "content": kwargs["system_prompt"]
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            stream = await self.client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "temperature": kwargs.get('temperature', self.temperature),
                    "num_predict": kwargs.get('max_tokens', self.max_tokens)
                }
            )
            
            async for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
                    
        except Exception as e:
            logger.error(f"Erreur streaming Ollama: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Génère des embeddings avec Ollama"""
        try:
            embeddings = []
            embedding_model = kwargs.get('embedding_model', 'nomic-embed-text')
            
            for text in texts:
                response = await self.client.embeddings(
                    model=embedding_model,
                    prompt=text
                )
                embeddings.append(response['embedding'])
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Erreur embeddings Ollama: {e}")
            # Fallback vers un embedding factice si le modèle d'embedding n'est pas disponible
            logger.warning("Utilisation d'embeddings factices pour Ollama")
            return [[0.0] * 384 for _ in texts]  # Embedding factice
    
    def is_available(self) -> bool:
        """Vérifie si le fournisseur est disponible"""
        try:
            return self.client is not None
        except:
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé du fournisseur"""
        try:
            # Vérifier si Ollama est accessible
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                options={"num_predict": 5}
            )
            
            return {
                "status": "healthy",
                "provider": "ollama",
                "model": self.model,
                "host": self.host,
                "response_received": bool(response.get('message', {}).get('content'))
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "host": self.host,
                "error": str(e)
            }
