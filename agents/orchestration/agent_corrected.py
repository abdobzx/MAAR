"""
Agent d'orchestration pour coordonner les flux de travail multi-agents.
Version corrigée pour production - compatible avec l'architecture existante.
"""

import asyncio
import uuid
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

from core.config import get_settings, settings
from core.exceptions import OrchestrationError, ValidationError, AgentError
from core.logging import get_logger
from core.models import (
    Document, DocumentChunk, SearchQuery, SearchResult,
    ProcessingStatus, TaskPriority, OrchestrationRequest,
    OrchestrationResponse, WorkflowStep, AgentTask, LLMConfig,
    WorkflowType
)
from core.providers import AIProviderManager
from database.manager import DatabaseManager

# Try to import SothemaAI provider with fallback
try:
    from core.providers.sothemaai_provider import SothemaAIProvider
    SOTHEMAAI_AVAILABLE = True
except ImportError:
    SOTHEMAAI_AVAILABLE = False
    SothemaAIProvider = None

logger = get_logger(__name__)


class WorkflowState(BaseModel):
    """État du workflow pour l'orchestration."""
    workflow_id: str
    user_id: str
    organization_id: str
    query: SearchQuery
    documents: List[Document] = Field(default_factory=list)
    chunks: List[DocumentChunk] = Field(default_factory=list)
    search_results: List[SearchResult] = Field(default_factory=list)
    synthesis_result: Optional[str] = None
    confidence_score: float = 0.0
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    completed_steps: List[str] = Field(default_factory=list)
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    token_usage: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationAgent:
    """
    Agent d'orchestration principal pour coordonner les workflows multi-agents.
    Version corrigée pour la production.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialise l'agent d'orchestration."""
        self.config = config or {}
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # Initialisation du gestionnaire de fournisseurs
        self.provider_manager = AIProviderManager()
        
        # Initialisation du gestionnaire de base de données
        self.db_manager = DatabaseManager()
        
        # État des workflows actifs
        self.active_workflows: Dict[str, WorkflowState] = {}
        
        # Configuration des retry
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)
        
        self.logger.info("OrchestrationAgent initialisé avec succès")
    
    async def initialize(self):
        """Initialise l'agent et ses dépendances."""
        try:
            # Initialisation du gestionnaire de base de données
            await self.db_manager.initialize()
            
            # Configuration des fournisseurs d'IA
            await self._setup_ai_providers()
            
            self.logger.info("Agent d'orchestration initialisé avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            raise OrchestrationError(f"Échec de l'initialisation: {e}")
    
    async def _setup_ai_providers(self):
        """Configure les fournisseurs d'IA."""
        try:
            # Configuration prioritaire de SothemaAI si disponible
            if SOTHEMAAI_AVAILABLE and self.settings.SOTHEMAAI_API_KEY:
                try:
                    sothemaai_config = LLMConfig(
                        model=self.settings.SOTHEMAAI_MODEL,
                        provider="sothemaai",
                        sothemaai_base_url=self.settings.SOTHEMAAI_BASE_URL,
                        sothemaai_api_key=self.settings.SOTHEMAAI_API_KEY
                    )
                    sothemaai_provider = SothemaAIProvider(sothemaai_config)
                    await self.provider_manager.register_provider(sothemaai_provider)
                    self.logger.info("SothemaAI provider configuré")
                except Exception as e:
                    self.logger.warning(f"Impossible de configurer SothemaAI: {e}")
            
            # Vérification qu'au moins un fournisseur est disponible
            if not self.provider_manager.has_provider("sothemaai"):
                self.logger.warning("Aucun fournisseur d'IA configuré")
            
            available_providers = self.provider_manager.get_available_providers()
            self.logger.info(f"Fournisseurs disponibles: {available_providers}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la configuration des fournisseurs: {e}")
            raise
    
    async def process_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """Traite une demande d'orchestration."""
        workflow_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Début du traitement de la demande {workflow_id}")
            
            # Validation de la demande
            await self._validate_request(request)
            
            # Création de l'état initial du workflow
            initial_state = await self._create_initial_state(workflow_id, request)
            
            # Exécution du workflow selon le type
            result = await self._execute_workflow(initial_state, request.workflow_type)
            
            # Construction de la réponse
            response = OrchestrationResponse(
                workflow_id=workflow_id,
                status=ProcessingStatus.COMPLETED,
                result=result.synthesis_result,
                confidence_score=result.confidence_score,
                citations=result.citations,
                execution_time=(result.end_time - result.start_time).total_seconds() if result.end_time else 0.0,
                steps_completed=result.completed_steps,
                # Champs de compatibilité
                response=result.synthesis_result or "Traitement terminé",
                sources=result.search_results,
                session_id=request.session_id or workflow_id,
                processing_time=(result.end_time - result.start_time).total_seconds() if result.end_time else 0.0,
                agent_execution_summary={
                    "workflow_type": request.workflow_type,
                    "steps_completed": len(result.completed_steps),
                    "confidence_score": result.confidence_score
                }
            )
            
            self.logger.info(f"Demande {workflow_id} traitée avec succès")
            return response
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de {workflow_id}: {e}")
            return OrchestrationResponse(
                workflow_id=workflow_id,
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                execution_time=0.0,
                steps_completed=[],
                # Champs de compatibilité
                response=f"Erreur: {str(e)}",
                sources=[],
                session_id=request.session_id or workflow_id,
                processing_time=0.0,
                agent_execution_summary={"error": str(e)}
            )
    
    async def _validate_request(self, request: OrchestrationRequest):
        """Valide une demande d'orchestration."""
        if not request.query or len(request.query.strip()) == 0:
            raise ValidationError("La requête ne peut pas être vide")
        
        if len(request.query) > 10000:
            raise ValidationError("La requête est trop longue (max 10000 caractères)")
        
        # Validation des IDs utilisateur et organisation si fournis
        if request.user_id and not request.user_id.strip():
            raise ValidationError("L'ID utilisateur ne peut pas être vide")
        
        if request.organization_id and not request.organization_id.strip():
            raise ValidationError("L'ID organisation ne peut pas être vide")
    
    async def _create_initial_state(self, workflow_id: str, request: OrchestrationRequest) -> WorkflowState:
        """Crée l'état initial du workflow."""
        
        # Création de l'objet SearchQuery approprié
        search_query = SearchQuery(
            query=request.query,
            user_id=uuid.UUID(request.user_id) if request.user_id else None,
            organization_id=uuid.UUID(request.organization_id) if request.organization_id else None
        )
        
        state = WorkflowState(
            workflow_id=workflow_id,
            user_id=request.user_id or "anonymous",
            organization_id=request.organization_id or "default",
            query=search_query,
            metadata=request.metadata or {}
        )
        
        self.active_workflows[workflow_id] = state
        return state
    
    async def _execute_workflow(self, state: WorkflowState, workflow_type: WorkflowType) -> WorkflowState:
        """Exécute un workflow selon son type."""
        try:
            if workflow_type == WorkflowType.SIMPLE_QA:
                return await self._execute_simple_qa_workflow(state)
            elif workflow_type == WorkflowType.MULTI_DOC_ANALYSIS:
                return await self._execute_multi_doc_analysis_workflow(state)
            elif workflow_type == WorkflowType.FACT_CHECKING:
                return await self._execute_fact_checking_workflow(state)
            elif workflow_type == WorkflowType.SUMMARIZATION:
                return await self._execute_summarization_workflow(state)
            elif workflow_type == WorkflowType.RESEARCH:
                return await self._execute_research_workflow(state)
            else:
                raise OrchestrationError(f"Type de workflow non supporté: {workflow_type}")
                
        except Exception as e:
            state.error_message = str(e)
            state.end_time = datetime.utcnow()
            raise
    
    async def _execute_simple_qa_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow de Q&A simple."""
        state.current_step = "retrieval"
        
        # Étape 1: Récupération
        await self._execute_retrieval_step(state)
        state.completed_steps.append("retrieval")
        
        # Étape 2: Synthèse
        state.current_step = "synthesis"
        await self._execute_synthesis_step(state)
        state.completed_steps.append("synthesis")
        
        state.end_time = datetime.utcnow()
        return state
    
    async def _execute_multi_doc_analysis_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow d'analyse multi-documents."""
        state.current_step = "document_retrieval"
        
        # Étape 1: Récupération de documents
        await self._execute_retrieval_step(state)
        state.completed_steps.append("document_retrieval")
        
        # Étape 2: Analyse contextuelle
        state.current_step = "contextual_analysis"
        await self._execute_contextual_analysis_step(state)
        state.completed_steps.append("contextual_analysis")
        
        # Étape 3: Synthèse comparative
        state.current_step = "comparative_synthesis"
        await self._execute_synthesis_step(state)
        state.completed_steps.append("comparative_synthesis")
        
        state.end_time = datetime.utcnow()
        return state
    
    async def _execute_fact_checking_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow de vérification des faits."""
        state.current_step = "evidence_retrieval"
        
        # Étape 1: Récupération de preuves
        await self._execute_retrieval_step(state)
        state.completed_steps.append("evidence_retrieval")
        
        # Étape 2: Vérification croisée
        state.current_step = "cross_verification"
        await self._execute_verification_step(state)
        state.completed_steps.append("cross_verification")
        
        # Étape 3: Synthèse de vérification
        state.current_step = "verification_synthesis"
        await self._execute_synthesis_step(state)
        state.completed_steps.append("verification_synthesis")
        
        state.end_time = datetime.utcnow()
        return state
    
    async def _execute_summarization_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow de résumé."""
        state.current_step = "content_retrieval"
        
        # Étape 1: Récupération de contenu
        await self._execute_retrieval_step(state)
        state.completed_steps.append("content_retrieval")
        
        # Étape 2: Synthèse résumée
        state.current_step = "summarization"
        await self._execute_synthesis_step(state, synthesis_type="summarization")
        state.completed_steps.append("summarization")
        
        state.end_time = datetime.utcnow()
        return state
    
    async def _execute_research_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow de recherche approfondie."""
        state.current_step = "comprehensive_retrieval"
        
        # Étape 1: Récupération exhaustive
        await self._execute_retrieval_step(state)
        state.completed_steps.append("comprehensive_retrieval")
        
        # Étape 2: Analyse thématique
        state.current_step = "thematic_analysis"
        await self._execute_thematic_analysis_step(state)
        state.completed_steps.append("thematic_analysis")
        
        # Étape 3: Synthèse de recherche
        state.current_step = "research_synthesis"
        await self._execute_synthesis_step(state, synthesis_type="research")
        state.completed_steps.append("research_synthesis")
        
        state.end_time = datetime.utcnow()
        return state
    
    async def _execute_retrieval_step(self, state: WorkflowState):
        """Exécute l'étape de récupération."""
        try:
            from agents.retrieval.agent import RetrievalAgent
            
            retrieval_agent = RetrievalAgent()
            await retrieval_agent.initialize()
            
            # Recherche de documents pertinents
            search_results = await retrieval_agent.search(
                query=state.query.query,
                user_id=state.user_id,
                organization_id=state.organization_id,
                limit=10
            )
            
            state.search_results = search_results
            self.logger.info(f"Récupération terminée: {len(search_results)} résultats")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération: {e}")
            raise AgentError(f"Échec de la récupération: {e}")
    
    async def _execute_synthesis_step(self, state: WorkflowState, synthesis_type: str = "standard"):
        """Exécute l'étape de synthèse."""
        try:
            from agents.synthesis.agent import SynthesisAgent
            
            synthesis_agent = SynthesisAgent()
            await synthesis_agent.initialize()
            
            # Préparation du contexte pour la synthèse
            synthesis_context = {
                "query": state.query.query,
                "search_results": state.search_results,
                "synthesis_type": synthesis_type,
                "user_id": state.user_id,
                "organization_id": state.organization_id
            }
            
            # Exécution de la synthèse
            synthesis_result = await synthesis_agent.synthesize(synthesis_context)
            
            state.synthesis_result = synthesis_result.get("response", "")
            state.confidence_score = synthesis_result.get("confidence_score", 0.0)
            state.citations = synthesis_result.get("citations", [])
            state.token_usage = synthesis_result.get("token_usage", {})
            
            self.logger.info("Synthèse terminée avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la synthèse: {e}")
            raise AgentError(f"Échec de la synthèse: {e}")
    
    async def _execute_contextual_analysis_step(self, state: WorkflowState):
        """Exécute l'étape d'analyse contextuelle."""
        try:
            # Analyse des relations entre les documents
            documents_analysis = {}
            for result in state.search_results:
                doc_id = str(result.document_id)
                if doc_id not in documents_analysis:
                    documents_analysis[doc_id] = {
                        "chunks": [],
                        "relevance_scores": [],
                        "themes": []
                    }
                
                documents_analysis[doc_id]["chunks"].append(result.content)
                documents_analysis[doc_id]["relevance_scores"].append(result.score)
            
            state.metadata["contextual_analysis"] = documents_analysis
            self.logger.info("Analyse contextuelle terminée")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse contextuelle: {e}")
            raise AgentError(f"Échec de l'analyse contextuelle: {e}")
    
    async def _execute_verification_step(self, state: WorkflowState):
        """Exécute l'étape de vérification croisée."""
        try:
            # Vérification de la cohérence des sources
            verification_results = {
                "consistent_sources": 0,
                "conflicting_sources": 0,
                "confidence_factors": []
            }
            
            # Analyse simple de cohérence basée sur les scores
            for result in state.search_results:
                if result.score > 0.8:
                    verification_results["consistent_sources"] += 1
                elif result.score < 0.5:
                    verification_results["conflicting_sources"] += 1
                
                verification_results["confidence_factors"].append({
                    "source": str(result.document_id),
                    "score": result.score,
                    "content_snippet": result.content[:100]
                })
            
            state.metadata["verification"] = verification_results
            self.logger.info("Vérification croisée terminée")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification: {e}")
            raise AgentError(f"Échec de la vérification: {e}")
    
    async def _execute_thematic_analysis_step(self, state: WorkflowState):
        """Exécute l'étape d'analyse thématique."""
        try:
            # Analyse thématique basique
            themes = {}
            for result in state.search_results:
                # Extraction simple de mots-clés
                words = re.findall(r'\b\w+\b', result.content.lower())
                for word in words:
                    if len(word) > 4:  # Ignorer les mots courts
                        themes[word] = themes.get(word, 0) + 1
            
            # Garder les thèmes les plus fréquents
            top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:10]
            
            state.metadata["thematic_analysis"] = {
                "top_themes": top_themes,
                "total_themes": len(themes)
            }
            
            self.logger.info("Analyse thématique terminée")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse thématique: {e}")
            raise AgentError(f"Échec de l'analyse thématique: {e}")
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retourne le statut d'un workflow."""
        if workflow_id not in self.active_workflows:
            return None
        
        state = self.active_workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "current_step": state.current_step,
            "completed_steps": state.completed_steps,
            "confidence_score": state.confidence_score,
            "execution_time": (datetime.utcnow() - state.start_time).total_seconds(),
            "error_message": state.error_message
        }
    
    async def cleanup_workflow(self, workflow_id: str):
        """Nettoie un workflow terminé."""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
            self.logger.info(f"Workflow {workflow_id} nettoyé")
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé de l'agent d'orchestration."""
        try:
            # Vérification des fournisseurs
            providers_health = {}
            if self.provider_manager.has_provider("sothemaai"):
                try:
                    provider = self.provider_manager.get_provider("sothemaai")
                    providers_health["sothemaai"] = True
                except Exception:
                    providers_health["sothemaai"] = False
            
            # Vérification de la base de données
            db_health = await self.db_manager.health_check()
            
            return {
                "status": "healthy",
                "active_workflows": len(self.active_workflows),
                "providers": providers_health,
                "database": db_health,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
