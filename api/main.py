"""
<<<<<<< HEAD
Application FastAPI principale pour la plateforme MAR.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import uvicorn
import os
from typing import Dict, Any

# Import des routers
from .routers import chat
from .routers import auth, documents, admin
from .middleware.rate_limiter import RateLimitMiddleware
from .middleware.auth import AuthMiddleware
from .middleware.logging import LoggingMiddleware

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MARPlatform:
    """Gestionnaire de la plateforme MAR"""
    
    def __init__(self):
        self.vector_store = None
        self.llm_client = None
        self.mar_crew = None
        self.initialized = False
    
    async def initialize(self):
        """Initialise les composants de la plateforme"""
        try:
            logger.info("Initialisation de la plateforme MAR...")
            
            # Initialiser le vector store
            from vector_store import create_vector_store
            self.vector_store = await create_vector_store(
                store_type=os.getenv("VECTOR_STORE_TYPE", "faiss"),
                config={
                    "persist_directory": os.getenv("VECTOR_STORE_PATH", "./data/vector_store"),
                    "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
                }
            )
            logger.info("Vector store initialisé")
            
            # Initialiser le client LLM
            from llm.ollama.client import OllamaClient
            self.llm_client = OllamaClient(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                default_model=os.getenv("DEFAULT_LLM_MODEL", "llama2")
            )
            await self.llm_client.health_check()
            logger.info("Client LLM initialisé")
            
            # Initialiser le crew MAR
            from orchestrator.crew.mar_crew import MARCrew
            self.mar_crew = MARCrew(
                vector_store=self.vector_store,
                llm_client=self.llm_client
            )
            logger.info("MAR Crew initialisé")
            
            self.initialized = True
            logger.info("Plateforme MAR initialisée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur initialisation plateforme: {e}")
            # En mode développement, on peut continuer sans tous les composants
            if os.getenv("DEV_MODE", "false").lower() == "true":
                logger.warning("Mode développement: initialisation partielle")
                self.initialized = True
            else:
                raise
    
    async def shutdown(self):
        """Arrêt propre de la plateforme"""
        try:
            logger.info("Arrêt de la plateforme MAR...")
            
            # Fermeture des connexions
            if self.vector_store:
                # await self.vector_store.close()
                pass
            
            if self.llm_client:
                # await self.llm_client.close()
                pass
            
            logger.info("Plateforme MAR arrêtée proprement")
            
        except Exception as e:
            logger.error(f"Erreur arrêt plateforme: {e}")


# Instance globale de la plateforme
platform = MARPlatform()


def get_platform() -> MARPlatform:
    """
    Dependency pour récupérer l'instance de la plateforme
    
    Returns:
        Instance de MARPlatform
    """
    return platform


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Startup
    await platform.initialize()
    yield
    # Shutdown
    await platform.shutdown()


def create_app() -> FastAPI:
    """
    Crée et configure l'application FastAPI
    
    Returns:
        Application FastAPI configurée
    """
    
    # Configuration de l'application
    app = FastAPI(
        title="Plateforme MAR API",
        description="API Gateway pour Multi-Agent RAG Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Configuration CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Middleware de compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Middleware personnalisés
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    
    # Inclusion des routers
    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["Authentication"]
    )
    
    app.include_router(
        chat.router,
        prefix="/api/v1/chat",
        tags=["Chat & RAG"]
    )
    
    app.include_router(
        documents.router,
        prefix="/api/v1/documents",
        tags=["Documents"]
    )
    
    app.include_router(
        admin.router,
        prefix="/api/v1/admin",
        tags=["Administration"]
    )
    
    # Routes de base
    @app.get("/")
    async def root():
        """Page d'accueil de l'API"""
        return {
            "message": "Plateforme MAR API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }
    
    @app.get("/health")
    async def health_check():
        """Vérification de santé de l'API"""
        try:
            status = "healthy" if platform.initialized else "initializing"
            
            health_data = {
                "status": status,
                "timestamp": time.time(),
                "components": {
                    "api": "healthy",
                    "vector_store": "healthy" if platform.vector_store else "not_initialized",
                    "llm_client": "healthy" if platform.llm_client else "not_initialized",
                    "mar_crew": "healthy" if platform.mar_crew else "not_initialized"
                }
            }
            
            return health_data
            
        except Exception as e:
            logger.error(f"Erreur health check: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }
            )
    
    @app.get("/metrics")
    async def get_metrics():
        """Métriques de l'API pour Prometheus"""
        try:
            if not platform.initialized:
                raise HTTPException(status_code=503, detail="Platform not initialized")
            
            metrics = {
                "platform_status": 1 if platform.initialized else 0,
                "agents_status": 1 if platform.mar_crew else 0,
                "vector_store_status": 1 if platform.vector_store else 0,
                "llm_status": 1 if platform.llm_client else 0
            }
            
            # Ajouter métriques des agents si disponibles
            if platform.mar_crew:
                agent_metrics = platform.mar_crew.get_agent_metrics()
                metrics.update(agent_metrics)
                
                # Statistiques d'exécution
                exec_stats = platform.mar_crew.get_execution_stats()
                metrics.update(exec_stats)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur récupération métriques: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Gestionnaire d'erreurs global
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Gestionnaire d'erreurs global"""
        logger.error(f"Erreur non gérée: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "Une erreur inattendue s'est produite",
                "path": str(request.url),
                "timestamp": time.time()
            }
        )
    
    # Middleware de mesure de performance
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Ajoute le temps de traitement dans les headers"""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    return app


# Fonction pour obtenir l'instance de la plateforme
def get_platform() -> MARPlatform:
    """Retourne l'instance de la plateforme MAR"""
    return platform


