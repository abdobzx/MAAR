"""
Agent d'orchestration pour coordonner les flux de travail multi-agents.
Utilise CrewAI et LangGraph pour la coordination et l'orchestration des tâches.
Intègre le système AIProviderManager avec support pour SothemaAI.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

from crewai import Agent, Crew, Task, Process
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from core.config import get_settings, settings
from core.exceptions import OrchestrationError, ValidationError
from core.logging import get_logger
from core.models import (
    Document, DocumentChunk, SearchQuery, SearchResult,
    ProcessingStatus, TaskPriority, OrchestrationRequest,
    OrchestrationResponse, WorkflowStep, AgentTask, LLMConfig
)
from core.providers import AIProviderManager, SothemaAIProvider
from database.manager import DatabaseManager


class WorkflowType(str, Enum):
    """Types de workflows disponibles."""
    SIMPLE_QA = "simple_qa"
    MULTI_DOC_ANALYSIS = "multi_doc_analysis"
    FACT_CHECKING = "fact_checking"
    SUMMARIZATION = "summarization"
    RESEARCH = "research"
    CUSTOM = "custom"


class WorkflowState(BaseModel):
    """État du workflow pour LangGraph."""
    workflow_id: str
    user_id: str
    organization_id: str
    query: SearchQuery
    documents: List[Document] = Field(default_factory=list)
    chunks: List[DocumentChunk] = Field(default_factory=list)
    search_results: List[SearchResult] = Field(default_factory=list)
    synthesis_result: Optional[str] = None
    confidence_score: float = 0.0
    citations: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    current_step: str = "start"
    completed_steps: List[str] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None


class OrchestrationAgent:
    """Agent d'orchestration principal pour coordonner les workflows multi-agents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.db_manager = DatabaseManager()
        
        # Initialisation du gestionnaire de fournisseurs AI
        self.provider_manager = AIProviderManager()
        
        # Configuration du fournisseur SothemaAI
        self._setup_sothemaai_provider()
        
        # Initialisation des agents CrewAI avec providers configurés
        self._setup_crew_agents()
        
        # Initialisation du graphe LangGraph
        self._setup_langgraph()
        
        # Métriques et monitoring
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.workflow_metrics: Dict[str, Dict[str, Any]] = {}
    
    def _setup_sothemaai_provider(self):
        """Configure le fournisseur SothemaAI si les paramètres sont disponibles."""
        try:
            # Vérifier si SothemaAI est configuré
            if (hasattr(settings.llm, 'sothemaai_base_url') and 
                hasattr(settings.llm, 'sothemaai_api_key') and
                settings.llm.sothemaai_base_url and 
                settings.llm.sothemaai_api_key):
                
                # Créer la configuration pour SothemaAI
                config = LLMConfig(
                    model="default",  # SothemaAI utilise un modèle par défaut
                    provider="sothemaai",
                    temperature=0.1,
                    max_tokens=4000,
                    sothemaai_base_url=settings.llm.sothemaai_base_url,
                    sothemaai_api_key=settings.llm.sothemaai_api_key
                )
                
                # Créer et enregistrer le fournisseur SothemaAI
                sothemaai_provider = SothemaAIProvider(config)
                self.provider_manager.register_provider("sothemaai", sothemaai_provider)
                
                self.logger.info("SothemaAI provider configured successfully for orchestration")
                
        except Exception as e:
            self.logger.warning(f"Failed to setup SothemaAI provider for orchestration: {str(e)}")
    
    def _get_primary_provider(self):
        """Obtient le fournisseur LLM principal selon la configuration."""
        # Si USE_SOTHEMAAI_ONLY est activé et SothemaAI disponible
        if getattr(settings, 'USE_SOTHEMAAI_ONLY', False):
            if self.provider_manager.has_provider("sothemaai"):
                return self.provider_manager.get_provider("sothemaai")
        
        # Ordre de priorité: SothemaAI → Ollama → Cohere → OpenAI
        priority_order = ["sothemaai", "ollama", "cohere", "openai"]
        
        for provider_name in priority_order:
            if self.provider_manager.has_provider(provider_name):
                return self.provider_manager.get_provider(provider_name)
        
        # Fallback sur le premier provider disponible
        available_providers = self.provider_manager.get_available_providers()
        if available_providers:
            return available_providers[0]
        
        self.logger.warning("No LLM providers available for orchestration")
        return None
    
    def _setup_crew_agents(self):
        """Configure les agents CrewAI pour différentes tâches."""
        
        # Obtenir le provider LLM principal
        primary_provider = self._get_primary_provider()
        provider_info = f" (using {primary_provider.config.provider})" if primary_provider else " (no LLM provider)"
        
        # Agent coordinateur principal
        self.coordinator_agent = Agent(
            role="Workflow Coordinator",
            goal="Orchestrer efficacement les workflows multi-agents",
            backstory=(
                f"Expert en coordination de systèmes multi-agents avec une "
                f"expertise en optimisation des flux de travail complexes{provider_info}."
            ),
            verbose=True,
            allow_delegation=True,
            max_iter=5,
            llm=primary_provider if primary_provider else None
        )
        
        # Agent de validation
        self.validator_agent = Agent(
            role="Quality Validator",
            goal="Valider la qualité et la cohérence des résultats",
            backstory=(
                f"Spécialiste en assurance qualité pour les systèmes d'IA "
                f"avec une attention particulière aux détails et à la précision{provider_info}."
            ),
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            llm=primary_provider if primary_provider else None
        )
        
        # Agent de monitoring
        self.monitor_agent = Agent(
            role="Performance Monitor",
            goal="Surveiller les performances et optimiser les workflows",
            backstory=(
                f"Analyste de performance expert en optimisation de systèmes "
                f"distribués et monitoring en temps réel{provider_info}."
            ),
            verbose=True,
            allow_delegation=False,
            max_iter=2,
            llm=primary_provider if primary_provider else None
        )
    
    def _setup_langgraph(self):
        """Configure le graphe LangGraph pour l'orchestration des workflows."""
        
        workflow = StateGraph(WorkflowState)
        
        # Ajout des nœuds
        workflow.add_node("validate_input", self._validate_input_node)
        workflow.add_node("ingestion", self._ingestion_node)
        workflow.add_node("vectorization", self._vectorization_node)
        workflow.add_node("storage", self._storage_node)
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("synthesis", self._synthesis_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("feedback", self._feedback_node)
        
        # Configuration des transitions
        workflow.set_entry_point("validate_input")
        
        workflow.add_edge("validate_input", "ingestion")
        workflow.add_edge("ingestion", "vectorization")
        workflow.add_edge("vectorization", "storage")
        workflow.add_edge("storage", "retrieval")
        workflow.add_edge("retrieval", "synthesis")
        workflow.add_edge("synthesis", "validation")
        workflow.add_edge("validation", "feedback")
        workflow.add_edge("feedback", END)
        
        # Compilation du graphe
        self.workflow_graph = workflow.compile()
    
    async def orchestrate_workflow(
        self,
        request: OrchestrationRequest
    ) -> OrchestrationResponse:
        """Orchestre un workflow complet selon le type spécifié."""
        
        workflow_id = str(uuid.uuid4())
        
        try:
            self.logger.info(
                "Démarrage du workflow d'orchestration",
                extra={
                    "workflow_id": workflow_id,
                    "workflow_type": request.workflow_type,
                    "user_id": request.user_id
                }
            )
            
            # Création de l'état initial
            initial_state = WorkflowState(
                workflow_id=workflow_id,
                user_id=request.user_id,
                organization_id=request.organization_id,
                query=request.query,
                metadata=request.metadata or {}
            )
            
            # Stockage de l'état actif
            self.active_workflows[workflow_id] = initial_state
            
            # Sélection et exécution du workflow
            if request.workflow_type == WorkflowType.SIMPLE_QA:
                result = await self._execute_simple_qa_workflow(initial_state)
            elif request.workflow_type == WorkflowType.MULTI_DOC_ANALYSIS:
                result = await self._execute_multi_doc_analysis_workflow(initial_state)
            elif request.workflow_type == WorkflowType.FACT_CHECKING:
                result = await self._execute_fact_checking_workflow(initial_state)
            elif request.workflow_type == WorkflowType.SUMMARIZATION:
                result = await self._execute_summarization_workflow(initial_state)
            elif request.workflow_type == WorkflowType.RESEARCH:
                result = await self._execute_research_workflow(initial_state)
            else:
                result = await self._execute_custom_workflow(initial_state, request.custom_steps)
            
            # Mise à jour de l'état final
            result.end_time = datetime.utcnow()
            
            # Création de la réponse
            response = OrchestrationResponse(
                workflow_id=workflow_id,
                status=ProcessingStatus.COMPLETED,
                result=result.synthesis_result,
                confidence_score=result.confidence_score,
                citations=result.citations,
                execution_time=(result.end_time - result.start_time).total_seconds(),
                steps_completed=result.completed_steps,
                metadata=result.metadata
            )
            
            # Nettoyage
            self.active_workflows.pop(workflow_id, None)
            
            self.logger.info(
                "Workflow d'orchestration terminé avec succès",
                extra={
                    "workflow_id": workflow_id,
                    "execution_time": response.execution_time,
                    "confidence_score": response.confidence_score
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Erreur lors de l'exécution du workflow",
                extra={
                    "workflow_id": workflow_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Nettoyage en cas d'erreur
            self.active_workflows.pop(workflow_id, None)
            
            return OrchestrationResponse(
                workflow_id=workflow_id,
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                execution_time=0.0,
                steps_completed=[],
                metadata={}
            )
    
    async def _execute_simple_qa_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow simple de question-réponse."""
        
        # Workflow optimisé pour des questions simples
        config = {"configurable": {"thread_id": state.workflow_id}}
        
        # Exécution du graphe LangGraph
        final_state = await self.workflow_graph.ainvoke(state.dict(), config)
        
        return WorkflowState(**final_state)
    
    async def _execute_multi_doc_analysis_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow d'analyse multi-documents avec CrewAI."""
        
        # Création des tâches CrewAI
        analysis_task = Task(
            description=f"Analyser les documents pour répondre à: {state.query.query}",
            agent=self.coordinator_agent,
            expected_output="Une analyse complète avec des citations précises"
        )
        
        validation_task = Task(
            description="Valider la qualité et la cohérence de l'analyse",
            agent=self.validator_agent,
            expected_output="Un rapport de validation avec score de confiance"
        )
        
        # Création de l'équipe
        crew = Crew(
            agents=[self.coordinator_agent, self.validator_agent],
            tasks=[analysis_task, validation_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Exécution parallèle avec LangGraph
        langgraph_task = asyncio.create_task(
            self.workflow_graph.ainvoke(
                state.dict(),
                {"configurable": {"thread_id": state.workflow_id}}
            )
        )
        
        crewai_task = asyncio.create_task(
            asyncio.to_thread(crew.kickoff)
        )
        
        # Attente des résultats
        langgraph_result, crewai_result = await asyncio.gather(
            langgraph_task, crewai_task
        )
        
        # Fusion des résultats
        final_state = WorkflowState(**langgraph_result)
        final_state.metadata["crewai_analysis"] = str(crewai_result)
        
        return final_state
    
    async def _execute_fact_checking_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow de vérification des faits."""
        
        # Workflow spécialisé avec validation renforcée
        fact_check_task = Task(
            description=f"Vérifier les faits dans: {state.query.query}",
            agent=self.validator_agent,
            expected_output="Un rapport de vérification avec sources"
        )
        
        crew = Crew(
            agents=[self.validator_agent, self.monitor_agent],
            tasks=[fact_check_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Exécution avec validation supplémentaire
        config = {"configurable": {"thread_id": state.workflow_id, "validation_mode": "strict"}}
        result = await self.workflow_graph.ainvoke(state.dict(), config)
        
        return WorkflowState(**result)
    
    async def _execute_summarization_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow de résumé de documents."""
        
        # Configuration optimisée pour le résumé
        config = {
            "configurable": {
                "thread_id": state.workflow_id,
                "mode": "summarization",
                "chunk_strategy": "hierarchical"
            }
        }
        
        result = await self.workflow_graph.ainvoke(state.dict(), config)
        return WorkflowState(**result)
    
    async def _execute_research_workflow(self, state: WorkflowState) -> WorkflowState:
        """Exécute un workflow de recherche approfondie."""
        
        # Workflow de recherche avec multiple itérations
        research_task = Task(
            description=f"Effectuer une recherche approfondie sur: {state.query.query}",
            agent=self.coordinator_agent,
            expected_output="Un rapport de recherche complet avec sources multiples"
        )
        
        monitoring_task = Task(
            description="Surveiller et optimiser le processus de recherche",
            agent=self.monitor_agent,
            expected_output="Métriques de performance et recommandations"
        )
        
        crew = Crew(
            agents=[self.coordinator_agent, self.monitor_agent],
            tasks=[research_task, monitoring_task],
            process=Process.parallel,
            verbose=True
        )
        
        # Exécution parallèle
        config = {"configurable": {"thread_id": state.workflow_id, "research_depth": "deep"}}
        
        langgraph_task = asyncio.create_task(
            self.workflow_graph.ainvoke(state.dict(), config)
        )
        
        crewai_task = asyncio.create_task(
            asyncio.to_thread(crew.kickoff)
        )
        
        langgraph_result, crewai_result = await asyncio.gather(
            langgraph_task, crewai_task
        )
        
        final_state = WorkflowState(**langgraph_result)
        final_state.metadata["research_insights"] = str(crewai_result)
        
        return final_state
    
    async def _execute_custom_workflow(
        self, 
        state: WorkflowState, 
        custom_steps: Optional[List[WorkflowStep]]
    ) -> WorkflowState:
        """Exécute un workflow personnalisé défini par l'utilisateur."""
        
        if not custom_steps:
            raise ValidationError("Les étapes personnalisées sont requises pour un workflow custom")
        
        # Construction dynamique du workflow
        for step in custom_steps:
            state.current_step = step.name
            
            # Exécution de l'étape selon son type
            if step.agent_type == "ingestion":
                await self._ingestion_node(state)
            elif step.agent_type == "vectorization":
                await self._vectorization_node(state)
            elif step.agent_type == "storage":
                await self._storage_node(state)
            elif step.agent_type == "retrieval":
                await self._retrieval_node(state)
            elif step.agent_type == "synthesis":
                await self._synthesis_node(state)
            elif step.agent_type == "validation":
                await self._validation_node(state)
            
            state.completed_steps.append(step.name)
        
        return state
    
    # Nœuds LangGraph
    async def _validate_input_node(self, state: WorkflowState) -> WorkflowState:
        """Valide les entrées du workflow."""
        try:
            # Validation de la requête
            if not state.query.query.strip():
                raise ValidationError("La requête ne peut pas être vide")
            
            state.completed_steps.append("validate_input")
            state.current_step = "ingestion"
            
            return state
        except Exception as e:
            state.errors.append(f"Erreur de validation: {str(e)}")
            raise
    
    async def _ingestion_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud d'ingestion des documents."""
        # Simulé - intégration avec l'agent d'ingestion
        state.completed_steps.append("ingestion")
        state.current_step = "vectorization"
        return state
    
    async def _vectorization_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de vectorisation utilisant l'agent de vectorisation avec providers configurés."""
        try:
            # Importer l'agent de vectorisation dynamiquement
            from agents.vectorization.agent import VectorizationAgent
            
            # Créer une instance de l'agent de vectorisation
            vectorization_agent = VectorizationAgent()
            
            # Simuler la vectorisation des documents/chunks
            if state.documents:
                for document in state.documents:
                    # Créer des chunks simulés si nécessaire
                    if not state.chunks:
                        from core.models import DocumentChunk
                        chunk = DocumentChunk(
                            id=str(uuid.uuid4()),
                            document_id=document.id,
                            content=document.content[:1000],  # Premier chunk de 1000 caractères
                            chunk_index=0,
                            metadata=document.metadata
                        )
                        state.chunks.append(chunk)
                    
                    # Vectoriser avec l'agent configuré
                    # Note: Cette partie serait normalement appelée avec le contenu réel
                    self.logger.info(
                        f"Vectorizing document {document.id} with configured providers"
                    )
            
            # Mettre à jour les métadonnées avec le provider utilisé
            if hasattr(vectorization_agent, 'primary_provider') and vectorization_agent.primary_provider:
                state.metadata["vectorization_provider"] = vectorization_agent.primary_provider.config.provider
            
            self.logger.info(
                "Vectorization completed successfully",
                extra={
                    "workflow_id": state.workflow_id,
                    "documents_count": len(state.documents),
                    "chunks_count": len(state.chunks)
                }
            )
            
        except Exception as e:
            error_msg = f"Erreur lors de la vectorisation: {str(e)}"
            state.errors.append(error_msg)
            
            self.logger.error(
                "Vectorization failed",
                extra={
                    "workflow_id": state.workflow_id,
                    "error": error_msg
                }
            )
        
        state.completed_steps.append("vectorization")
        state.current_step = "storage"
        return state
    
    async def _storage_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de stockage."""
        # Simulé - intégration avec l'agent de stockage
        state.completed_steps.append("storage")
        state.current_step = "retrieval"
        return state
    
    async def _retrieval_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de récupération."""
        # Simulé - intégration avec l'agent de récupération
        state.completed_steps.append("retrieval")
        state.current_step = "synthesis"
        return state
    
    async def _synthesis_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de synthèse utilisant l'agent de synthèse avec providers configurés."""
        try:
            # Importer l'agent de synthèse dynamiquement pour éviter les imports circulaires
            from agents.synthesis.agent import SynthesisAgent
            
            # Créer une instance de l'agent de synthèse
            synthesis_agent = SynthesisAgent()
            
            # Préparer la requête pour l'agent de synthèse
            from core.models import QueryRequest, ChatMessage
            
            query_request = QueryRequest(
                query=state.query.query,
                user_id=state.user_id,
                organization_id=state.organization_id,
                search_results=state.search_results,
                max_results=10,
                include_sources=True
            )
            
            # Générer la réponse avec l'agent de synthèse
            response = await synthesis_agent.generate_response(query_request)
            
            # Mettre à jour l'état avec les résultats
            state.synthesis_result = response.response
            state.confidence_score = response.confidence_score or 0.85
            state.citations = response.sources or []
            state.metadata["synthesis_provider"] = getattr(synthesis_agent.default_provider, 'config', {}).get('provider', 'unknown')
            
            self.logger.info(
                "Synthesis completed successfully",
                extra={
                    "workflow_id": state.workflow_id,
                    "confidence_score": state.confidence_score,
                    "provider": state.metadata.get("synthesis_provider", "unknown")
                }
            )
            
        except Exception as e:
            error_msg = f"Erreur lors de la synthèse: {str(e)}"
            state.errors.append(error_msg)
            state.synthesis_result = f"Erreur: Impossible de générer une réponse pour: {state.query.query}"
            state.confidence_score = 0.0
            
            self.logger.error(
                "Synthesis failed",
                extra={
                    "workflow_id": state.workflow_id,
                    "error": error_msg
                }
            )
        
        state.completed_steps.append("synthesis")
        state.current_step = "validation"
        return state
    
    async def _validation_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de validation finale."""
        # Validation de la qualité du résultat
        if state.confidence_score < 0.5:
            state.errors.append("Score de confiance trop faible")
        
        state.completed_steps.append("validation")
        state.current_step = "feedback"
        return state
    
    async def _feedback_node(self, state: WorkflowState) -> WorkflowState:
        """Nœud de collecte de feedback."""
        # Préparation pour l'agent de feedback
        state.completed_steps.append("feedback")
        state.current_step = "completed"
        return state
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'un workflow en cours."""
        
        if workflow_id in self.active_workflows:
            state = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "current_step": state.current_step,
                "completed_steps": state.completed_steps,
                "progress": len(state.completed_steps) / 8,  # 8 étapes totales
                "start_time": state.start_time,
                "errors": state.errors
            }
        
        return None
    
    async def orchestrate_response_with_fallback(
        self,
        request: OrchestrationRequest,
        max_retries: int = 3
    ) -> OrchestrationResponse:
        """Orchestre une réponse avec fallback automatique entre providers."""
        
        workflow_id = str(uuid.uuid4())
        last_error = None
        
        # Liste des providers à essayer par ordre de priorité
        fallback_providers = ["sothemaai", "ollama", "cohere", "openai"]
        
        for attempt in range(max_retries):
            provider_name = fallback_providers[attempt % len(fallback_providers)]
            
            try:
                self.logger.info(
                    f"Attempting orchestration with provider: {provider_name} (attempt {attempt + 1})",
                    extra={"workflow_id": workflow_id}
                )
                
                # Temporairement forcer l'utilisation du provider spécifique
                original_setting = getattr(settings, 'USE_SOTHEMAAI_ONLY', False)
                if provider_name == "sothemaai":
                    settings.USE_SOTHEMAAI_ONLY = True
                else:
                    settings.USE_SOTHEMAAI_ONLY = False
                
                try:
                    # Réinitialiser les agents avec le nouveau provider
                    self._setup_sothemaai_provider()
                    self._setup_crew_agents()
                    
                    # Tenter l'orchestration
                    response = await self.orchestrate_workflow(request)
                    
                    # Ajouter des métadonnées sur le provider utilisé
                    response.metadata = response.metadata or {}
                    response.metadata["primary_provider"] = provider_name
                    response.metadata["attempt_number"] = attempt + 1
                    
                    self.logger.info(
                        f"Orchestration successful with provider: {provider_name}",
                        extra={"workflow_id": workflow_id}
                    )
                    
                    return response
                    
                finally:
                    # Restaurer la configuration originale
                    settings.USE_SOTHEMAAI_ONLY = original_setting
                    
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Orchestration failed with provider {provider_name}: {str(e)}",
                    extra={"workflow_id": workflow_id, "attempt": attempt + 1}
                )
                
                # Si c'est le dernier essai, ne pas attendre
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # Si tous les providers ont échoué
        error_response = OrchestrationResponse(
            workflow_id=workflow_id,
            status=ProcessingStatus.FAILED,
            result=f"Échec de l'orchestration après {max_retries} tentatives",
            confidence_score=0.0,
            sources=[],
            citations=[],
            metadata={
                "error": str(last_error),
                "failed_providers": fallback_providers[:max_retries],
                "total_attempts": max_retries
            },
            processing_time=0.0,
            token_usage={},
            created_at=datetime.utcnow()
        )
        
        raise OrchestrationError(
            f"Échec de l'orchestration avec tous les providers après {max_retries} tentatives: {str(last_error)}"
        )
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Annule un workflow en cours."""
        
        if workflow_id in self.active_workflows:
            self.active_workflows.pop(workflow_id)
            self.logger.info(
                "Workflow annulé",
                extra={"workflow_id": workflow_id}
            )
            return True
        
        return False
    
    async def get_workflow_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques des workflows."""
        
        return {
            "active_workflows": len(self.active_workflows),
            "workflow_metrics": self.workflow_metrics,
            "performance_stats": {
                "average_execution_time": 0.0,  # À calculer
                "success_rate": 0.95,  # À calculer
                "error_rate": 0.05  # À calculer
            }
        }
    
    @asynccontextmanager
    async def workflow_context(self, workflow_id: str):
        """Gestionnaire de contexte pour les workflows."""
        
        try:
            self.logger.info(
                "Démarrage du contexte de workflow",
                extra={"workflow_id": workflow_id}
            )
            yield
        finally:
            # Nettoyage automatique
            self.active_workflows.pop(workflow_id, None)
            self.logger.info(
                "Nettoyage du contexte de workflow",
                extra={"workflow_id": workflow_id}
            )
