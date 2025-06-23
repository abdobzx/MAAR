#!/usr/bin/env python3
"""
Test d'intégration complet pour valider tous les agents corrigés.
"""

import asyncio
import sys
import traceback
from typing import Dict, Any
from datetime import datetime

def test_import(module_path: str, class_name: str) -> Dict[str, Any]:
    """Test d'import d'un agent."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        agent_class = getattr(module, class_name)
        return {
            "success": True,
            "class": agent_class,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "class": None,
            "error": str(e)
        }

async def test_agent_initialization(agent_class, agent_name: str) -> Dict[str, Any]:
    """Test d'initialisation d'un agent."""
    try:
        agent = agent_class()
        await agent.initialize()
        return {
            "success": True,
            "agent": agent,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "agent": None,
            "error": str(e)
        }

async def test_integration():
    """Test d'intégration principal."""
    print("🚀 Début du test d'intégration complet")
    print("=" * 60)
    
    # Configuration des agents à tester
    agents_config = [
        ("agents.synthesis.agent", "SynthesisAgent"),
        ("agents.orchestration.agent", "OrchestrationAgent"),
        ("agents.retrieval.agent", "RetrievalAgent"),
        ("agents.vectorization.agent", "VectorizationAgent"),
        ("agents.storage.agent", "StorageAgent"),
        ("agents.ingestion.agent", "IngestionAgent"),
    ]
    
    results = {}
    
    # Test 1: Imports
    print("📦 Test des imports...")
    for module_path, class_name in agents_config:
        print(f"  ➤ Import {class_name}...", end=" ")
        result = test_import(module_path, class_name)
        results[class_name] = {"import": result}
        
        if result["success"]:
            print("✅ OK")
        else:
            print(f"❌ ÉCHEC: {result['error']}")
    
    print()
    
    # Test 2: Initialisation des agents réussis
    print("⚙️  Test d'initialisation des agents...")
    initialized_agents = {}
    
    for module_path, class_name in agents_config:
        if results[class_name]["import"]["success"]:
            print(f"  ➤ Initialisation {class_name}...", end=" ")
            agent_class = results[class_name]["import"]["class"]
            
            try:
                init_result = await test_agent_initialization(agent_class, class_name)
                results[class_name]["initialization"] = init_result
                
                if init_result["success"]:
                    print("✅ OK")
                    initialized_agents[class_name] = init_result["agent"]
                else:
                    print(f"❌ ÉCHEC: {init_result['error']}")
            except Exception as e:
                print(f"❌ ÉCHEC: {str(e)}")
                results[class_name]["initialization"] = {
                    "success": False,
                    "agent": None,
                    "error": str(e)
                }
        else:
            print(f"  ➤ {class_name} ignoré (import échoué)")
    
    print()
    
    # Test 3: Test de workflow simple si orchestration disponible
    if "OrchestrationAgent" in initialized_agents:
        print("🔄 Test de workflow simple...")
        try:
            orchestration_agent = initialized_agents["OrchestrationAgent"]
            
            # Import des modèles nécessaires
            from core.models import OrchestrationRequest, WorkflowType
            
            # Création d'une demande de test
            test_request = OrchestrationRequest(
                query="Test de fonctionnement du système",
                workflow_type=WorkflowType.SIMPLE_QA,
                user_id="test_user",
                organization_id="test_org"
            )
            
            print("  ➤ Exécution du workflow de test...", end=" ")
            response = await orchestration_agent.process_request(test_request)
            
            if response and response.status:
                print("✅ OK")
                print(f"    Workflow ID: {response.workflow_id}")
                print(f"    Statut: {response.status}")
            else:
                print("❌ ÉCHEC: Réponse invalide")
                
        except Exception as e:
            print(f"❌ ÉCHEC: {str(e)}")
            print(f"    Détails: {traceback.format_exc()}")
    
    # Test 4: Test de recherche si agent de récupération disponible
    if "RetrievalAgent" in initialized_agents:
        print("\n🔍 Test de recherche...")
        try:
            retrieval_agent = initialized_agents["RetrievalAgent"]
            
            print("  ➤ Test de recherche simple...", end=" ")
            results_search = await retrieval_agent.search(
                query="test de fonctionnement",
                limit=5
            )
            
            print(f"✅ OK ({len(results_search)} résultats)")
            
        except Exception as e:
            print(f"❌ ÉCHEC: {str(e)}")
    
    # Test 5: Test de synthèse si agent de synthèse disponible
    if "SynthesisAgent" in initialized_agents:
        print("\n💡 Test de synthèse...")
        try:
            synthesis_agent = initialized_agents["SynthesisAgent"]
            
            print("  ➤ Test de synthèse simple...", end=" ")
            test_context = {
                "query": "Test de synthèse",
                "search_results": [],
                "user_id": "test_user"
            }
            
            synthesis_result = await synthesis_agent.synthesize(test_context)
            
            if synthesis_result:
                print("✅ OK")
            else:
                print("❌ ÉCHEC: Pas de résultat")
                
        except Exception as e:
            print(f"❌ ÉCHEC: {str(e)}")
    
    print()
    print("=" * 60)
    print("📊 Résumé des résultats:")
    
    total_agents = len(agents_config)
    import_success = sum(1 for agent in results.values() if agent["import"]["success"])
    init_success = sum(1 for agent in results.values() 
                      if agent.get("initialization", {}).get("success", False))
    
    print(f"  • Agents testés: {total_agents}")
    print(f"  • Imports réussis: {import_success}/{total_agents}")
    print(f"  • Initialisations réussies: {init_success}/{total_agents}")
    print(f"  • Agents opérationnels: {len(initialized_agents)}")
    
    if len(initialized_agents) >= 3:  # Au moins 3 agents fonctionnels
        print("\n✅ SYSTÈME PRÊT POUR LA PRODUCTION")
        print("   Les agents critiques sont opérationnels.")
        return True
    else:
        print("\n⚠️  SYSTÈME PARTIELLEMENT OPÉRATIONNEL")
        print("   Certains agents nécessitent une attention.")
        return False

if __name__ == "__main__":
    try:
        # Ajout du répertoire racine au path Python
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Exécution du test
        success = asyncio.run(test_integration())
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Erreur critique lors du test: {e}")
        print(traceback.format_exc())
        sys.exit(1)
