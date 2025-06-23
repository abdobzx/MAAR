"""
Client pour l'intégration avec le serveur SothemaAI
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
from dataclasses import dataclass
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class SothemaAIConfig:
    """Configuration pour le client SothemaAI"""
    base_url: str
    api_key: str
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0

class SothemaAIError(Exception):
    """Exception personnalisée pour les erreurs SothemaAI"""
    pass

class SothemaAIClient:
    """Client pour interagir avec le serveur SothemaAI"""
    
    def __init__(self, config: SothemaAIConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Gestionnaire de contexte asynchrone - entrée"""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        headers = {
            'X-API-Key': self.config.api_key,
            'Content-Type': 'application/json'
        }
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Gestionnaire de contexte asynchrone - sortie"""
        if self.session:
            await self.session.close()
            
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Effectue une requête HTTP avec gestion d'erreurs et retry"""
        if not self.session:
            raise SothemaAIError("Client not initialized. Use async context manager.")
            
        url = f"{self.config.base_url}/api{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Tentative {attempt + 1}/{self.config.max_retries} - {method} {url}")
                
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200 or response.status == 201:
                        return await response.json()
                    elif response.status == 401:
                        raise SothemaAIError("Clé API invalide ou expirée")
                    elif response.status == 403:
                        raise SothemaAIError("Accès refusé - vérifiez vos permissions")
                    elif response.status == 404:
                        raise SothemaAIError(f"Endpoint non trouvé: {endpoint}")
                    elif response.status == 503:
                        raise SothemaAIError("Service temporairement indisponible")
                    else:
                        error_text = await response.text()
                        raise SothemaAIError(f"Erreur HTTP {response.status}: {error_text}")
                        
            except aiohttp.ClientError as e:
                if attempt == self.config.max_retries - 1:
                    raise SothemaAIError(f"Erreur de connexion après {self.config.max_retries} tentatives: {e}")
                
                logger.warning(f"Tentative {attempt + 1} échouée, retry dans {self.config.retry_delay}s: {e}")
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                
    async def generate_text(
        self, 
        prompt: str, 
        max_length: int = 4096,
        context_chunks: Optional[List[str]] = None
    ) -> str:
        """
        Génère du texte via le service d'inférence SothemaAI
        
        Args:
            prompt: Le prompt pour la génération
            max_length: Longueur maximale de la réponse
            context_chunks: Chunks de contexte pour RAG (optionnel)
            
        Returns:
            Le texte généré
        """
        payload = {
            "text_input": prompt,
            "max_length": max_length
        }
        
        if context_chunks:
            payload["context_chunks"] = context_chunks
            
        try:
            response = await self._make_request(
                "POST", 
                "/inference/generate",
                json=payload
            )
            
            if response.get("status") == "success":
                return response.get("output_data", "")
            else:
                error_msg = response.get("error", "Erreur inconnue")
                raise SothemaAIError(f"Erreur de génération: {error_msg}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération de texte: {e}")
            raise
            
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Génère des embeddings via le service d'inférence SothemaAI
        
        Args:
            texts: Liste des textes à vectoriser
            
        Returns:
            Liste des vecteurs d'embeddings
        """
        payload = {"texts": texts}
        
        try:
            response = await self._make_request(
                "POST",
                "/inference/embed", 
                json=payload
            )
            
            if response.get("status") == "success":
                return response.get("embeddings", [])
            else:
                error_msg = response.get("error", "Erreur inconnue")
                raise SothemaAIError(f"Erreur d'embedding: {error_msg}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération d'embeddings: {e}")
            raise
            
    async def stream_generate_text(
        self, 
        prompt: str, 
        max_length: int = 4096,
        context_chunks: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Génère du texte en streaming (émulation pour compatibilité)
        Note: SothemaAI ne supporte pas le streaming natif, on émule
        """
        try:
            # Génération complète puis émulation du streaming
            full_response = await self.generate_text(prompt, max_length, context_chunks)
            
            # Découpage en chunks pour simuler le streaming
            chunk_size = 50  # Caractères par chunk
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.05)  # Petite pause pour simuler le streaming
                
        except Exception as e:
            logger.error(f"Erreur lors du streaming: {e}")
            raise

def create_sothemaai_client() -> SothemaAIClient:
    """
    Factory pour créer un client SothemaAI configuré depuis les variables d'environnement
    """
    base_url = os.getenv("SOTHEMAAI_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("SOTHEMAAI_API_KEY")
    timeout = int(os.getenv("SOTHEMAAI_TIMEOUT", "120"))
    
    if not api_key:
        raise ValueError(
            "SOTHEMAAI_API_KEY manquante. "
            "Générez une clé API via l'interface SothemaAI et ajoutez-la à votre .env"
        )
    
    config = SothemaAIConfig(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout
    )
    
    return SothemaAIClient(config)

# Test du client
async def test_sothemaai_client():
    """Test basique du client SothemaAI"""
    try:
        async with create_sothemaai_client() as client:
            # Test de génération de texte
            response = await client.generate_text(
                "Qu'est-ce que l'intelligence artificielle ?", 
                max_length=150
            )
            print(f"Réponse générée: {response}")
            
            # Test d'embeddings
            embeddings = await client.generate_embeddings([
                "Intelligence artificielle", 
                "Machine learning"
            ])
            print(f"Embeddings générés: {len(embeddings)} vecteurs")
            
    except Exception as e:
        logger.error(f"Test du client échoué: {e}")
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_sothemaai_client())
