#!/usr/bin/env python3
"""
Démarrage rapide du système RAG MAR - Version simplifiée
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from datetime import datetime

# Pas de dotenv pour l'instant - version simple

app = FastAPI(
    title="MAR RAG System - Quick Start",
    description="Système RAG Multi-Agents - Version de démarrage rapide",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    status: str = "success"

@app.get("/")
async def root():
    return {
        "message": "🚀 MAR RAG System - Démarrage rapide",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "query": "/api/v1/query",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "MAR RAG API",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/query")
async def query(request: QueryRequest):
    """
    Endpoint de requête simple pour tester le système
    """
    try:
        # Simulation d'une réponse RAG
        response = f"Réponse simulée pour: '{request.question}'. Le système MAR RAG est opérationnel !"
        
        return QueryResponse(
            answer=response,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Démarrage du système MAR RAG...")
    print("📡 API sera disponible sur: http://localhost:8000")
    print("📚 Documentation sur: http://localhost:8000/docs")
    
    uvicorn.run(
        "quick_start:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
