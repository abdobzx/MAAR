#!/usr/bin/env python3
"""
RAG Ultra-Simple et Rapide
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from datetime import datetime

app = FastAPI(title="RAG Ultra-Rapide", version="3.0.0")

class Query(BaseModel):
    question: str

class Response(BaseModel):
    answer: str
    time: float
    model: str

def ask_ollama_fast(question: str) -> str:
    """Version ultra-simplifiée pour gemma3:1b"""
    try:
        # Prompt minimal pour réponse rapide
        payload = {
            "model": "gemma3:1b",
            "prompt": f"Q: {question}\nA (en français, bref):",
            "stream": False,
            "options": {"num_predict": 100, "temperature": 0.3}
        }
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=20  # 20 secondes max
        )
        
        if response.status_code == 200:
            return response.json()["response"].strip()
        return f"Erreur API: {response.status_code}"
        
    except requests.exceptions.Timeout:
        return "⏰ Réponse trop lente. Essayez une question plus simple."
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

@app.get("/")
def root():
    return {
        "service": "🚀 RAG Ultra-Rapide",
        "model": "gemma3:1b",
        "status": "ready",
        "endpoint": "/ask"
    }

@app.post("/ask")
def ask(query: Query):
    start = datetime.now()
    
    # Vérification Ollama
    try:
        requests.get("http://localhost:11434/api/version", timeout=2)
    except:
        raise HTTPException(status_code=503, detail="Ollama non disponible")
    
    # Génération
    answer = ask_ollama_fast(query.question)
    duration = (datetime.now() - start).total_seconds()
    
    return Response(
        answer=answer,
        time=duration,
        model="gemma3:1b"
    )

if __name__ == "__main__":
    print("🚀 RAG Ultra-Rapide sur http://localhost:8003")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="warning")
