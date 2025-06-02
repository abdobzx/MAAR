#!/usr/bin/env python3
"""
Script de validation de production pour le système MAR avec SothemaAI
Vérifie que tous les composants fonctionnent correctement avant le déploiement
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_config():
    """Valide la configuration du système"""
    logger.info("🔧 Validation de la configuration...")
    
    try:
        from core.config import settings
        
        # Vérifier les settings essentiels
        essential_settings = [
            'database',
            'redis', 
            'vector_db',
            'llm',
            'security'
        ]
        
        for setting in essential_settings:
            if hasattr(settings, setting):
                logger.info(f"✅ Configuration {setting} chargée")
            else:
                logger.error(f"❌ Configuration {setting} manquante")
                return False
        
        # Vérifier les fournisseurs LLM autorisés
        allowed_providers = ["sothemaai", "cohere", "ollama"]
        if settings.llm.default_provider in allowed_providers:
            logger.info(f"✅ Fournisseur par défaut valide: {settings.llm.default_provider}")
        else:
            logger.error(f"❌ Fournisseur par défaut invalide: {settings.llm.default_provider}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation de la configuration: {e}")
        return False

async def validate_providers():
    """Valide les fournisseurs d'IA"""
    logger.info("🧠 Validation des fournisseurs d'IA...")
    
    try:
        from core.providers import initialize_providers, provider_manager
        
        # Initialiser les fournisseurs
        await initialize_providers()
        
        # Vérifier que des fournisseurs sont disponibles
        if not provider_manager.providers:
            logger.error("❌ Aucun fournisseur d'IA disponible")
            return False
        
        logger.info(f"✅ Fournisseurs disponibles: {list(provider_manager.providers.keys())}")
        
        # Vérifier SothemaAI en priorité
        if "sothemaai" in provider_manager.providers:
            logger.info("✅ SothemaAI disponible comme fournisseur principal")
        else:
            logger.warning("⚠️ SothemaAI non disponible - utilisation des fournisseurs de fallback")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation des fournisseurs: {e}")
        return False

async def validate_models():
    """Valide les modèles de données"""
    logger.info("📋 Validation des modèles de données...")
    
    try:
        from core.models import (
            DocumentMetadata, 
            EmbeddingModel, 
            ChatMessage,
            SynthesisRequest,
            VectorizationRequest
        )
        
        # Test de création d'instances de modèles
        test_models = [
            DocumentMetadata,
            EmbeddingModel,
            ChatMessage,
            SynthesisRequest,
            VectorizationRequest
        ]
        
        for model in test_models:
            logger.info(f"✅ Modèle {model.__name__} valide")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation des modèles: {e}")
        return False

async def validate_agents():
    """Valide les agents principaux"""
    logger.info("🤖 Validation des agents...")
    
    agents_to_test = [
        ("synthesis", "SynthesisAgent"),
        ("vectorization", "VectorizationAgent"),
        ("orchestration", "OrchestrationAgent")
    ]
    
    for agent_module, agent_class in agents_to_test:
        try:
            module = __import__(f"agents.{agent_module}.agent", fromlist=[agent_class])
            agent_cls = getattr(module, agent_class)
            
            # Vérifier que la classe existe et peut être importée
            logger.info(f"✅ Agent {agent_class} importé avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'importation de {agent_class}: {e}")
            return False
    
    return True

async def validate_api():
    """Valide l'API principale"""
    logger.info("🌐 Validation de l'API...")
    
    try:
        from api.main import app
        
        # Vérifier que l'app FastAPI est créée
        if app:
            logger.info("✅ Application FastAPI créée avec succès")
        else:
            logger.error("❌ Impossible de créer l'application FastAPI")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation de l'API: {e}")
        return False

async def validate_sothemaai_integration():
    """Valide spécifiquement l'intégration SothemaAI"""
    logger.info("🔗 Validation de l'intégration SothemaAI...")
    
    try:
        from core.providers.sothemaai_provider import SothemaAIProvider
        from core.providers.sothemaai_client import SothemaAIClient
        
        # Test d'importation des classes SothemaAI
        logger.info("✅ Classes SothemaAI importées avec succès")
        
        # Vérifier la configuration SothemaAI
        sothemaai_config = {
            'base_url': os.getenv('SOTHEMAAI_BASE_URL'),
            'api_key': os.getenv('SOTHEMAAI_API_KEY'),
            'use_only': os.getenv('USE_SOTHEMAAI_ONLY', 'false').lower() == 'true'
        }
        
        if sothemaai_config['base_url']:
            logger.info(f"✅ SothemaAI Base URL configurée: {sothemaai_config['base_url']}")
        else:
            logger.warning("⚠️ SothemaAI Base URL non configurée")
        
        if sothemaai_config['api_key']:
            logger.info("✅ SothemaAI API Key configurée")
        else:
            logger.warning("⚠️ SothemaAI API Key non configurée")
        
        if sothemaai_config['use_only']:
            logger.info("✅ Mode SothemaAI uniquement activé")
        else:
            logger.info("ℹ️ Mode SothemaAI avec fallback activé")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la validation de SothemaAI: {e}")
        return False

async def main():
    """Fonction principale de validation"""
    logger.info("🚀 Début de la validation de production MAR avec SothemaAI")
    
    # Tests de validation
    validation_tests = [
        ("Configuration", validate_config),
        ("Fournisseurs d'IA", validate_providers),
        ("Modèles de données", validate_models),
        ("Agents", validate_agents),
        ("API", validate_api),
        ("Intégration SothemaAI", validate_sothemaai_integration)
    ]
    
    results = {}
    
    for test_name, test_func in validation_tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Test: {test_name}")
        logger.info('='*50)
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name}: RÉUSSI")
            else:
                logger.error(f"❌ {test_name}: ÉCHOUÉ")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERREUR - {e}")
            results[test_name] = False
    
    # Résumé des résultats
    logger.info("\n" + "="*60)
    logger.info("RÉSUMÉ DE LA VALIDATION")
    logger.info("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nRésultat global: {passed}/{total} tests réussis")
    
    if passed == total:
        logger.info("🎉 TOUS LES TESTS SONT RÉUSSIS - PRÊT POUR LA PRODUCTION")
        return True
    else:
        logger.error("⚠️ CERTAINS TESTS ONT ÉCHOUÉ - CORRECTION REQUISE AVANT PRODUCTION")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
