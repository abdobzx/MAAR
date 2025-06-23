#!/usr/bin/env python3
"""
Service RAG simplifié avec Ollama
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from datetime import datetime
from typing import List, Optional
import requests

app = FastAPI(
    title="MAR RAG System with Ollama",
    description="Système RAG avec Ollama LLM",
    version="2.0.0"
)

class QueryRequest(BaseModel):
    question: str
    model: Optional[str] = "llama3.2:3b"

class QueryResponse(BaseModel):
    answer: str
    model_used: str
    processing_time: float
    status: str = "success"

def check_ollama_status() -> bool:
    """Vérifier si Ollama est disponible"""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        return response.status_code == 200
    except:
        return False

def generate_with_ollama(question: str, model: str = "llama3.2:3b") -> str:
    """Générer une réponse avec Ollama via API REST"""
    try:
        prompt = f"""Tu es un assistant expert en systèmes RAG (Retrieval-Augmented Generation).

Question: {question}

Réponds de manière précise et technique en français. Explique les concepts de façon claire et donne des exemples concrets quand c'est pertinent."""

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"Erreur Ollama: {response.status_code}"
            
    except Exception as e:
        return f"Erreur de connexion à Ollama: {str(e)}"

@app.get("/")
async def root():
    ollama_status = check_ollama_status()
    return {
        "message": "🚀 MAR RAG System with Ollama",
        "status": "running",
        "version": "2.0.0",
        "ollama_status": "connected" if ollama_status else "disconnected",
        "model": "llama3.2:3b",
        "endpoints": {
            "health": "/health",
            "query": "/api/v1/query",
            "test": "/api/v1/test",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    ollama_status = check_ollama_status()
    return {
        "status": "healthy",
        "service": "MAR RAG API with Ollama",
        "timestamp": datetime.now().isoformat(),
        "ollama_connected": ollama_status
    }

@app.get("/api/v1/test")
async def test_ollama():
    """Test simple d'Ollama"""
    if not check_ollama_status():
        raise HTTPException(status_code=503, detail="Ollama non disponible")
    
    answer = generate_with_ollama("Dis juste 'Hello from Ollama!'")
    return {"test": "success", "response": answer}

@app.post("/api/v1/query")
async def query(request: QueryRequest):
    """Endpoint principal pour les requêtes RAG"""
    start_time = datetime.now()
    
    try:
        # Vérifier Ollama
        if not check_ollama_status():
            raise HTTPException(status_code=503, detail="Ollama service non disponible")
        
        # Générer la réponse
        answer = generate_with_ollama(request.question, request.model)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            answer=answer,
            model_used=request.model,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

if __name__ == "__main__":
    print("🚀 Démarrage du système MAR RAG avec Ollama...")
    print("📡 API disponible sur: http://localhost:8001")
    print("📚 Documentation sur: http://localhost:8001/docs")
    print("🤖 Modèle: llama3.2:3b")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
