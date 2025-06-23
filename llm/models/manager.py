"""
Gestionnaire de modèles LLM pour la plateforme MAR.
Support pour LLaMA3, Mistral, Phi-3, Code Llama et autres modèles.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import os

from ..ollama.client import OllamaClient, ModelNotFoundError

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Types de modèles supportés"""
    LLAMA3 = "llama3"
    LLAMA2 = "llama2"
    MISTRAL = "mistral"
    MIXTRAL = "mixtral"
    PHI3 = "phi3"
    CODE_LLAMA = "codellama"
    GEMMA = "gemma"
    NEURAL_CHAT = "neural-chat"
    VICUNA = "vicuna"
    ORCA_MINI = "orca-mini"


class ModelSize(str, Enum):
    """Tailles de modèles"""
    TINY = "tiny"      # < 1B params
    SMALL = "small"    # 1-3B params
    MEDIUM = "medium"  # 3-7B params
    LARGE = "large"    # 7-13B params
    XLARGE = "xlarge"  # 13-70B params
    XXLARGE = "xxlarge" # > 70B params


@dataclass
class ModelInfo:
    """Informations sur un modèle"""
    name: str
    type: ModelType
    size: ModelSize
    parameters: str
    description: str
    capabilities: List[str]
    context_length: int
    languages: List[str]
    use_cases: List[str]
    requirements: Dict[str, Any]
    available: bool = False
    downloaded: bool = False
    last_used: Optional[datetime] = None
    usage_count: int = 0
    avg_tokens_per_second: float = 0.0
    memory_usage_mb: int = 0


