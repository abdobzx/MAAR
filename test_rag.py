#!/usr/bin/env python3
"""
Test interactif du système RAG
"""
import requests
import json
import time

def test_simple():
    print("🧪 Test simple...")
    response = requests.post(
        "http://localhost:8001/api/v1/query",
        json={"question": "Dis juste 'Bonjour' en français"},
        timeout=30
    )
    print(f"✅ Réponse: {response.json()['answer']}")
    print(f"⏱️  Temps: {response.json()['processing_time']:.2f}s\n")

def test_rag():
    print("🔍 Test RAG technique...")
    response = requests.post(
        "http://localhost:8001/api/v1/query",
        json={"question": "Qu'est-ce qu'un système RAG? (bref)"},
        timeout=45
    )
    result = response.json()
    print(f"✅ Réponse: {result['answer'][:200]}...")
    print(f"⏱️  Temps: {result['processing_time']:.2f}s\n")

def test_interactif():
    print("💬 Test interactif - Tapez votre question (ou 'quit' pour quitter):")
    while True:
        question = input("\n❓ Question: ")
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        try:
            start = time.time()
            response = requests.post(
                "http://localhost:8001/api/v1/query",
                json={"question": question},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n🤖 Réponse:")
                print(f"{result['answer']}")
                print(f"\n⏱️  Temps de traitement: {result['processing_time']:.2f}s")
            else:
                print(f"❌ Erreur: {response.status_code}")
        except requests.exceptions.Timeout:
            print("⏰ Timeout - Question trop complexe, essayez quelque chose de plus simple")
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    print("🚀 Tests du système MAR RAG avec Ollama")
    print("=" * 50)
    
    # Vérification du service
    try:
        health = requests.get("http://localhost:8001/health", timeout=5)
        if health.status_code == 200:
            print("✅ Service RAG actif")
            status = health.json()
            print(f"✅ Ollama: {'connecté' if status['ollama_connected'] else 'déconnecté'}")
        else:
            print("❌ Service RAG non disponible")
            exit(1)
    except:
        print("❌ Impossible de joindre le service RAG sur http://localhost:8001")
        exit(1)
    
    print("\n" + "=" * 50)
    
    # Tests automatiques
    try:
        test_simple()
        test_rag()
    except Exception as e:
        print(f"❌ Erreur dans les tests automatiques: {e}")
    
    # Test interactif
    test_interactif()
    
    print("\n👋 Au revoir !")
