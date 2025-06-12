#!/usr/bin/env python3
"""
Service RAG OPTIMISÉ avec gestion des timeouts et modèles rapides
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from datetime import datetime
from typing import List, Optional
import asyncio
import concurrent.futures

app = FastAPI(
    title="MAR RAG System - Optimized",
    description="Système RAG optimisé avec modèles rapides",
    version="2.1.0"
)

class QueryRequest(BaseModel):
    question: str
    model: Optional[str] = "gemma3:1b"  # Modèle le plus rapide
    timeout: Optional[int] = 30

class QueryResponse(BaseModel):
    answer: str
    model_used: str
    processing_time: float
    status: str = "success"
    fallback_used: Optional[bool] = False

# Modèles disponibles par ordre de vitesse
MODELS = {
    "gemma3:1b": {"timeout": 15, "description": "Ultra-rapide (1B params)"},
    "llama3.2:3b": {"timeout": 30, "description": "Rapide (3B params)"},
    "llama3:latest": {"timeout": 60, "description": "Performant (8B params)"}
}

def check_ollama_status() -> bool:
    """Vérifier si Ollama est disponible"""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=3)
        return response.status_code == 200
    except:
        return False

def generate_with_ollama(question: str, model: str = "gemma3:1b", timeout: int = 15) -> tuple:
    """Générer une réponse avec gestion des timeouts et fallback"""
    
    # Prompts optimisés par longueur de question
    if len(question) < 50:
        prompt = f"Question: {question}\nRéponds de façon concise en français:"
    else:
        prompt = f"Réponds brièvement en français:\n{question}"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Plus déterministe
            "top_p": 0.9,
            "num_predict": 150 if len(question) < 50 else 300  # Limite la longueur
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()["response"], False
        else:
            return f"Erreur API: {response.status_code}", True
            
    except requests.exceptions.Timeout:
        return f"⏰ Timeout après {timeout}s - Question trop complexe pour le modèle {model}", True
    except Exception as e:
        return f"Erreur: {str(e)}", True

def generate_with_fallback(question: str, preferred_model: str, timeout: int) -> tuple:
    """Génération avec fallback automatique"""
    
    # Essai avec le modèle demandé
    answer, had_error = generate_with_ollama(question, preferred_model, timeout)
    
    if not had_error:
        return answer, preferred_model, False
    
    # Fallback vers gemma3:1b si pas déjà utilisé
    if preferred_model != "gemma3:1b":
        print(f"🔄 Fallback vers gemma3:1b...")
        answer, had_error = generate_with_ollama(question, "gemma3:1b", 15)
        if not had_error:
            return answer, "gemma3:1b", True
    
    # Réponse d'urgence
    emergency_response = f"""⚠️ Réponse d'urgence (Ollama surchargé):

Question: {question}

Cette question nécessite un traitement plus complexe que le modèle disponible ne peut gérer rapidement. 

Suggestions:
- Reformulez votre question de façon plus simple
- Divisez votre question en plusieurs parties
- Réessayez dans quelques instants

Le système RAG fonctionne mais nécessite des questions plus directes pour des réponses rapides."""
    
    return emergency_response, preferred_model, True

@app.get("/")
async def root():
    ollama_status = check_ollama_status()
    return {
        "message": "🚀 MAR RAG System - Optimized",
        "status": "running",
        "version": "2.1.0",
        "ollama_status": "connected" if ollama_status else "disconnected",
        "available_models": list(MODELS.keys()),
        "recommended_model": "gemma3:1b",
        "endpoints": {
            "health": "/health",
            "query": "/api/v1/query",
            "models": "/api/v1/models",
            "test": "/api/v1/test-fast",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    ollama_status = check_ollama_status()
    return {
        "status": "healthy",
        "service": "MAR RAG API - Optimized",
        "timestamp": datetime.now().isoformat(),
        "ollama_connected": ollama_status,
        "models_available": list(MODELS.keys())
    }

@app.get("/api/v1/models")
async def list_models():
    """Lister les modèles avec leurs performances"""
    return {
        "models": MODELS,
        "recommended": "gemma3:1b",
        "status": "success"
    }

@app.get("/api/v1/test-fast")
async def test_fast():
    """Test ultra-rapide avec gemma3:1b"""
    if not check_ollama_status():
        raise HTTPException(status_code=503, detail="Ollama non disponible")
    
    answer, had_error = generate_with_ollama("Dis juste 'Hello RAG!'", "gemma3:1b", 10)
    return {
        "test": "fast",
        "model": "gemma3:1b",
        "response": answer,
        "had_error": had_error
    }

@app.post("/api/v1/query")
async def query(request: QueryRequest):
    """Endpoint optimisé avec fallback automatique"""
    start_time = datetime.now()
    
    try:
        # Vérifier Ollama
        if not check_ollama_status():
            raise HTTPException(status_code=503, detail="Ollama service non disponible")
        
        # Génération avec fallback
        answer, model_used, fallback_used = generate_with_fallback(
            request.question, 
            request.model, 
            request.timeout
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            answer=answer,
            model_used=model_used,
            processing_time=processing_time,
            fallback_used=fallback_used
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

if __name__ == "__main__":
    print("🚀 Démarrage du système MAR RAG OPTIMISÉ...")
    print("📡 API disponible sur: http://localhost:8002")
    print("📚 Documentation sur: http://localhost:8002/docs")
    print("⚡ Modèle par défaut: gemma3:1b (ultra-rapide)")
    print("🔄 Fallback automatique en cas de timeout")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
