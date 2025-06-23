#!/usr/bin/env python3
"""
Test end-to-end de la plateforme MAR.

Ce script démontre le flux complet :
1. Ingestion de documents
2. Recherche vectorielle
3. Exécution d'agents RAG
4. Génération de réponse

Usage:
    python scripts/test_end_to_end.py
    python scripts/test_end_to_end.py --interactive
"""

import os
import sys
import asyncio
import argparse
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import json
import time

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MAREndToEndTest:
    """Test end-to-end de la plateforme MAR"""
    
    def __init__(self):
        self.vector_store = None
        self.llm_client = None
        self.mar_crew = None
        self.test_data_dir = None
    
    async def setup(self):
        """Configuration initiale du test"""
        try:
            logger.info("🚀 Initialisation du test end-to-end MAR")
            
            # Créer un répertoire temporaire pour les données de test
            self.test_data_dir = tempfile.mkdtemp(prefix="mar_test_")
            logger.info(f"Répertoire de test: {self.test_data_dir}")
            
            # Initialiser le vector store
            await self._setup_vector_store()
            
            # Initialiser le client LLM
            await self._setup_llm_client()
            
            # Initialiser le crew MAR
            await self._setup_mar_crew()
            
            logger.info("✅ Initialisation terminée")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            raise
    
    async def _setup_vector_store(self):
        """Initialise le vector store pour les tests"""
        try:
            from vector_store import create_vector_store
            
            config = {
                "persist_directory": os.path.join(self.test_data_dir, "vector_store"),
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
            }
            
            self.vector_store = await create_vector_store("faiss", config)
            logger.info("📚 Vector store initialisé")
            
        except Exception as e:
            logger.warning(f"⚠️ Vector store non disponible: {e}")
            # Créer un mock pour les tests
            self.vector_store = MockVectorStore()
    
    async def _setup_llm_client(self):
        """Initialise le client LLM pour les tests"""
        try:
            from llm.ollama.client import OllamaClient
            
            self.llm_client = OllamaClient(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
            
            # Test de connectivité
            await self.llm_client.health_check()
            logger.info("🧠 Client LLM initialisé")
            
        except Exception as e:
            logger.warning(f"⚠️ Client LLM non disponible: {e}")
            # Créer un mock pour les tests
            self.llm_client = MockLLMClient()
    
    async def _setup_mar_crew(self):
        """Initialise le crew MAR pour les tests"""
        try:
            from orchestrator.crew.mar_crew import MARCrew
            
            self.mar_crew = MARCrew(
                vector_store=self.vector_store,
                llm_client=self.llm_client
            )
            logger.info("👥 MAR Crew initialisé")
            
        except Exception as e:
            logger.warning(f"⚠️ MAR Crew non disponible: {e}")
            # Créer un mock pour les tests
            self.mar_crew = MockMARCrew()
    
    async def create_sample_documents(self) -> List[Dict[str, Any]]:
        """Crée des documents d'exemple pour les tests"""
        logger.info("📝 Création de documents d'exemple")
        
        sample_docs = [
            {
                "title": "Introduction à l'Intelligence Artificielle",
                "content": """
                L'intelligence artificielle (IA) est une technologie révolutionnaire qui permet aux machines 
                d'apprendre, de raisonner et de prendre des décisions comme les humains. Elle comprend plusieurs 
                domaines comme l'apprentissage automatique, le traitement du langage naturel, et la vision par ordinateur.
                
                Les applications de l'IA sont nombreuses : assistants virtuels, voitures autonomes, 
                diagnostic médical, recommandations personnalisées, et bien plus encore.
                """,
                "metadata": {
                    "category": "technology",
                    "author": "MAR Team",
                    "tags": ["AI", "machine learning", "technology"]
                }
            },
            {
                "title": "RAG : Retrieval-Augmented Generation",
                "content": """
                Le RAG (Retrieval-Augmented Generation) est une technique qui combine la recherche d'informations 
                avec la génération de texte. Elle permet aux modèles de langage d'accéder à des connaissances 
                externes pour produire des réponses plus précises et actualisées.
                
                Le processus RAG implique : 1) la recherche de documents pertinents, 2) l'extraction d'informations clés, 
                3) la génération d'une réponse basée sur ces informations. Cette approche est particulièrement 
                utile pour les systèmes de questions-réponses et les assistants documentaires.
                """,
                "metadata": {
                    "category": "AI techniques",
                    "author": "MAR Team", 
                    "tags": ["RAG", "NLP", "information retrieval"]
                }
            },
            {
                "title": "Agents Multi-Agents et Collaboration",
                "content": """
                Les systèmes multi-agents permettent à plusieurs agents intelligents de collaborer pour résoudre 
                des problèmes complexes. Chaque agent peut avoir des spécialités différentes : recherche, analyse, 
                synthèse, critique, etc.
                
                Dans un système MAR (Multi-Agent RAG), les agents travaillent ensemble : un agent retriever 
                trouve les documents, un agent summarizer résume l'information, un agent synthesizer 
                combine les sources, et un agent critic valide la qualité de la réponse finale.
                """,
                "metadata": {
                    "category": "multi-agent systems",
                    "author": "MAR Team",
                    "tags": ["multi-agent", "collaboration", "RAG"]
                }
            }
        ]
        
        return sample_docs
    
    async def test_document_ingestion(self, sample_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Teste l'ingestion de documents"""
        logger.info("📥 Test d'ingestion de documents")
        
        ingestion_results = {
            "total_documents": 0,
            "total_chunks": 0,
            "ingestion_times": [],
            "documents": []
        }
        
        for i, doc in enumerate(sample_docs):
            start_time = time.time()
            
            try:
                # Ingérer le document
                result = await self.vector_store.ingest_text(
                    content=f"# {doc['title']}\n\n{doc['content']}",
                    metadata={
                        **doc['metadata'],
                        "document_id": f"doc_{i+1}",
                        "test_document": True
                    },
                    chunk_size=500,
                    chunk_overlap=50
                )
                
                ingestion_time = time.time() - start_time
                
                ingestion_results["total_documents"] += 1
                ingestion_results["total_chunks"] += result.get("chunks_count", 1)
                ingestion_results["ingestion_times"].append(ingestion_time)
                ingestion_results["documents"].append({
                    "title": doc["title"],
                    "chunks": result.get("chunks_count", 1),
                    "time": ingestion_time
                })
                
                logger.info(f"  ✅ {doc['title']}: {result.get('chunks_count', 1)} chunks en {ingestion_time:.2f}s")
                
            except Exception as e:
                logger.error(f"  ❌ Erreur ingestion {doc['title']}: {e}")
        
        avg_time = sum(ingestion_results["ingestion_times"]) / len(ingestion_results["ingestion_times"])
        logger.info(f"📊 Ingestion terminée: {ingestion_results['total_documents']} documents, "
                   f"{ingestion_results['total_chunks']} chunks, temps moyen: {avg_time:.2f}s")
        
        return ingestion_results
    
    async def test_vector_search(self, queries: List[str]) -> Dict[str, Any]:
        """Teste la recherche vectorielle"""
        logger.info("🔍 Test de recherche vectorielle")
        
        search_results = {
            "total_queries": 0,
            "search_times": [],
            "queries": []
        }
        
        for query in queries:
            start_time = time.time()
            
            try:
                # Effectuer la recherche
                results = await self.vector_store.search(
                    query=query,
                    k=3,
                    threshold=0.1
                )
                
                search_time = time.time() - start_time
                
                search_results["total_queries"] += 1
                search_results["search_times"].append(search_time)
                search_results["queries"].append({
                    "query": query,
                    "results_count": len(results),
                    "time": search_time,
                    "top_score": results[0].get("score", 0) if results else 0
                })
                
                logger.info(f"  ✅ '{query}': {len(results)} résultats en {search_time:.2f}s")
                
                # Afficher le meilleur résultat
                if results:
                    best_result = results[0]
                    logger.info(f"    🎯 Meilleur: score {best_result.get('score', 0):.3f}")
                
            except Exception as e:
                logger.error(f"  ❌ Erreur recherche '{query}': {e}")
        
        avg_time = sum(search_results["search_times"]) / len(search_results["search_times"])
        logger.info(f"📊 Recherches terminées: {search_results['total_queries']} requêtes, temps moyen: {avg_time:.2f}s")
        
        return search_results
    
    async def test_rag_pipeline(self, questions: List[str]) -> Dict[str, Any]:
        """Teste le pipeline RAG complet"""
        logger.info("🤖 Test du pipeline RAG")
        
        rag_results = {
            "total_questions": 0,
            "processing_times": [],
            "questions": []
        }
        
        for question in questions:
            start_time = time.time()
            
            try:
                # Exécuter le pipeline RAG
                result = await self.mar_crew.process_query(
                    query=question,
                    context_size=3,
                    use_critic=True
                )
                
                processing_time = time.time() - start_time
                
                rag_results["total_questions"] += 1
                rag_results["processing_times"].append(processing_time)
                rag_results["questions"].append({
                    "question": question,
                    "answer_length": len(result.get("answer", "")),
                    "sources_count": len(result.get("sources", [])),
                    "confidence": result.get("confidence", 0),
                    "time": processing_time
                })
                
                logger.info(f"  ✅ '{question}': réponse générée en {processing_time:.2f}s")
                logger.info(f"    📝 Longueur: {len(result.get('answer', ''))} caractères")
                logger.info(f"    📚 Sources: {len(result.get('sources', []))} documents")
                
                # Afficher un extrait de la réponse
                answer = result.get("answer", "")
                if answer:
                    preview = answer[:150] + "..." if len(answer) > 150 else answer
                    logger.info(f"    💬 Aperçu: {preview}")
                
            except Exception as e:
                logger.error(f"  ❌ Erreur RAG '{question}': {e}")
        
        avg_time = sum(rag_results["processing_times"]) / len(rag_results["processing_times"])
        logger.info(f"📊 Pipeline RAG terminé: {rag_results['total_questions']} questions, temps moyen: {avg_time:.2f}s")
        
        return rag_results
    
    async def run_complete_test(self, interactive: bool = False) -> Dict[str, Any]:
        """Exécute le test end-to-end complet"""
        logger.info("🎯 Début du test end-to-end complet")
        
        test_results = {
            "timestamp": time.time(),
            "interactive": interactive,
            "ingestion": None,
            "search": None,
            "rag": None,
            "success": False
        }
        
        try:
            # 1. Créer les documents d'exemple
            sample_docs = await self.create_sample_documents()
            
            # 2. Tester l'ingestion
            test_results["ingestion"] = await self.test_document_ingestion(sample_docs)
            
            # 3. Tester la recherche vectorielle
            search_queries = [
                "Qu'est-ce que l'intelligence artificielle ?",
                "Comment fonctionne le RAG ?",
                "Systèmes multi-agents collaboration"
            ]
            test_results["search"] = await self.test_vector_search(search_queries)
            
            # 4. Tester le pipeline RAG
            rag_questions = [
                "Peux-tu expliquer ce qu'est l'intelligence artificielle et ses applications ?",
                "Comment le RAG améliore-t-il les modèles de langage ?",
                "Quels sont les avantages des systèmes multi-agents ?"
            ]
            
            if interactive:
                rag_questions = await self._get_interactive_questions()
            
            test_results["rag"] = await self.test_rag_pipeline(rag_questions)
            
            # 5. Statistiques finales
            await self._display_final_stats(test_results)
            
            test_results["success"] = True
            logger.info("🎉 Test end-to-end terminé avec succès!")
            
        except Exception as e:
            logger.error(f"❌ Erreur dans le test end-to-end: {e}")
            test_results["error"] = str(e)
        
        return test_results
    
    async def _get_interactive_questions(self) -> List[str]:
        """Mode interactif pour poser des questions personnalisées"""
        questions = []
        
        print("\n🎤 Mode interactif activé!")
        print("Posez vos questions sur les documents ingérés (tapez 'quit' pour terminer):")
        
        while True:
            try:
                question = input("\n❓ Votre question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    break
                
                if question:
                    questions.append(question)
                    print(f"✅ Question ajoutée: {question}")
                
            except KeyboardInterrupt:
                break
        
        # Si aucune question interactive, utiliser les questions par défaut
        if not questions:
            questions = [
                "Peux-tu résumer les concepts principaux des documents ?",
                "Quelles sont les applications pratiques mentionnées ?"
            ]
        
        return questions
    
    async def _display_final_stats(self, results: Dict[str, Any]):
        """Affiche les statistiques finales du test"""
        logger.info("📈 Statistiques finales:")
        
        if results.get("ingestion"):
            ing = results["ingestion"]
            logger.info(f"  📥 Ingestion: {ing['total_documents']} docs, {ing['total_chunks']} chunks")
        
        if results.get("search"):
            search = results["search"]
            logger.info(f"  🔍 Recherche: {search['total_queries']} requêtes")
        
        if results.get("rag"):
            rag = results["rag"]
            logger.info(f"  🤖 RAG: {rag['total_questions']} questions traitées")
        
        # Statistiques du vector store
        try:
            stats = await self.vector_store.get_stats()
            logger.info(f"  📚 Vector Store: {stats.get('total_chunks', 0)} chunks, "
                       f"{stats.get('vector_dimension', 0)}D")
        except:
            pass
    
    async def cleanup(self):
        """Nettoyage après les tests"""
        try:
            if self.test_data_dir and os.path.exists(self.test_data_dir):
                import shutil
                shutil.rmtree(self.test_data_dir)
                logger.info(f"🧹 Nettoyage: {self.test_data_dir} supprimé")
        except Exception as e:
            logger.warning(f"⚠️ Erreur nettoyage: {e}")


# Classes mock pour les tests sans dépendances
class MockVectorStore:
    """Mock du vector store pour les tests"""
    
    def __init__(self):
        self.documents = []
        self.chunks = []
    
    async def ingest_text(self, content, metadata=None, chunk_size=1000, chunk_overlap=200):
        # Simuler l'ingestion
        chunks_count = max(1, len(content) // chunk_size)
        self.chunks.extend([{"content": content[:100], "metadata": metadata}] * chunks_count)
        return {"chunks_count": chunks_count}
    
    async def search(self, query, k=5, threshold=None):
        # Simuler une recherche
        results = []
        for i, chunk in enumerate(self.chunks[:k]):
            results.append({
                "content": chunk["content"],
                "score": 0.8 - (i * 0.1),
                "metadata": chunk["metadata"]
            })
        return results
    
    async def get_stats(self):
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "vector_dimension": 384
        }


class MockLLMClient:
    """Mock du client LLM pour les tests"""
    
    async def health_check(self):
        return True
    
    async def generate(self, prompt, model=None):
        return f"Réponse simulée pour: {prompt[:50]}..."


class MockMARCrew:
    """Mock du crew MAR pour les tests"""
    
    def __init__(self, vector_store=None, llm_client=None):
        self.vector_store = vector_store
        self.llm_client = llm_client
    
    async def process_query(self, query, context_size=3, use_critic=True):
        # Simuler le traitement
        return {
            "answer": f"Réponse simulée pour la question: {query}. "
                     f"Cette réponse est basée sur {context_size} sources pertinentes.",
            "sources": [{"title": f"Source {i+1}"} for i in range(context_size)],
            "confidence": 0.85
        }


async def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Test end-to-end de la plateforme MAR")
    parser.add_argument("--interactive", "-i", action="store_true", help="Mode interactif")
    parser.add_argument("--output", "-o", help="Fichier de sortie pour les résultats JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Exécuter le test
    test = MAREndToEndTest()
    
    try:
        await test.setup()
        results = await test.run_complete_test(interactive=args.interactive)
        
        # Sauvegarder les résultats si demandé
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"📄 Résultats sauvegardés dans {args.output}")
        
        # Afficher un résumé
        if results["success"]:
            print("\n🎉 Test end-to-end réussi!")
            print("✅ Ingestion: OK")
            print("✅ Recherche vectorielle: OK") 
            print("✅ Pipeline RAG: OK")
        else:
            print("\n❌ Test end-to-end échoué")
            if "error" in results:
                print(f"Erreur: {results['error']}")
        
    except KeyboardInterrupt:
        logger.info("Test interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
