"""
Client Ollama pour interaction avec les LLMs locaux.
"""

import aiohttp
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Exception spécifique à Ollama"""
    pass


class ModelNotFoundError(OllamaError):
    """Modèle non trouvé"""
    pass


class OllamaClient:
    """
    Client asynchrone pour l'API Ollama
    Support complet des fonctionnalités Ollama avec gestion d'erreurs robuste
    """
    
    def __init__(
        self,
        base_url: str = None,
        timeout: int = 120,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialise le client Ollama
        
        Args:
            base_url: URL de base d'Ollama (défaut: http://localhost:11434)
            timeout: Timeout en secondes pour les requêtes
            max_retries: Nombre maximum de tentatives
            retry_delay: Délai entre les tentatives
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Statistiques
        self.stats = {
            "requests_count": 0,
            "errors_count": 0,
            "total_tokens": 0,
            "total_generation_time": 0.0,
            "last_request": None
        }
        
        # Session HTTP réutilisable
        self._session = None
        
        logger.info(f"Client Ollama initialisé: {self.base_url}")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Assure qu'une session HTTP est disponible"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                keepalive_timeout=30
            )
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
    
    async def close(self):
        """Ferme la session HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Effectue une requête HTTP vers Ollama avec retry automatique
        
        Args:
            method: Méthode HTTP (GET, POST, etc.)
            endpoint: Endpoint API
            data: Données à envoyer
            stream: Si True, retourne un générateur pour streaming
            
        Returns:
            Réponse JSON ou générateur asynchrone
        """
        await self._ensure_session()
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries + 1):
            try:
                self.stats["requests_count"] += 1
                self.stats["last_request"] = datetime.now().isoformat()
                
                if stream:
                    return self._stream_request(method, url, data)
                else:
                    async with self._session.request(method, url, json=data) as response:
                        await self._check_response(response)
                        return await response.json()
                        
            except aiohttp.ClientError as e:
                self.stats["errors_count"] += 1
                
                if attempt == self.max_retries:
                    logger.error(f"Échec définitif requête Ollama après {self.max_retries + 1} tentatives: {e}")
                    raise OllamaError(f"Erreur communication Ollama: {e}")
                
                logger.warning(f"Tentative {attempt + 1} échouée, retry dans {self.retry_delay}s: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                
            except Exception as e:
                self.stats["errors_count"] += 1
                logger.error(f"Erreur inattendue requête Ollama: {e}")
                raise OllamaError(f"Erreur inattendue: {e}")
    
    async def _stream_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Gère les requêtes en streaming"""
        
        async with self._session.request(method, url, json=data) as response:
            await self._check_response(response)
            
            async for line in response.content:
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8').strip())
                        yield chunk
                    except json.JSONDecodeError:
                        continue
    
    async def _check_response(self, response: aiohttp.ClientResponse):
        """Vérifie le statut de la réponse HTTP"""
        
        if response.status == 404:
            error_data = await response.json()
            error_msg = error_data.get("error", "Modèle non trouvé")
            raise ModelNotFoundError(error_msg)
        
        elif response.status >= 400:
            try:
                error_data = await response.json()
                error_msg = error_data.get("error", f"Erreur HTTP {response.status}")
            except:
                error_msg = f"Erreur HTTP {response.status}"
            
            raise OllamaError(error_msg)
    
    # Méthodes de l'API Ollama
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Liste les modèles disponibles
        
        Returns:
            Liste des modèles avec leurs métadonnées
        """
        try:
            response = await self._make_request("GET", "/api/tags")
            models = response.get("models", [])
            
            logger.info(f"Modèles disponibles: {len(models)}")
            return models
            
        except Exception as e:
            logger.error(f"Erreur liste modèles: {e}")
            raise
    
    async def show_model(self, model: str) -> Dict[str, Any]:
        """
        Affiche les détails d'un modèle
        
        Args:
            model: Nom du modèle
            
        Returns:
            Détails du modèle
        """
        try:
            data = {"name": model}
            response = await self._make_request("POST", "/api/show", data)
            
            logger.info(f"Détails modèle {model} récupérés")
            return response
            
        except Exception as e:
            logger.error(f"Erreur détails modèle {model}: {e}")
            raise
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        context: Optional[List[int]] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Génère du texte avec un modèle
        
        Args:
            model: Nom du modèle à utiliser
            prompt: Prompt d'entrée
            system: Message système optionnel
            options: Options de génération
            stream: Activer le streaming
            context: Contexte de conversation
            
        Returns:
            Réponse générée ou générateur pour streaming
        """
        try:
            start_time = time.time()
            
            data = {
                "model": model,
                "prompt": prompt,
                "stream": stream
            }
            
            if system:
                data["system"] = system
            
            if options:
                data["options"] = options
            
            if context:
                data["context"] = context
            
            if stream:
                logger.info(f"Génération streaming avec {model}: {prompt[:100]}...")
                
                async def stream_generator():
                    total_tokens = 0
                    async for chunk in await self._make_request("POST", "/api/generate", data, stream=True):
                        if "response" in chunk:
                            total_tokens += 1
                        yield chunk
                    
                    # Mettre à jour les stats
                    generation_time = time.time() - start_time
                    self.stats["total_tokens"] += total_tokens
                    self.stats["total_generation_time"] += generation_time
                
                return stream_generator()
            
            else:
                logger.info(f"Génération avec {model}: {prompt[:100]}...")
                response = await self._make_request("POST", "/api/generate", data)
                
                # Mettre à jour les stats
                generation_time = time.time() - start_time
                tokens = len(response.get("response", "").split())
                self.stats["total_tokens"] += tokens
                self.stats["total_generation_time"] += generation_time
                
                logger.info(f"Génération terminée: {tokens} tokens en {generation_time:.2f}s")
                return response
                
        except Exception as e:
            logger.error(f"Erreur génération avec {model}: {e}")
            raise
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Interface de chat avec conversation
        
        Args:
            model: Nom du modèle
            messages: Historique de conversation
            options: Options de génération
            stream: Activer le streaming
            
        Returns:
            Réponse de chat ou générateur
        """
        try:
            start_time = time.time()
            
            data = {
                "model": model,
                "messages": messages,
                "stream": stream
            }
            
            if options:
                data["options"] = options
            
            if stream:
                logger.info(f"Chat streaming avec {model}: {len(messages)} messages")
                
                async def chat_stream_generator():
                    total_tokens = 0
                    async for chunk in await self._make_request("POST", "/api/chat", data, stream=True):
                        if "message" in chunk:
                            total_tokens += 1
                        yield chunk
                    
                    generation_time = time.time() - start_time
                    self.stats["total_tokens"] += total_tokens
                    self.stats["total_generation_time"] += generation_time
                
                return chat_stream_generator()
            
            else:
                logger.info(f"Chat avec {model}: {len(messages)} messages")
                response = await self._make_request("POST", "/api/chat", data)
                
                generation_time = time.time() - start_time
                if "message" in response and "content" in response["message"]:
                    tokens = len(response["message"]["content"].split())
                    self.stats["total_tokens"] += tokens
                self.stats["total_generation_time"] += generation_time
                
                return response
                
        except Exception as e:
            logger.error(f"Erreur chat avec {model}: {e}")
            raise
    
    async def pull_model(
        self,
        model: str,
        insecure: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Télécharge un modèle
        
        Args:
            model: Nom du modèle à télécharger
            insecure: Autoriser les connexions non sécurisées
            
        Returns:
            Générateur de progression
        """
        try:
            data = {"name": model}
            if insecure:
                data["insecure"] = True
            
            logger.info(f"Téléchargement du modèle {model}...")
            
            async for chunk in await self._make_request("POST", "/api/pull", data, stream=True):
                yield chunk
                
        except Exception as e:
            logger.error(f"Erreur téléchargement modèle {model}: {e}")
            raise
    
    async def delete_model(self, model: str) -> Dict[str, Any]:
        """
        Supprime un modèle
        
        Args:
            model: Nom du modèle à supprimer
            
        Returns:
            Confirmation de suppression
        """
        try:
            data = {"name": model}
            response = await self._make_request("DELETE", "/api/delete", data)
            
            logger.info(f"Modèle {model} supprimé")
            return response
            
        except Exception as e:
            logger.error(f"Erreur suppression modèle {model}: {e}")
            raise
    
    async def copy_model(self, source: str, destination: str) -> Dict[str, Any]:
        """
        Copie un modèle
        
        Args:
            source: Modèle source
            destination: Nom du nouveau modèle
            
        Returns:
            Confirmation de copie
        """
        try:
            data = {"source": source, "destination": destination}
            response = await self._make_request("POST", "/api/copy", data)
            
            logger.info(f"Modèle {source} copié vers {destination}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur copie modèle {source} -> {destination}: {e}")
            raise
    
    async def create_model(
        self,
        name: str,
        modelfile: str,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Crée un modèle personnalisé à partir d'un Modelfile
        
        Args:
            name: Nom du nouveau modèle
            modelfile: Contenu du Modelfile
            stream: Activer le streaming
            
        Returns:
            Réponse de création ou générateur
        """
        try:
            data = {
                "name": name,
                "modelfile": modelfile,
                "stream": stream
            }
            
            if stream:
                logger.info(f"Création streaming du modèle {name}...")
                return await self._make_request("POST", "/api/create", data, stream=True)
            else:
                logger.info(f"Création du modèle {name}...")
                response = await self._make_request("POST", "/api/create", data)
                logger.info(f"Modèle {name} créé avec succès")
                return response
                
        except Exception as e:
            logger.error(f"Erreur création modèle {name}: {e}")
            raise
    
    async def embeddings(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Génère des embeddings pour un texte
        
        Args:
            model: Modèle à utiliser
            prompt: Texte à encoder
            options: Options de génération
            
        Returns:
            Vecteur d'embeddings
        """
        try:
            data = {
                "model": model,
                "prompt": prompt
            }
            
            if options:
                data["options"] = options
            
            logger.info(f"Génération embeddings avec {model}: {prompt[:50]}...")
            response = await self._make_request("POST", "/api/embeddings", data)
            
            embedding_dim = len(response.get("embedding", []))
            logger.info(f"Embeddings générés: {embedding_dim} dimensions")
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur génération embeddings avec {model}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Vérifie la santé du service Ollama
        
        Returns:
            Statut de santé
        """
        try:
            # Ollama n'a pas d'endpoint de santé officiel, on teste avec list_models
            models = await self.list_models()
            
            return {
                "status": "healthy",
                "models_count": len(models),
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du client
        
        Returns:
            Statistiques d'utilisation
        """
        stats = self.stats.copy()
        
        # Calculer des métriques dérivées
        if stats["requests_count"] > 0:
            stats["error_rate"] = stats["errors_count"] / stats["requests_count"]
            stats["avg_generation_time"] = stats["total_generation_time"] / stats["requests_count"]
            
            if stats["total_generation_time"] > 0:
                stats["tokens_per_second"] = stats["total_tokens"] / stats["total_generation_time"]
        
        return stats
    
    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            "requests_count": 0,
            "errors_count": 0,
            "total_tokens": 0,
            "total_generation_time": 0.0,
            "last_request": None
        }
        logger.info("Statistiques Ollama remises à zéro")


# Instance par défaut pour utilisation simple
default_client = OllamaClient()
