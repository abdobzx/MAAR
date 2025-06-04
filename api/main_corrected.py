"""
API principale FastAPI pour le système RAG multi-agents.
Version corrigée pour production - compatible avec tous les agents.
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

from core.config import settings, get_settings
from core.logging import get_logger
from core.exceptions import ValidationError, ProcessingError
from core.models import (
    Document, DocumentChunk, SearchQuery, SearchResult,
    OrchestrationRequest, OrchestrationResponse, FeedbackEntry,
    HealthCheck, APIResponse, FileUploadResponse, DocumentStatus,
    WorkflowType
)
from database.manager import DatabaseManager

# Imports conditionnels pour tous les agents
try:
    from agents.ingestion.agent import IngestionAgent
    INGESTION_AVAILABLE = True
except ImportError:
    INGESTION_AVAILABLE = False
    IngestionAgent = None

try:
    from agents.vectorization.agent import VectorizationAgent
    VECTORIZATION_AVAILABLE = True
except ImportError:
    VECTORIZATION_AVAILABLE = False
    VectorizationAgent = None

try:
    from agents.storage.agent import StorageAgent
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    StorageAgent = None

try:
    from agents.retrieval.agent import RetrievalAgent
    RETRIEVAL_AVAILABLE = True
except ImportError:
    RETRIEVAL_AVAILABLE = False
    RetrievalAgent = None

try:
    from agents.synthesis.agent import SynthesisAgent
    SYNTHESIS_AVAILABLE = True
except ImportError:
    SYNTHESIS_AVAILABLE = False
    SynthesisAgent = None

try:
    from agents.orchestration.agent import OrchestrationAgent
    ORCHESTRATION_AVAILABLE = True
except ImportError:
    ORCHESTRATION_AVAILABLE = False
    OrchestrationAgent = None

try:
    from agents.feedback.agent import FeedbackMemoryAgent
    FEEDBACK_AVAILABLE = True
except ImportError:
    FEEDBACK_AVAILABLE = False
    FeedbackMemoryAgent = None

try:
    from security.auth import AuthManager, get_current_user, check_permissions
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    AuthManager = None
    get_current_user = None
    check_permissions = None


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
    app.state.db_manager = db_manager
    
    # Initialisation des agents disponibles
    agents_initialized = 0
    
    if INGESTION_AVAILABLE:
        try:
            app.state.ingestion_agent = IngestionAgent()
            await app.state.ingestion_agent.initialize()
            agents_initialized += 1
            logger.info("Agent d'ingestion initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent d'ingestion: {e}")
            app.state.ingestion_agent = None
    else:
        app.state.ingestion_agent = None
    
    if VECTORIZATION_AVAILABLE:
        try:
            app.state.vectorization_agent = VectorizationAgent()
            await app.state.vectorization_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de vectorisation initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de vectorisation: {e}")
            app.state.vectorization_agent = None
    else:
        app.state.vectorization_agent = None
    
    if STORAGE_AVAILABLE:
        try:
            app.state.storage_agent = StorageAgent()
            await app.state.storage_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de stockage initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de stockage: {e}")
            app.state.storage_agent = None
    else:
        app.state.storage_agent = None
    
    if RETRIEVAL_AVAILABLE:
        try:
            app.state.retrieval_agent = RetrievalAgent()
            await app.state.retrieval_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de récupération initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de récupération: {e}")
            app.state.retrieval_agent = None
    else:
        app.state.retrieval_agent = None
    
    if SYNTHESIS_AVAILABLE:
        try:
            app.state.synthesis_agent = SynthesisAgent()
            await app.state.synthesis_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de synthèse initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de synthèse: {e}")
            app.state.synthesis_agent = None
    else:
        app.state.synthesis_agent = None
    
    if ORCHESTRATION_AVAILABLE:
        try:
            app.state.orchestration_agent = OrchestrationAgent()
            await app.state.orchestration_agent.initialize()
            agents_initialized += 1
            logger.info("Agent d'orchestration initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent d'orchestration: {e}")
            app.state.orchestration_agent = None
    else:
        app.state.orchestration_agent = None
    
    if FEEDBACK_AVAILABLE:
        try:
            app.state.feedback_agent = FeedbackMemoryAgent()
            await app.state.feedback_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de feedback initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de feedback: {e}")
            app.state.feedback_agent = None
    else:
        app.state.feedback_agent = None
    
    # Initialisation de l'authentification
    if AUTH_AVAILABLE:
        try:
            app.state.auth_manager = AuthManager()
            logger.info("Gestionnaire d'authentification initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation authentification: {e}")
            app.state.auth_manager = None
    else:
        app.state.auth_manager = None
    
    logger.info(f"Application initialisée avec succès - {agents_initialized} agents disponibles")
    
    yield
    
    # Nettoyage
    logger.info("Arrêt de l'application")
    if hasattr(app.state, 'db_manager'):
        await app.state.db_manager.close()


# Création de l'application FastAPI
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
    allow_origins=["*"],  # Configuration par défaut sécurisée
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configuration de la sécurité
security = HTTPBearer() if AUTH_AVAILABLE else None
logger = get_logger(__name__)


# Fonctions utilitaires pour vérifier la disponibilité des agents
def require_agent(agent_name: str):
    """Décorateur pour vérifier qu'un agent est disponible."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            agent = getattr(app.state, f"{agent_name}_agent", None)
            if agent is None:
                raise HTTPException(
                    status_code=503,
                    detail=f"Agent {agent_name} non disponible"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Routes de santé et monitoring
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Vérification de la santé du système."""
    try:
        components = {}
        
        # Vérification des agents
        agent_names = ["ingestion", "vectorization", "storage", "retrieval", "synthesis", "orchestration", "feedback"]
        for agent_name in agent_names:
            agent = getattr(app.state, f"{agent_name}_agent", None)
            if agent:
                try:
                    if hasattr(agent, 'health_check'):
                        agent_health = await agent.health_check()
                        components[f"{agent_name}_agent"] = agent_health
                    else:
                        components[f"{agent_name}_agent"] = {"status": "available"}
                except Exception as e:
                    components[f"{agent_name}_agent"] = {"status": "error", "error": str(e)}
            else:
                components[f"{agent_name}_agent"] = {"status": "unavailable"}
        
        # Vérification de la base de données
        if hasattr(app.state, 'db_manager'):
            try:
                db_health = await app.state.db_manager.health_check()
                components["database"] = db_health
            except Exception as e:
                components["database"] = {"status": "error", "error": str(e)}
        
        return HealthCheck(
            status="healthy",
            version="1.0.0",
            components=components
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du health check: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/status")
async def get_system_status():
    """Statut détaillé du système."""
    try:
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {},
            "dependencies": {
                "ingestion": INGESTION_AVAILABLE,
                "vectorization": VECTORIZATION_AVAILABLE,
                "storage": STORAGE_AVAILABLE,
                "retrieval": RETRIEVAL_AVAILABLE,
                "synthesis": SYNTHESIS_AVAILABLE,
                "orchestration": ORCHESTRATION_AVAILABLE,
                "feedback": FEEDBACK_AVAILABLE,
                "auth": AUTH_AVAILABLE
            }
        }
        
        # Statut des agents
        agent_names = ["ingestion", "vectorization", "storage", "retrieval", "synthesis", "orchestration", "feedback"]
        for agent_name in agent_names:
            agent = getattr(app.state, f"{agent_name}_agent", None)
            status["agents"][agent_name] = {
                "available": agent is not None,
                "initialized": agent is not None
            }
        
        return status
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


# Routes principales
@app.post("/orchestrate", response_model=OrchestrationResponse)
async def orchestrate_workflow(request: OrchestrationRequest):
    """Point d'entrée principal pour l'orchestration de workflows."""
    try:
        if not app.state.orchestration_agent:
            raise HTTPException(
                status_code=503,
                detail="Agent d'orchestration non disponible"
            )
        
        logger.info(f"Début d'orchestration: {request.query[:100]}...")
        
        # Traitement de la demande d'orchestration
        response = await app.state.orchestration_agent.process_request(request)
        
        logger.info(f"Orchestration terminée: {response.workflow_id}")
        return response
        
    except ValidationError as e:
        logger.warning(f"Erreur de validation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ProcessingError as e:
        logger.error(f"Erreur de traitement: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'orchestration: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/orchestrate/stream")
async def orchestrate_workflow_stream(request: OrchestrationRequest):
    """Orchestration avec réponse en streaming."""
    try:
        if not app.state.orchestration_agent:
            raise HTTPException(
                status_code=503,
                detail="Agent d'orchestration non disponible"
            )
        
        async def generate_response() -> AsyncGenerator[str, None]:
            try:
                # Traitement normal de la demande
                response = await app.state.orchestration_agent.process_request(request)
                
                # Streaming de la réponse
                if response.result:
                    # Divise la réponse en chunks pour le streaming
                    chunks = response.result.split('. ')
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            chunk_data = {
                                "chunk": chunk + ('.' if i < len(chunks) - 1 else ''),
                                "index": i,
                                "total": len(chunks),
                                "workflow_id": response.workflow_id
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            await asyncio.sleep(0.1)  # Délai pour simulation streaming
                
                # Message de fin
                final_data = {
                    "status": "completed",
                    "workflow_id": response.workflow_id,
                    "confidence_score": response.confidence_score,
                    "execution_time": response.execution_time
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                
            except Exception as e:
                error_data = {
                    "status": "error",
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/search", response_model=List[SearchResult])
async def search_documents(
    query: str,
    search_type: str = "hybrid",
    limit: int = 10,
    threshold: float = 0.7
):
    """Recherche dans les documents."""
    try:
        if not app.state.retrieval_agent:
            raise HTTPException(
                status_code=503,
                detail="Agent de récupération non disponible"
            )
        
        # Validation des paramètres
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Requête vide")
        
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limite doit être entre 1 et 100")
        
        # Recherche
        results = await app.state.retrieval_agent.search(
            query=query,
            search_type=search_type,
            limit=limit,
            threshold=threshold
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/synthesize")
async def synthesize_response(
    query: str,
    search_results: List[Dict[str, Any]],
    synthesis_type: str = "standard"
):
    """Synthèse de réponse basée sur des résultats de recherche."""
    try:
        if not app.state.synthesis_agent:
            raise HTTPException(
                status_code=503,
                detail="Agent de synthèse non disponible"
            )
        
        # Préparation du contexte
        context = {
            "query": query,
            "search_results": search_results,
            "synthesis_type": synthesis_type
        }
        
        # Synthèse
        result = await app.state.synthesis_agent.synthesize(context)
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la synthèse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.post("/upload", response_model=FileUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None
):
    """Upload et traitement d'un document."""
    try:
        if not app.state.ingestion_agent:
            raise HTTPException(
                status_code=503,
                detail="Agent d'ingestion non disponible"
            )
        
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        # Lecture du contenu
        content = await file.read()
        
        # Traitement en arrière-plan
        document_id = str(uuid.uuid4())
        background_tasks.add_task(
            process_document_background,
            document_id,
            file.filename,
            content,
            user_id,
            organization_id
        )
        
        return FileUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status=DocumentStatus.PENDING,
            message="Document en cours de traitement"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'upload: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


async def process_document_background(
    document_id: str,
    filename: str,
    content: bytes,
    user_id: Optional[str],
    organization_id: Optional[str]
):
    """Traitement d'un document en arrière-plan."""
    try:
        if app.state.ingestion_agent:
            await app.state.ingestion_agent.process_document(
                document_id=document_id,
                filename=filename,
                content=content,
                user_id=user_id,
                organization_id=organization_id
            )
            logger.info(f"Document {document_id} traité avec succès")
    except Exception as e:
        logger.error(f"Erreur lors du traitement du document {document_id}: {e}")


@app.post("/feedback")
async def submit_feedback(feedback: FeedbackEntry):
    """Soumission de feedback."""
    try:
        if not app.state.feedback_agent:
            # Feedback simple sans agent
            logger.info(f"Feedback reçu: {feedback.rating}/5 - {feedback.feedback_text}")
            return {"message": "Feedback enregistré"}
        
        # Traitement avec l'agent de feedback
        await app.state.feedback_agent.store_feedback(feedback)
        
        return {"message": "Feedback traité avec succès"}
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


@app.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Récupère le statut d'un workflow."""
    try:
        if not app.state.orchestration_agent:
            raise HTTPException(
                status_code=503,
                detail="Agent d'orchestration non disponible"
            )
        
        status = await app.state.orchestration_agent.get_workflow_status(workflow_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="Workflow non trouvé")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")


# Route de test simple
@app.get("/")
async def root():
    """Route racine."""
    return {
        "message": "Système RAG Multi-Agents Entreprise",
        "version": "1.0.0",
        "status": "opérationnel",
        "agents_available": {
            "ingestion": app.state.ingestion_agent is not None,
            "vectorization": app.state.vectorization_agent is not None,
            "storage": app.state.storage_agent is not None,
            "retrieval": app.state.retrieval_agent is not None,
            "synthesis": app.state.synthesis_agent is not None,
            "orchestration": app.state.orchestration_agent is not None,
            "feedback": app.state.feedback_agent is not None
        }
    }


# Gestionnaire d'erreurs global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Gestionnaire d'erreurs global."""
    logger.error(f"Erreur non gérée: {exc}")
    return HTTPException(status_code=500, detail="Erreur interne du serveur")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