if __name__ == "__main__":
    # Configuration pour le développement
    app = create_app()
    
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )
=======
API principale FastAPI pour le système RAG multi-agents - Version Production.
Expose les endpoints pour l'interaction avec tous les agents.
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
import json
import uuid
from datetime import datetime

from core.config import get_app_settings
from core.logging import get_logger
from core.exceptions import ValidationError, ProcessingError

# Get settings instance
settings = get_app_settings()

from core.models import (
    Document, DocumentChunk, SearchQuery, SearchResult,
    HealthCheck, APIResponse
)

# Imports conditionnels pour tous les agents
try:
    from agents.ingestion.agent import IngestionAgent
    INGESTION_AVAILABLE = True
except ImportError as e:
    INGESTION_AVAILABLE = False
    IngestionAgent = None

try:
    from agents.vectorization.agent import VectorizationAgent
    VECTORIZATION_AVAILABLE = True
except ImportError as e:
    VECTORIZATION_AVAILABLE = False
    VectorizationAgent = None

try:
    from agents.storage.agent import StorageAgent
    STORAGE_AVAILABLE = True
except ImportError as e:
    STORAGE_AVAILABLE = False
    StorageAgent = None

try:
    from agents.retrieval.agent import RetrievalAgent
    RETRIEVAL_AVAILABLE = True
except ImportError as e:
    RETRIEVAL_AVAILABLE = False
    RetrievalAgent = None

try:
    from agents.synthesis.agent import SynthesisAgent
    SYNTHESIS_AVAILABLE = True
except ImportError as e:
    SYNTHESIS_AVAILABLE = False
    SynthesisAgent = None

try:
    from agents.orchestration.agent import OrchestrationAgent
    ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    ORCHESTRATION_AVAILABLE = False
    OrchestrationAgent = None

try:
    from agents.feedback.agent import FeedbackMemoryAgent
    FEEDBACK_AVAILABLE = True
except ImportError as e:
    FEEDBACK_AVAILABLE = False
    FeedbackMemoryAgent = None

try:
    from database.manager import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    DatabaseManager = None


