"""
Router pour les interactions de chat et RAG.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from ..platform import get_platform
from ..auth.dependencies import get_current_user
from ..models.chat import (
    ChatRequest, ChatResponse, ChatSession, 
    RAGRequest, RAGResponse, WorkflowRequest
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Stockage temporaire des sessions (en production, utiliser Redis/DB)
active_sessions: Dict[str, ChatSession] = {}


@router.post("/simple", response_model=ChatResponse)
async def simple_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Chat simple avec RAG basique
    
    Exécute un workflow RAG simple pour répondre à une question.
    """
    try:
        logger.info(f"Chat simple demandé par {current_user.get('username', 'anonymous')}: {request.message}")
        
        if not platform.initialized:
            raise HTTPException(status_code=503, detail="Platform not initialized")
        
        if not platform.mar_crew:
            raise HTTPException(status_code=503, detail="MAR Crew not available")
        
        # Exécuter le workflow RAG simple
        start_time = datetime.now()
        
        workflow_result = platform.mar_crew.execute_simple_rag(
            query=request.message,
            max_documents=request.max_documents or 5,
            include_validation=request.include_validation
        )
        
        # Créer la réponse
        response = ChatResponse(
            response=workflow_result.get("final_answer", "Désolé, je n'ai pas pu générer une réponse."),
            sources=workflow_result.get("sources_used", []),
            confidence_level=workflow_result.get("confidence_level", "medium"),
            execution_time=workflow_result.get("execution_duration", 0),
            workflow_id=workflow_result.get("execution_id"),
            metadata={
                "workflow_type": "simple_rag",
                "total_sources": len(workflow_result.get("sources_used", [])),
                "validation_included": request.include_validation,
                "user_id": current_user.get("user_id")
            }
        )
        
        # Tâche en arrière-plan pour logging/analytics
        background_tasks.add_task(
            log_chat_interaction,
            request.message,
            response,
            current_user.get("user_id"),
            workflow_result
        )
        
        logger.info(f"Chat simple terminé: {response.execution_time:.2f}s, confiance: {response.confidence_level}")
        return response
        
    except Exception as e:
        logger.error(f"Erreur chat simple: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")


