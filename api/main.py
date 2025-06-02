"""
API principale FastAPI pour le système RAG multi-agents.
Expose les endpoints pour l'interaction avec tous les agents.
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
import json
import uuid
from datetime import datetime

from core.config import get_settings
from core.logging import get_logger
from core.exceptions import ValidationError, ProcessingError
from core.models import (
    Document, DocumentChunk, SearchQuery, SearchResult,
    OrchestrationRequest, OrchestrationResponse, FeedbackEntry,
    HealthCheck, APIResponse, FileUploadResponse
)
from database.manager import DatabaseManager
from agents.ingestion.agent import IngestionAgent
from agents.vectorization.agent import VectorizationAgent
from agents.storage.agent import StorageAgent
from agents.retrieval.agent import RetrievalAgent
from agents.synthesis.agent import SynthesisAgent
from agents.orchestration.agent import OrchestrationAgent
from agents.feedback.agent import FeedbackMemoryAgent
from security.auth import AuthManager, get_current_user, check_permissions


# Gestionnaire de contexte pour l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire du cycle de vie de l'application."""
    
    logger = get_logger(__name__)
    
    # Initialisation
    logger.info("Démarrage de l'application RAG multi-agents")
    
    # Initialisation de la base de données
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialisation des agents
    app.state.ingestion_agent = IngestionAgent()
    app.state.vectorization_agent = VectorizationAgent()
    app.state.storage_agent = StorageAgent()
    app.state.retrieval_agent = RetrievalAgent()
    app.state.synthesis_agent = SynthesisAgent()
    app.state.orchestration_agent = OrchestrationAgent()
    app.state.feedback_agent = FeedbackMemoryAgent()
    
    # Initialisation de l'authentification
    app.state.auth_manager = AuthManager()
    
    logger.info("Application initialisée avec succès")
    
    yield
    
    # Nettoyage
    logger.info("Arrêt de l'application")
    await db_manager.close()


# Création de l'application FastAPI
settings = get_settings()
app = FastAPI(
    title="Système RAG Multi-Agents Entreprise",
    description="API pour le système de Retrieval-Augmented Generation avec architecture multi-agents",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan
)

# Configuration des middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configuration de la sécurité
security = HTTPBearer()
logger = get_logger(__name__)


# Routes de santé et monitoring
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Vérification de l'état de santé du système."""
    
    try:
        # Vérification de la base de données
        db_manager = DatabaseManager()
        db_healthy = await db_manager.health_check()
        
        # Vérification des agents (simulation)
        agents_status = {
            "ingestion": "healthy",
            "vectorization": "healthy", 
            "storage": "healthy",
            "retrieval": "healthy",
            "synthesis": "healthy",
            "orchestration": "healthy",
            "feedback": "healthy"
        }
        
        overall_status = "healthy" if db_healthy else "unhealthy"
        
        return HealthCheck(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            components={
                "database": "healthy" if db_healthy else "unhealthy",
                "agents": agents_status
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du health check: {str(e)}")
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            error=str(e)
        )


@app.get("/metrics")
async def get_metrics(
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["metrics:read"]))
):
    """Récupère les métriques du système."""
    
    try:
        # Métriques des agents
        orchestration_metrics = await app.state.orchestration_agent.get_workflow_metrics()
        feedback_metrics = await app.state.feedback_agent.get_memory_statistics()
        
        return {
            "timestamp": datetime.utcnow(),
            "orchestration": orchestration_metrics,
            "feedback_memory": feedback_metrics,
            "system": {
                "active_users": 1,  # À implémenter
                "total_documents": 0,  # À récupérer de la DB
                "total_queries": 0  # À récupérer de la DB
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Routes de gestion des documents
@app.post("/documents/upload", response_model=APIResponse[FileUploadResponse])
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    organization_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["documents:write"]))
):
    """Upload et traitement de documents."""
    
    try:
        user_id = current_user["sub"]
        org_id = organization_id or current_user.get("organization_id")
        
        if not org_id:
            raise ValidationError("ID d'organisation requis")
        
        upload_results = []
        
        for file in files:
            # Validation du fichier
            if file.size > settings.max_file_size:
                raise ValidationError(f"Fichier {file.filename} trop volumineux")
            
            # Lecture du contenu
            content = await file.read()
            
            # Création du document
            document = Document(
                title=file.filename,
                content="",  # Sera extrait par l'agent d'ingestion
                content_type=file.content_type,
                file_path=f"uploads/{uuid.uuid4()}_{file.filename}",
                user_id=user_id,
                organization_id=org_id,
                metadata={
                    "original_filename": file.filename,
                    "file_size": file.size,
                    "upload_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Traitement asynchrone
            background_tasks.add_task(
                process_document_async,
                document,
                content
            )
            
            upload_results.append(FileUploadResponse(
                document_id=document.id,
                filename=file.filename,
                status="uploaded",
                processing_status="queued"
            ))
        
        return APIResponse(
            success=True,
            data=upload_results,
            message=f"{len(files)} fichier(s) uploadé(s) avec succès"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


async def process_document_async(document: Document, content: bytes):
    """Traite un document de manière asynchrone."""
    
    try:
        # Ingestion
        extracted_content = await app.state.ingestion_agent.extract_content(
            content, document.content_type, document.metadata
        )
        document.content = extracted_content.text
        
        # Vectorisation
        chunks = await app.state.vectorization_agent.create_chunks(
            document, {"chunk_strategy": "adaptive"}
        )
        
        # Stockage
        await app.state.storage_agent.store_document(document)
        for chunk in chunks:
            await app.state.storage_agent.store_chunk(chunk)
        
        logger.info(f"Document {document.id} traité avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du document {document.id}: {str(e)}")


@app.get("/documents", response_model=APIResponse[List[Document]])
async def list_documents(
    organization_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["documents:read"]))
):
    """Liste les documents de l'organisation."""
    
    try:
        org_id = organization_id or current_user.get("organization_id")
        
        # Récupération depuis le storage agent
        documents = await app.state.storage_agent.list_documents(
            organization_id=org_id,
            limit=limit,
            offset=offset
        )
        
        return APIResponse(
            success=True,
            data=documents,
            message=f"{len(documents)} document(s) récupéré(s)"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}", response_model=APIResponse[bool])
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["documents:delete"]))
):
    """Supprime un document."""
    
    try:
        success = await app.state.storage_agent.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        
        return APIResponse(
            success=True,
            data=True,
            message="Document supprimé avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Routes de recherche et synthèse
@app.post("/search", response_model=APIResponse[SearchResult])
async def search_documents(
    query: SearchQuery,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["search:read"]))
):
    """Effectue une recherche dans les documents."""
    
    try:
        user_id = current_user["sub"]
        org_id = current_user.get("organization_id")
        
        # Mise à jour de la requête avec les informations utilisateur
        query.user_id = user_id
        query.organization_id = org_id
        
        # Recherche via l'agent de récupération
        results = await app.state.retrieval_agent.search(query)
        
        # Stockage en mémoire conversationnelle
        await app.state.feedback_agent.store_conversation_memory(
            user_id, org_id, query, results
        )
        
        return APIResponse(
            success=True,
            data=results,
            message=f"{len(results.chunks)} résultat(s) trouvé(s)"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=APIResponse[str])
