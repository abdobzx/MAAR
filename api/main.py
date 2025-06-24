"""
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
            from vector_store.factory import create_vector_store
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
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
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