@router.post("/comparative", response_model=ChatResponse)
async def comparative_chat(
    request: RAGRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Chat avec analyse comparative
    
    Exécute un workflow RAG comparatif pour analyser différents points de vue.
    """
    try:
        logger.info(f"Chat comparatif demandé: {request.query}")
        
        if not platform.initialized or not platform.mar_crew:
            raise HTTPException(status_code=503, detail="Platform not ready")
        
        if not request.comparison_aspects:
            raise HTTPException(status_code=400, detail="Aspects de comparaison requis")
        
        # Exécuter le workflow comparatif
        workflow_result = platform.mar_crew.execute_comparative_rag(
            query=request.query,
            comparison_aspects=request.comparison_aspects,
            max_documents=request.max_documents or 8
        )
        
        # Créer la réponse
        response = ChatResponse(
            response=workflow_result.get("final_answer", "Analyse comparative non disponible."),
            sources=workflow_result.get("sources_used", []),
            confidence_level=workflow_result.get("comparison_quality", {}).get("validation_score", 0.5),
            execution_time=workflow_result.get("execution_duration", 0),
            workflow_id=workflow_result.get("execution_id"),
            metadata={
                "workflow_type": "comparative_rag",
                "comparison_aspects": request.comparison_aspects,
                "quality_metrics": workflow_result.get("comparison_quality", {}),
                "user_id": current_user.get("user_id")
            }
        )
        
        background_tasks.add_task(
            log_chat_interaction,
            request.query,
            response,
            current_user.get("user_id"),
            workflow_result
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur chat comparatif: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow", response_model=Dict[str, Any])
async def execute_custom_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Exécute un workflow personnalisé
    
    Permet d'exécuter des workflows spécifiques avec configuration avancée.
    """
    try:
        logger.info(f"Workflow personnalisé: {request.workflow_type}")
        
        if not platform.initialized or not platform.mar_crew:
            raise HTTPException(status_code=503, detail="Platform not ready")
        
        result = {}
        
        if request.workflow_type == "summarization":
            if not request.documents:
                raise HTTPException(status_code=400, detail="Documents requis pour résumé")
            
            result = platform.mar_crew.execute_summarization_workflow(
                documents=request.documents,
                summary_type=request.parameters.get("summary_type", "abstractive"),
                max_length=request.parameters.get("max_length", 200)
            )
            
        elif request.workflow_type == "simple_rag":
            if not request.query:
                raise HTTPException(status_code=400, detail="Query requise pour RAG")
            
            result = platform.mar_crew.execute_simple_rag(
                query=request.query,
                max_documents=request.parameters.get("max_documents", 5),
                include_validation=request.parameters.get("include_validation", True)
            )
            
        elif request.workflow_type == "comparative_rag":
            if not request.query or not request.parameters.get("comparison_aspects"):
                raise HTTPException(status_code=400, detail="Query et aspects de comparaison requis")
            
            result = platform.mar_crew.execute_comparative_rag(
                query=request.query,
                comparison_aspects=request.parameters["comparison_aspects"],
                max_documents=request.parameters.get("max_documents", 8)
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Workflow type non supporté: {request.workflow_type}")
        
        # Ajouter métadonnées utilisateur
        result["user_metadata"] = {
            "user_id": current_user.get("user_id"),
            "request_timestamp": datetime.now().isoformat(),
            "workflow_type": request.workflow_type
        }
        
        background_tasks.add_task(
            log_workflow_execution,
            request.workflow_type,
            result,
            current_user.get("user_id")
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur workflow personnalisé: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/create")
async def create_chat_session(
    session_name: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Crée une nouvelle session de chat
    """
    try:
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            session_id=session_id,
            user_id=current_user.get("user_id"),
            session_name=session_name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_at=datetime.now(),
            messages=[],
            metadata={}
        )
        
        active_sessions[session_id] = session
        
        logger.info(f"Session créée: {session_id} pour {current_user.get('username')}")
        
        return {
            "session_id": session_id,
            "session_name": session.session_name,
            "created_at": session.created_at.isoformat(),
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Erreur création session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Récupère une session de chat
    """
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        session = active_sessions[session_id]
        
        # Vérifier que l'utilisateur a accès à cette session
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette session")
        
        return {
            "session_id": session.session_id,
            "session_name": session.session_name,
            "created_at": session.created_at.isoformat(),
            "message_count": len(session.messages),
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "messages": [msg.dict() for msg in session.messages[-20:]]  # 20 derniers messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_user_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Liste les sessions de l'utilisateur
    """
    try:
        user_sessions = [
            {
                "session_id": session.session_id,
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat(),
                "message_count": len(session.messages),
                "last_activity": session.last_activity.isoformat() if session.last_activity else None
            }
            for session in active_sessions.values()
            if session.user_id == current_user.get("user_id")
        ]
        
        # Trier par dernière activité
        user_sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        
        return user_sessions
        
    except Exception as e:
        logger.error(f"Erreur liste sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Supprime une session de chat
    """
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        session = active_sessions[session_id]
        
        if session.user_id != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Accès non autorisé")
        
        del active_sessions[session_id]
        
        logger.info(f"Session supprimée: {session_id}")
        
        return {"message": "Session supprimée avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Fonctions utilitaires pour les tâches en arrière-plan

async def log_chat_interaction(
    message: str,
    response: ChatResponse,
    user_id: str,
    workflow_result: Dict[str, Any]
):
    """Log une interaction de chat pour analytics"""
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "message": message,
            "response_length": len(response.response),
            "execution_time": response.execution_time,
            "confidence_level": response.confidence_level,
            "sources_count": len(response.sources),
            "workflow_id": response.workflow_id,
            "workflow_status": workflow_result.get("status")
        }
        
        # En production, envoyer vers un système de logging/analytics
        logger.info(f"Chat interaction logged: {log_data}")
        
    except Exception as e:
        logger.warning(f"Erreur logging interaction: {e}")


async def log_workflow_execution(
    workflow_type: str,
    result: Dict[str, Any],
    user_id: str
):
    """Log l'exécution d'un workflow"""
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "workflow_type": workflow_type,
            "execution_id": result.get("execution_id"),
            "status": result.get("status"),
            "execution_duration": result.get("execution_duration"),
            "steps_completed": len(result.get("steps", {}))
        }
        
        logger.info(f"Workflow execution logged: {log_data}")
        
    except Exception as e:
        logger.warning(f"Erreur logging workflow: {e}")