async def answer_query(
    query: SearchQuery,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["query:read"]))
):
    """Répond à une question en utilisant la synthèse."""
    
    try:
        user_id = current_user["sub"]
        org_id = current_user.get("organization_id")
        
        query.user_id = user_id
        query.organization_id = org_id
        
        # Recherche
        search_results = await app.state.retrieval_agent.search(query)
        
        # Synthèse
        answer = await app.state.synthesis_agent.synthesize_response(
            query, search_results.chunks
        )
        
        # Stockage en mémoire
        await app.state.feedback_agent.store_conversation_memory(
            user_id, org_id, query, search_results
        )
        
        return APIResponse(
            success=True,
            data=answer.content,
            message="Réponse générée avec succès",
            metadata={
                "confidence_score": answer.confidence_score,
                "citations": answer.citations,
                "response_time": answer.processing_time
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de réponse: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/stream")
async def stream_answer_query(
    query: SearchQuery,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["query:read"]))
):
    """Répond à une question avec streaming."""
    
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            user_id = current_user["sub"]
            org_id = current_user.get("organization_id")
            
            query.user_id = user_id
            query.organization_id = org_id
            
            # Recherche
            search_results = await app.state.retrieval_agent.search(query)
            
            # Streaming de la synthèse
            async for chunk in app.state.synthesis_agent.synthesize_response_stream(
                query, search_results.chunks
            ):
                yield f"data: {json.dumps({'content': chunk, 'type': 'content'})}\n\n"
            
            # Signal de fin
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"Erreur lors du streaming: {str(e)}")
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# Routes d'orchestration
@app.post("/orchestrate", response_model=APIResponse[OrchestrationResponse])
async def orchestrate_workflow(
    request: OrchestrationRequest,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["orchestration:execute"]))
):
    """Lance un workflow d'orchestration."""
    
    try:
        user_id = current_user["sub"]
        org_id = current_user.get("organization_id")
        
        request.user_id = user_id
        request.organization_id = org_id
        
        response = await app.state.orchestration_agent.orchestrate_workflow(request)
        
        return APIResponse(
            success=True,
            data=response,
            message="Workflow exécuté avec succès"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'orchestration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestrate/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["orchestration:read"]))
):
    """Récupère le statut d'un workflow."""
    
    try:
        status = await app.state.orchestration_agent.get_workflow_status(workflow_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Workflow non trouvé")
        
        return APIResponse(
            success=True,
            data=status,
            message="Statut récupéré avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/orchestrate/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["orchestration:cancel"]))
):
    """Annule un workflow en cours."""
    
    try:
        success = await app.state.orchestration_agent.cancel_workflow(workflow_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workflow non trouvé")
        
        return APIResponse(
            success=True,
            data=True,
            message="Workflow annulé avec succès"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'annulation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Routes de feedback
@app.post("/feedback", response_model=APIResponse[Dict[str, Any]])
async def submit_feedback(
    feedback: FeedbackEntry,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["feedback:write"]))
):
    """Soumet un feedback utilisateur."""
    
    try:
        user_id = current_user["sub"]
        org_id = current_user.get("organization_id")
        
        feedback.user_id = user_id
        feedback.organization_id = org_id
        
        result = await app.state.feedback_agent.collect_feedback(feedback)
        
        return APIResponse(
            success=True,
            data=result,
            message="Feedback collecté avec succès"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la collecte de feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insights", response_model=APIResponse[List[Dict[str, Any]]])
async def get_learning_insights(
    timeframe_days: int = 7,
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(check_permissions(["insights:read"]))
):
    """Récupère les insights d'apprentissage."""
    
    try:
        org_id = current_user.get("organization_id")
        
        insights = await app.state.feedback_agent.get_learning_insights(
            org_id, timeframe_days
        )
        
        return APIResponse(
            success=True,
            data=[insight.dict() for insight in insights],
            message=f"{len(insights)} insight(s) récupéré(s)"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Gestionnaire d'erreurs global
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(ProcessingError)
async def processing_exception_handler(request, exc):
    return HTTPException(status_code=500, detail=str(exc))


# Point d'entrée principal
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_config=None  # Utilise notre configuration de logging
    )
