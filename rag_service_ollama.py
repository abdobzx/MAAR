#!/usr/bin/env python3
"""
Service RAG avec Ollama - Version fonctionnelle
"""
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import httpx
from datetime import datetime
from typing import List, Optional
import asyncio

app = FastAPI(
    title="MAR RAG System with Ollama",
    description="Système RAG Multi-Agents avec Ollama LLM",
    version="2.0.0"
)

class QueryRequest(BaseModel):
    question: str
    model: Optional[str] = "llama3.2:3b"
    use_context: Optional[bool] = True

class QueryResponse(BaseModel):
    answer: str
    model_used: str
    processing_time: float
    status: str = "success"
    context_used: Optional[List[str]] = None

class RAGService:
    def __init__(self):
        self.client = ollama.Client()
        self.knowledge_base = [
            "Le système MAR (Multi-Agent RAG) utilise plusieurs agents spécialisés pour traiter les requêtes.",
            "Les agents incluent : Agent de Recherche, Agent d'Analyse, Agent de Synthèse, et Agent de Validation.",
            "Le système utilise Qdrant pour la recherche vectorielle et PostgreSQL pour le stockage des données.",
            "FastAPI est utilisé comme framework web principal avec uvicorn comme serveur ASGI.",
            "L'architecture microservices permet une scalabilité horizontale et une maintenance facilitée.",
            "Les embeddings sont générés via des modèles Sentence Transformers pour la recherche sémantique.",
            "Redis est utilisé pour le cache et la gestion des sessions utilisateur.",
            "Le monitoring se fait via Prometheus et Grafana pour les métriques en temps réel."
        ]
    
    async def check_ollama_status(self) -> bool:
        """Vérifier si Ollama est disponible"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:11434/api/version")
                return response.status_code == 200
        except:
            return False
    
    def find_relevant_context(self, question: str) -> List[str]:
        """Simuler la recherche de contexte pertinent"""
        question_lower = question.lower()
        relevant = []
        
        keywords = {
            "agent": ["agent", "multi-agent", "architecture"],
            "rag": ["rag", "recherche", "retrieval"],
            "database": ["base", "données", "postgresql", "qdrant"],
            "api": ["api", "fastapi", "endpoint"],
            "monitoring": ["monitoring", "métriques", "prometheus"],
            "cache": ["cache", "redis", "session"]
        }
        
        for category, terms in keywords.items():
            if any(term in question_lower for term in terms):
                relevant.extend([kb for kb in self.knowledge_base if any(term in kb.lower() for term in terms)])
        
        return list(set(relevant))[:3]  # Max 3 contextes pertinents
    
    async def generate_answer(self, question: str, context: List[str], model: str) -> str:
        """Générer une réponse avec Ollama"""
        context_text = "\n".join(context) if context else ""
        
        prompt = f"""Tu es un assistant expert en systèmes RAG et architecture multi-agents.

Contexte disponible:
{context_text}

Question: {question}

Réponds de manière précise et technique en français. Si le contexte ne contient pas d'information pertinente, réponds quand même avec tes connaissances générales sur les systèmes RAG."""

        try:
            response = await asyncio.to_thread(
                self.client.generate,
                model=model,
                prompt=prompt,
                stream=False
            )
            return response['response']
        except Exception as e:
            return f"Erreur lors de la génération: {str(e)}"

rag_service = RAGService()

@app.get("/")
async def root():
    ollama_status = await rag_service.check_ollama_status()
    return {
        "message": "🚀 MAR RAG System with Ollama",
        "status": "running",
        "version": "2.0.0",
        "ollama_status": "connected" if ollama_status else "disconnected",
        "available_models": ["llama3.2:3b"],
        "endpoints": {
            "health": "/health",
            "query": "/api/v1/query",
            "models": "/api/v1/models",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    ollama_status = await rag_service.check_ollama_status()
    return {
        "status": "healthy",
        "service": "MAR RAG API with Ollama",
        "timestamp": datetime.now().isoformat(),
        "ollama_connected": ollama_status
    }

@app.get("/api/v1/models")
async def list_models():
    """Lister les modèles disponibles"""
    try:
        models = await asyncio.to_thread(rag_service.client.list)
        return {
            "models": [model['name'] for model in models['models']],
            "status": "success"
        }
    except Exception as e:
        return {
            "models": [],
            "status": "error",
            "error": str(e)
        }

@app.post("/api/v1/query")
async def query(request: QueryRequest):
    """
    Endpoint principal pour les requêtes RAG avec Ollama
    """
    start_time = datetime.now()
    
    try:
        # Vérifier la connexion Ollama
        if not await rag_service.check_ollama_status():
            raise HTTPException(status_code=503, detail="Ollama service non disponible")
        
        # Rechercher le contexte pertinent
        context = []
        if request.use_context:
            context = rag_service.find_relevant_context(request.question)
        
        # Générer la réponse
        answer = await rag_service.generate_answer(
            request.question, 
            context, 
            request.model
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            answer=answer,
            model_used=request.model,
            processing_time=processing_time,
            context_used=context if request.use_context else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

if __name__ == "__main__":
    print("🚀 Démarrage du système MAR RAG avec Ollama...")
    print("📡 API sera disponible sur: http://localhost:8001")
    print("📚 Documentation sur: http://localhost:8001/docs")
    print("🤖 Modèle par défaut: llama3.2:3b")
    
    uvicorn.run(
        "rag_service_ollama:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