class ModelManager:
    """
    Gestionnaire de modèles LLM avec support complet d'Ollama
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        Initialise le gestionnaire de modèles
        
        Args:
            ollama_client: Client Ollama (optionnel)
        """
        self.ollama_client = ollama_client or OllamaClient()
        
        # Catalogue des modèles supportés
        self.model_catalog = self._initialize_model_catalog()
        
        # Modèles actuellement disponibles
        self.available_models: Dict[str, ModelInfo] = {}
        
        # Configuration par défaut
        self.default_models = {
            "chat": "llama3:8b",
            "code": "codellama:7b",
            "analysis": "mistral:7b",
            "embedding": "nomic-embed-text"
        }
        
        # Cache des métadonnées
        self._cache_file = "data/models_cache.json"
        self._last_refresh = None
        self._refresh_interval = timedelta(hours=1)
        
        logger.info("Gestionnaire de modèles initialisé")
    
    def _initialize_model_catalog(self) -> Dict[str, ModelInfo]:
        """Initialise le catalogue des modèles supportés"""
        
        catalog = {}
        
        # LLaMA 3 Models
        catalog["llama3:8b"] = ModelInfo(
            name="llama3:8b",
            type=ModelType.LLAMA3,
            size=ModelSize.MEDIUM,
            parameters="8B",
            description="LLaMA 3 8B - Modèle général haute performance",
            capabilities=["chat", "reasoning", "code", "analysis"],
            context_length=8192,
            languages=["en", "fr", "es", "de", "it", "pt"],
            use_cases=["chat", "qa", "summarization", "analysis"],
            requirements={"ram_gb": 8, "vram_gb": 6, "cpu_cores": 4}
        )
        
        catalog["llama3:70b"] = ModelInfo(
            name="llama3:70b",
            type=ModelType.LLAMA3,
            size=ModelSize.XLARGE,
            parameters="70B",
            description="LLaMA 3 70B - Modèle très haute performance",
            capabilities=["chat", "reasoning", "code", "analysis", "creative"],
            context_length=8192,
            languages=["en", "fr", "es", "de", "it", "pt", "ru", "zh"],
            use_cases=["complex_reasoning", "research", "creative_writing"],
            requirements={"ram_gb": 64, "vram_gb": 48, "cpu_cores": 8}
        )
        
        # Mistral Models
        catalog["mistral:7b"] = ModelInfo(
            name="mistral:7b",
            type=ModelType.MISTRAL,
            size=ModelSize.MEDIUM,
            parameters="7B",
            description="Mistral 7B - Modèle efficace et rapide",
            capabilities=["chat", "reasoning", "analysis"],
            context_length=32768,
            languages=["en", "fr", "es", "de", "it"],
            use_cases=["chat", "analysis", "classification"],
            requirements={"ram_gb": 6, "vram_gb": 4, "cpu_cores": 4}
        )
        
        catalog["mixtral:8x7b"] = ModelInfo(
            name="mixtral:8x7b",
            type=ModelType.MIXTRAL,
            size=ModelSize.LARGE,
            parameters="8x7B",
            description="Mixtral 8x7B - Modèle Mixture of Experts",
            capabilities=["chat", "reasoning", "code", "multilingual"],
            context_length=32768,
            languages=["en", "fr", "es", "de", "it", "pt", "ru"],
            use_cases=["complex_reasoning", "multilingual", "code"],
            requirements={"ram_gb": 32, "vram_gb": 24, "cpu_cores": 8}
        )
        
        # Phi-3 Models
        catalog["phi3:3.8b"] = ModelInfo(
            name="phi3:3.8b",
            type=ModelType.PHI3,
            size=ModelSize.SMALL,
            parameters="3.8B",
            description="Phi-3 Mini - Modèle compact haute qualité",
            capabilities=["chat", "reasoning", "math"],
            context_length=128000,
            languages=["en"],
            use_cases=["qa", "reasoning", "education"],
            requirements={"ram_gb": 4, "vram_gb": 2, "cpu_cores": 2}
        )
        
        catalog["phi3:14b"] = ModelInfo(
            name="phi3:14b",
            type=ModelType.PHI3,
            size=ModelSize.LARGE,
            parameters="14B",
            description="Phi-3 Medium - Performance équilibrée",
            capabilities=["chat", "reasoning", "math", "code"],
            context_length=128000,
            languages=["en"],
            use_cases=["reasoning", "math", "code", "research"],
            requirements={"ram_gb": 16, "vram_gb": 12, "cpu_cores": 4}
        )
        
        # Code Llama Models
        catalog["codellama:7b"] = ModelInfo(
            name="codellama:7b",
            type=ModelType.CODE_LLAMA,
            size=ModelSize.MEDIUM,
            parameters="7B",
            description="Code Llama 7B - Spécialisé en programmation",
            capabilities=["code", "debug", "explain"],
            context_length=16384,
            languages=["en"],
            use_cases=["coding", "debugging", "code_review"],
            requirements={"ram_gb": 6, "vram_gb": 4, "cpu_cores": 4}
        )
        
        catalog["codellama:13b"] = ModelInfo(
            name="codellama:13b",
            type=ModelType.CODE_LLAMA,
            size=ModelSize.LARGE,
            parameters="13B",
            description="Code Llama 13B - Programmation avancée",
            capabilities=["code", "debug", "explain", "architecture"],
            context_length=16384,
            languages=["en"],
            use_cases=["complex_coding", "architecture", "optimization"],
            requirements={"ram_gb": 12, "vram_gb": 8, "cpu_cores": 6}
        )
        
        # Gemma Models
        catalog["gemma:2b"] = ModelInfo(
            name="gemma:2b",
            type=ModelType.GEMMA,
            size=ModelSize.SMALL,
            parameters="2B",
            description="Gemma 2B - Modèle léger de Google",
            capabilities=["chat", "reasoning"],
            context_length=8192,
            languages=["en"],
            use_cases=["chat", "qa", "edge_deployment"],
            requirements={"ram_gb": 2, "vram_gb": 1, "cpu_cores": 2}
        )
        
        catalog["gemma:7b"] = ModelInfo(
            name="gemma:7b",
            type=ModelType.GEMMA,
            size=ModelSize.MEDIUM,
            parameters="7B",
            description="Gemma 7B - Performance équilibrée",
            capabilities=["chat", "reasoning", "safety"],
            context_length=8192,
            languages=["en"],
            use_cases=["chat", "qa", "safe_ai"],
            requirements={"ram_gb": 6, "vram_gb": 4, "cpu_cores": 4}
        )
        
        # Modèles spécialisés
        catalog["neural-chat:7b"] = ModelInfo(
            name="neural-chat:7b",
            type=ModelType.NEURAL_CHAT,
            size=ModelSize.MEDIUM,
            parameters="7B",
            description="Neural Chat - Optimisé pour la conversation",
            capabilities=["chat", "assistant", "helpful"],
            context_length=4096,
            languages=["en"],
            use_cases=["assistant", "customer_service", "help"],
            requirements={"ram_gb": 6, "vram_gb": 4, "cpu_cores": 4}
        )
        
        catalog["orca-mini:3b"] = ModelInfo(
            name="orca-mini:3b",
            type=ModelType.ORCA_MINI,
            size=ModelSize.SMALL,
            parameters="3B",
            description="Orca Mini - Modèle compact pour déploiement léger",
            capabilities=["chat", "qa"],
            context_length=2048,
            languages=["en"],
            use_cases=["edge", "mobile", "qa"],
            requirements={"ram_gb": 3, "vram_gb": 2, "cpu_cores": 2}
        )
        
        return catalog
    
    async def refresh_available_models(self, force: bool = False) -> List[str]:
        """
        Rafraîchit la liste des modèles disponibles
        
        Args:
            force: Forcer le rafraîchissement même si récent
            
        Returns:
            Liste des noms de modèles disponibles
        """
        try:
            # Vérifier si un rafraîchissement est nécessaire
            if not force and self._last_refresh:
                if datetime.now() - self._last_refresh < self._refresh_interval:
                    return list(self.available_models.keys())
            
            logger.info("Rafraîchissement des modèles disponibles...")
            
            # Récupérer la liste depuis Ollama
            ollama_models = await self.ollama_client.list_models()
            
            # Mettre à jour les modèles disponibles
            self.available_models.clear()
            
            for ollama_model in ollama_models:
                model_name = ollama_model["name"]
                
                # Chercher dans le catalogue
                if model_name in self.model_catalog:
                    model_info = self.model_catalog[model_name]
                    model_info.available = True
                    model_info.downloaded = True
                    
                    # Mettre à jour les métadonnées depuis Ollama
                    model_info.memory_usage_mb = ollama_model.get("size", 0) // (1024 * 1024)
                    
                else:
                    # Créer une entrée basique pour les modèles inconnus
                    model_info = ModelInfo(
                        name=model_name,
                        type=ModelType.LLAMA3,  # Par défaut
                        size=ModelSize.MEDIUM,
                        parameters="Unknown",
                        description=f"Modèle {model_name}",
                        capabilities=["chat"],
                        context_length=4096,
                        languages=["en"],
                        use_cases=["general"],
                        requirements={"ram_gb": 4, "vram_gb": 2, "cpu_cores": 2},
                        available=True,
                        downloaded=True,
                        memory_usage_mb=ollama_model.get("size", 0) // (1024 * 1024)
                    )
                
                self.available_models[model_name] = model_info
            
            self._last_refresh = datetime.now()
            
            # Sauvegarder le cache
            await self._save_cache()
            
            logger.info(f"Modèles disponibles mis à jour: {len(self.available_models)}")
            return list(self.available_models.keys())
            
        except Exception as e:
            logger.error(f"Erreur rafraîchissement modèles: {e}")
            return list(self.available_models.keys())
    
    async def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Récupère les informations d'un modèle
        
        Args:
            model_name: Nom du modèle
            
        Returns:
            Informations du modèle ou None
        """
        try:
            # Vérifier d'abord dans les modèles disponibles
            if model_name in self.available_models:
                return self.available_models[model_name]
            
            # Sinon chercher dans le catalogue
            if model_name in self.model_catalog:
                return self.model_catalog[model_name]
            
            # Essayer de récupérer depuis Ollama
            try:
                ollama_info = await self.ollama_client.show_model(model_name)
                
                # Créer une entrée basique
                model_info = ModelInfo(
                    name=model_name,
                    type=ModelType.LLAMA3,  # Par défaut
                    size=ModelSize.MEDIUM,
                    parameters="Unknown",
                    description=ollama_info.get("details", {}).get("description", f"Modèle {model_name}"),
                    capabilities=["chat"],
                    context_length=4096,
                    languages=["en"],
                    use_cases=["general"],
                    requirements={"ram_gb": 4, "vram_gb": 2, "cpu_cores": 2},
                    available=True,
                    downloaded=True
                )
                
                return model_info
                
            except ModelNotFoundError:
                return None
                
        except Exception as e:
            logger.error(f"Erreur récupération info modèle {model_name}: {e}")
            return None
    
    async def download_model(self, model_name: str) -> bool:
        """
        Télécharge un modèle
        
        Args:
            model_name: Nom du modèle à télécharger
            
        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"Téléchargement du modèle {model_name}...")
            
            # Vérifier si le modèle est dans le catalogue
            if model_name in self.model_catalog:
                model_info = self.model_catalog[model_name]
                
                # Vérifier les prérequis système
                if not self._check_system_requirements(model_info):
                    logger.warning(f"Prérequis système non satisfaits pour {model_name}")
                    return False
            
            # Lancer le téléchargement
            async for progress in await self.ollama_client.pull_model(model_name):
                if "status" in progress:
                    logger.info(f"Téléchargement {model_name}: {progress['status']}")
                
                if "completed" in progress and progress.get("completed"):
                    break
            
            # Rafraîchir la liste des modèles
            await self.refresh_available_models(force=True)
            
            logger.info(f"Modèle {model_name} téléchargé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur téléchargement modèle {model_name}: {e}")
            return False
    
    async def delete_model(self, model_name: str) -> bool:
        """
        Supprime un modèle
        
        Args:
            model_name: Nom du modèle à supprimer
            
        Returns:
            True si succès, False sinon
        """
        try:
            await self.ollama_client.delete_model(model_name)
            
            # Mettre à jour la liste locale
            if model_name in self.available_models:
                del self.available_models[model_name]
            
            logger.info(f"Modèle {model_name} supprimé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur suppression modèle {model_name}: {e}")
            return False
    
    def get_recommended_model(
        self,
        use_case: str,
        max_memory_gb: Optional[int] = None,
        prefer_speed: bool = False
    ) -> Optional[str]:
        """
        Recommande un modèle selon les critères
        
        Args:
            use_case: Cas d'usage (chat, code, analysis, etc.)
            max_memory_gb: Mémoire maximum disponible
            prefer_speed: Privilégier la vitesse
            
        Returns:
            Nom du modèle recommandé
        """
        try:
            candidates = []
            
            # Filtrer les modèles disponibles
            for name, model in self.available_models.items():
                if not model.available:
                    continue
                
                # Vérifier le cas d'usage
                if use_case not in model.use_cases and use_case not in model.capabilities:
                    continue
                
                # Vérifier la mémoire
                if max_memory_gb and model.requirements.get("ram_gb", 0) > max_memory_gb:
                    continue
                
                candidates.append((name, model))
            
            if not candidates:
                # Utiliser les modèles par défaut
                default_model = self.default_models.get(use_case)
                if default_model and default_model in self.available_models:
                    return default_model
                return None
            
            # Trier selon les préférences
            if prefer_speed:
                # Privilégier les modèles plus petits
                candidates.sort(key=lambda x: x[1].requirements.get("ram_gb", 0))
            else:
                # Privilégier les modèles plus performants
                candidates.sort(key=lambda x: x[1].requirements.get("ram_gb", 0), reverse=True)
            
            recommended = candidates[0][0]
            logger.info(f"Modèle recommandé pour {use_case}: {recommended}")
            
            return recommended
            
        except Exception as e:
            logger.error(f"Erreur recommandation modèle: {e}")
            return None
    
    async def get_models_by_capability(self, capability: str) -> List[str]:
        """
        Récupère les modèles avec une capacité spécifique
        
        Args:
            capability: Capacité recherchée
            
        Returns:
            Liste des modèles
        """
        models = []
        
        for name, model in self.available_models.items():
            if capability in model.capabilities and model.available:
                models.append(name)
        
        return models
    
    async def update_model_usage(self, model_name: str, tokens_generated: int, generation_time: float):
        """
        Met à jour les statistiques d'usage d'un modèle
        
        Args:
            model_name: Nom du modèle
            tokens_generated: Nombre de tokens générés
            generation_time: Temps de génération
        """
        try:
            if model_name in self.available_models:
                model = self.available_models[model_name]
                model.usage_count += 1
                model.last_used = datetime.now()
                
                # Calculer la moyenne mobile des tokens/seconde
                tokens_per_second = tokens_generated / generation_time if generation_time > 0 else 0
                if model.avg_tokens_per_second == 0:
                    model.avg_tokens_per_second = tokens_per_second
                else:
                    # Moyenne pondérée (80% ancien, 20% nouveau)
                    model.avg_tokens_per_second = (
                        model.avg_tokens_per_second * 0.8 + tokens_per_second * 0.2
                    )
                
                logger.debug(f"Stats mises à jour pour {model_name}: {tokens_per_second:.1f} tokens/s")
            
        except Exception as e:
            logger.warning(f"Erreur mise à jour stats modèle {model_name}: {e}")
    
    def _check_system_requirements(self, model_info: ModelInfo) -> bool:
        """
        Vérifie si les prérequis système sont satisfaits
        
        Args:
            model_info: Informations du modèle
            
        Returns:
            True si les prérequis sont OK
        """
        try:
            import psutil
            
            # Vérifier la RAM disponible
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
            required_ram = model_info.requirements.get("ram_gb", 0)
            
            if available_ram_gb < required_ram:
                logger.warning(f"RAM insuffisante: {available_ram_gb:.1f}GB disponible, {required_ram}GB requis")
                return False
            
            # Vérifier le nombre de CPU
            cpu_count = psutil.cpu_count()
            required_cpu = model_info.requirements.get("cpu_cores", 1)
            
            if cpu_count < required_cpu:
                logger.warning(f"CPU insuffisant: {cpu_count} cores disponibles, {required_cpu} requis")
                return False
            
            return True
            
        except ImportError:
            logger.warning("psutil non disponible, impossible de vérifier les prérequis")
            return True
        except Exception as e:
            logger.warning(f"Erreur vérification prérequis: {e}")
            return True
    
    async def _save_cache(self):
        """Sauvegarde le cache des modèles"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            
            cache_data = {
                "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                "available_models": {
                    name: asdict(model) for name, model in self.available_models.items()
                }
            }
            
            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.warning(f"Erreur sauvegarde cache: {e}")
    
    async def _load_cache(self):
        """Charge le cache des modèles"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                if cache_data.get("last_refresh"):
                    self._last_refresh = datetime.fromisoformat(cache_data["last_refresh"])
                
                # Charger les modèles depuis le cache
                for name, model_data in cache_data.get("available_models", {}).items():
                    # Convertir datetime strings en datetime objects
                    if model_data.get("last_used"):
                        model_data["last_used"] = datetime.fromisoformat(model_data["last_used"])
                    
                    self.available_models[name] = ModelInfo(**model_data)
                
                logger.info(f"Cache chargé: {len(self.available_models)} modèles")
                
        except Exception as e:
            logger.warning(f"Erreur chargement cache: {e}")
    
    def get_model_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques des modèles
        
        Returns:
            Statistiques complètes
        """
        stats = {
            "total_models": len(self.model_catalog),
            "available_models": len(self.available_models),
            "models_by_type": {},
            "models_by_size": {},
            "total_memory_usage_mb": 0,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "most_used_models": []
        }
        
        # Statistiques par type et taille
        for model in self.available_models.values():
            # Par type
            model_type = model.type.value
            stats["models_by_type"][model_type] = stats["models_by_type"].get(model_type, 0) + 1
            
            # Par taille
            model_size = model.size.value
            stats["models_by_size"][model_size] = stats["models_by_size"].get(model_size, 0) + 1
            
            # Mémoire totale
            stats["total_memory_usage_mb"] += model.memory_usage_mb
        
        # Modèles les plus utilisés
        used_models = [(name, model.usage_count) for name, model in self.available_models.items() if model.usage_count > 0]
        used_models.sort(key=lambda x: x[1], reverse=True)
        stats["most_used_models"] = used_models[:5]
        
        return stats