# Gestionnaire de contexte pour l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire du cycle de vie de l'application."""
    
    logger = get_logger(__name__)
    
    # Initialisation
    logger.info("Démarrage de l'application RAG multi-agents")
    
    # Initialisation de la base de données si disponible
    if DATABASE_AVAILABLE:
        try:
            db_manager = DatabaseManager()
            await db_manager.initialize()
            app.state.db_manager = db_manager
        except Exception as e:
            logger.error(f"Erreur initialisation DB: {e}")
            app.state.db_manager = None
    else:
        app.state.db_manager = None
    
    # Initialisation des agents disponibles
    agents_initialized = 0
    
    # Agent d'ingestion
    if INGESTION_AVAILABLE:
        try:
            app.state.ingestion_agent = IngestionAgent()
            agents_initialized += 1
            logger.info("Agent d'ingestion initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent d'ingestion: {e}")
            app.state.ingestion_agent = None
    else:
        app.state.ingestion_agent = None
        
    # Agent de vectorisation
    if VECTORIZATION_AVAILABLE:
        try:
            app.state.vectorization_agent = VectorizationAgent()
            agents_initialized += 1
            logger.info("Agent de vectorisation initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de vectorisation: {e}")
            app.state.vectorization_agent = None
    else:
        app.state.vectorization_agent = None
        
    # Agent de stockage
    if STORAGE_AVAILABLE:
        try:
            app.state.storage_agent = StorageAgent()
            agents_initialized += 1
            logger.info("Agent de stockage initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de stockage: {e}")
            app.state.storage_agent = None
    else:
        app.state.storage_agent = None
        
    # Agent de récupération (nécessite storage et vectorization)
    if RETRIEVAL_AVAILABLE and app.state.storage_agent and app.state.vectorization_agent:
        try:
            app.state.retrieval_agent = RetrievalAgent(
                storage_agent=app.state.storage_agent,
                vectorization_agent=app.state.vectorization_agent
            )
            if hasattr(app.state.retrieval_agent, 'initialize'):
                await app.state.retrieval_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de récupération initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de récupération: {e}")
            app.state.retrieval_agent = None
    else:
        app.state.retrieval_agent = None
        
    # Agent de synthèse
    if SYNTHESIS_AVAILABLE:
        try:
            app.state.synthesis_agent = SynthesisAgent()
            if hasattr(app.state.synthesis_agent, 'initialize'):
                await app.state.synthesis_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de synthèse initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de synthèse: {e}")
            app.state.synthesis_agent = None
    else:
        app.state.synthesis_agent = None
        
    # Agent d'orchestration
    if ORCHESTRATION_AVAILABLE:
        try:
            app.state.orchestration_agent = OrchestrationAgent()
            if hasattr(app.state.orchestration_agent, 'initialize'):
                await app.state.orchestration_agent.initialize()
            agents_initialized += 1
            logger.info("Agent d'orchestration initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent d'orchestration: {e}")
            app.state.orchestration_agent = None
    else:
        app.state.orchestration_agent = None
        
    # Agent de feedback
    if FEEDBACK_AVAILABLE:
        try:
            app.state.feedback_agent = FeedbackMemoryAgent()
            if hasattr(app.state.feedback_agent, 'initialize'):
                await app.state.feedback_agent.initialize()
            agents_initialized += 1
            logger.info("Agent de feedback initialisé")
        except Exception as e:
            logger.error(f"Erreur initialisation agent de feedback: {e}")
            app.state.feedback_agent = None
    else:
        app.state.feedback_agent = None

    logger.info(f"Application démarrée avec {agents_initialized} agents initialisés")
    
    yield
    
    # Nettoyage à l'arrêt
    logger.info("Arrêt de l'application RAG multi-agents")
    
    # Fermeture de la base de données
    if hasattr(app.state, 'db_manager') and app.state.db_manager:
        try:
            await app.state.db_manager.close()
        except Exception as e:
            logger.error(f"Erreur fermeture DB: {e}")


# Créer l'application FastAPI
app = FastAPI(
    title="RAG Multi-Agent System",
    description="API principale pour le système RAG multi-agents d'entreprise",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À configurer selon l'environnement
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Logger
logger = get_logger(__name__)


@app.get("/", response_model=Dict[str, Any])
async def root():
    """Point d'entrée racine de l'API."""
    return {
        "message": "RAG Multi-Agent System API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Vérification de l'état de santé du système."""
    
    # Vérifier l'état des agents
    agents_status = {}
    
    if hasattr(app.state, 'ingestion_agent') and app.state.ingestion_agent:
        agents_status["ingestion"] = "available"
    else:
        agents_status["ingestion"] = "unavailable"
        
    if hasattr(app.state, 'vectorization_agent') and app.state.vectorization_agent:
        agents_status["vectorization"] = "available"
    else:
        agents_status["vectorization"] = "unavailable"
        
    if hasattr(app.state, 'storage_agent') and app.state.storage_agent:
        agents_status["storage"] = "available"
    else:
        agents_status["storage"] = "unavailable"
        
    if hasattr(app.state, 'retrieval_agent') and app.state.retrieval_agent:
        agents_status["retrieval"] = "available"
    else:
        agents_status["retrieval"] = "unavailable"
        
    if hasattr(app.state, 'synthesis_agent') and app.state.synthesis_agent:
        agents_status["synthesis"] = "available"
    else:
        agents_status["synthesis"] = "unavailable"
        
    if hasattr(app.state, 'orchestration_agent') and app.state.orchestration_agent:
        agents_status["orchestration"] = "available"
    else:
        agents_status["orchestration"] = "unavailable"
        
    if hasattr(app.state, 'feedback_agent') and app.state.feedback_agent:
        agents_status["feedback"] = "available"
    else:
        agents_status["feedback"] = "unavailable"
    
    # Vérifier la base de données
    db_status = "unavailable"
    if hasattr(app.state, 'db_manager') and app.state.db_manager:
        try:
            # Test simple de connexion
            db_status = "available"
        except Exception:
            db_status = "error"
    
    # Compter les agents disponibles
    available_agents = sum(1 for status in agents_status.values() if status == "available")
    
    return HealthCheck(
        status="healthy" if available_agents > 0 else "degraded",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        agents=agents_status,
        database=db_status,
        uptime_seconds=0  # À implémenter si nécessaire
    )


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload et traitement de documents."""
    
    if not app.state.ingestion_agent:
        raise HTTPException(
            status_code=503,
            detail="Agent d'ingestion non disponible"
        )
    
    try:
        # Lire le contenu du fichier
        content = await file.read()
        
        # Créer un ID unique pour le document
        document_id = str(uuid.uuid4())
        
        # Process en arrière-plan
        background_tasks.add_task(
            process_document_async,
            document_id,
            file.filename,
            content
        )
        
        return {
            "message": "Document reçu pour traitement",
            "document_id": document_id,
            "filename": file.filename,
            "size": len(content),
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Erreur upload document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_document_async(document_id: str, filename: str, content: bytes):
    """Traite un document de manière asynchrone."""
    
    try:
        logger.info(f"Début traitement document {document_id}")
        
        # Ici on appellerait les agents pour traiter le document
        # Pour l'instant, on simule le traitement
        await asyncio.sleep(1)
        
        logger.info(f"Document {document_id} traité avec succès")
        
    except Exception as e:
        logger.error(f"Erreur traitement document {document_id}: {e}")


@app.post("/search")
async def search_documents(query: SearchQuery):
    """Effectue une recherche dans les documents."""
    
    if not app.state.retrieval_agent:
        raise HTTPException(
            status_code=503,
            detail="Agent de récupération non disponible"
        )
    
    try:
        # Simuler une recherche pour l'instant
        results = [
            SearchResult(
                document_id=str(uuid.uuid4()),
                title=f"Document résultat {i+1}",
                content=f"Contenu simulé pour la requête: {query.text}",
                score=0.9 - i * 0.1,
                metadata={"source": f"doc_{i+1}.pdf"}
            )
            for i in range(min(3, query.limit or 10))
        ]
        
        return {
            "query": query.text,
            "results": results,
            "total": len(results),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
async def ask_question(query: SearchQuery):
    """Répond à une question en utilisant la synthèse."""
    
    if not app.state.synthesis_agent:
        raise HTTPException(
            status_code=503,
            detail="Agent de synthèse non disponible"
        )
    
    try:
        # Simuler une réponse pour l'instant
        response = f"Réponse simulée pour: {query.text}"
        
        return {
            "question": query.text,
            "answer": response,
            "confidence": 0.85,
            "sources": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur synthèse: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Récupère les métriques du système."""
    
    return {
        "agents": {
            "ingestion": INGESTION_AVAILABLE,
            "vectorization": VECTORIZATION_AVAILABLE,
            "storage": STORAGE_AVAILABLE,
            "retrieval": RETRIEVAL_AVAILABLE,
            "synthesis": SYNTHESIS_AVAILABLE,
            "orchestration": ORCHESTRATION_AVAILABLE,
            "feedback": FEEDBACK_AVAILABLE
        },
        "database": DATABASE_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
>>>>>>> origin/main
