"""
Modèles Pydantic pour les interactions de chat et RAG.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class WorkflowType(str, Enum):
    """Types de workflow supportés"""
    SIMPLE_RAG = "simple_rag"
    COMPARATIVE_RAG = "comparative_rag"
    SUMMARIZATION = "summarization"
    ANALYSIS = "analysis"


class ConfidenceLevel(str, Enum):
    """Niveaux de confiance"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ChatRequest(BaseModel):
    """Requête de chat simple"""
    message: str = Field(..., description="Message/question de l'utilisateur", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="ID de session optionnel")
    max_documents: Optional[int] = Field(5, description="Nombre maximum de documents à récupérer", ge=1, le=20)
    include_validation: bool = Field(True, description="Inclure la validation par l'agent critic")
    context: Optional[str] = Field(None, description="Contexte additionnel", max_length=1000)
    user_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Préférences utilisateur")


class RAGRequest(BaseModel):
    """Requête RAG avancée"""
    query: str = Field(..., description="Requête de recherche", min_length=1, max_length=2000)
    max_documents: Optional[int] = Field(8, description="Nombre maximum de documents", ge=1, le=50)
    retrieval_strategy: str = Field("contextual", description="Stratégie de récupération")
    synthesis_style: str = Field("comprehensive", description="Style de synthèse")
    comparison_aspects: Optional[List[str]] = Field(None, description="Aspects à comparer")
    focus_areas: Optional[List[str]] = Field(None, description="Domaines de focus")
    include_citations: bool = Field(True, description="Inclure les citations")
    quality_threshold: float = Field(0.7, description="Seuil de qualité minimum", ge=0.0, le=1.0)


class WorkflowRequest(BaseModel):
    """Requête de workflow personnalisé"""
    workflow_type: WorkflowType = Field(..., description="Type de workflow à exécuter")
    query: Optional[str] = Field(None, description="Requête pour workflows de recherche")
    documents: Optional[List[Dict[str, Any]]] = Field(None, description="Documents pour workflows de traitement")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Paramètres spécifiques au workflow")
    priority: str = Field("normal", description="Priorité d'exécution", pattern="^(low|normal|high|urgent)$")
    timeout: Optional[int] = Field(300, description="Timeout en secondes", ge=10, le=3600)


class SourceDocument(BaseModel):
    """Document source utilisé dans une réponse"""
    content: str = Field(..., description="Contenu du document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées du document")
    score: Optional[float] = Field(None, description="Score de pertinence", ge=0.0, le=1.0)
    source: Optional[str] = Field(None, description="Source du document")
    timestamp: Optional[datetime] = Field(None, description="Timestamp du document")


class ChatResponse(BaseModel):
    """Réponse de chat"""
    response: str = Field(..., description="Réponse générée")
    sources: List[SourceDocument] = Field(default_factory=list, description="Sources utilisées")
    confidence_level: Union[ConfidenceLevel, float] = Field(..., description="Niveau de confiance")
    execution_time: float = Field(..., description="Temps d'exécution en secondes", ge=0)
    workflow_id: Optional[str] = Field(None, description="ID du workflow exécuté")
    citations: Optional[List[str]] = Field(default_factory=list, description="Citations incluses")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la réponse")


class RAGResponse(BaseModel):
    """Réponse RAG détaillée"""
    answer: str = Field(..., description="Réponse générée")
    sources: List[SourceDocument] = Field(..., description="Documents sources")
    retrieval_metrics: Dict[str, Any] = Field(..., description="Métriques de récupération")
    synthesis_metrics: Dict[str, Any] = Field(..., description="Métriques de synthèse")
    validation_results: Optional[Dict[str, Any]] = Field(None, description="Résultats de validation")
    workflow_details: Dict[str, Any] = Field(..., description="Détails du workflow")
    performance_metrics: Dict[str, float] = Field(..., description="Métriques de performance")


class ChatMessage(BaseModel):
    """Message dans une conversation"""
    message_id: str = Field(..., description="ID unique du message")
    content: str = Field(..., description="Contenu du message")
    role: str = Field(..., description="Rôle (user/assistant)", pattern="^(user|assistant|system)$")
    timestamp: datetime = Field(..., description="Timestamp du message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées du message")
    sources: Optional[List[SourceDocument]] = Field(None, description="Sources pour réponses assistant")
    feedback: Optional[Dict[str, Any]] = Field(None, description="Feedback utilisateur")


class ChatSession(BaseModel):
    """Session de chat"""
    session_id: str = Field(..., description="ID unique de la session")
    user_id: str = Field(..., description="ID de l'utilisateur")
    session_name: str = Field(..., description="Nom de la session")
    created_at: datetime = Field(..., description="Date de création")
    last_activity: Optional[datetime] = Field(None, description="Dernière activité")
    messages: List[ChatMessage] = Field(default_factory=list, description="Messages de la session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées de session")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Paramètres de session")
    is_active: bool = Field(True, description="Session active")


class WorkflowStatus(str, Enum):
    """Statuts de workflow"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowResult(BaseModel):
    """Résultat d'exécution de workflow"""
    workflow_id: str = Field(..., description="ID du workflow")
    workflow_type: WorkflowType = Field(..., description="Type de workflow")
    status: WorkflowStatus = Field(..., description="Statut d'exécution")
    start_time: datetime = Field(..., description="Heure de début")
    end_time: Optional[datetime] = Field(None, description="Heure de fin")
    execution_duration: Optional[float] = Field(None, description="Durée d'exécution")
    result: Optional[Dict[str, Any]] = Field(None, description="Résultat du workflow")
    error: Optional[str] = Field(None, description="Message d'erreur si échec")
    steps: Dict[str, Any] = Field(default_factory=dict, description="Détails des étapes")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Métriques d'exécution")
    user_id: str = Field(..., description="ID de l'utilisateur")


class FeedbackRequest(BaseModel):
    """Requête de feedback utilisateur"""
    message_id: str = Field(..., description="ID du message concerné")
    rating: int = Field(..., description="Note de 1 à 5", ge=1, le=5)
    feedback_type: str = Field(..., description="Type de feedback", pattern="^(quality|relevance|accuracy|speed)$")
    comment: Optional[str] = Field(None, description="Commentaire optionnel", max_length=1000)
    suggestions: Optional[List[str]] = Field(None, description="Suggestions d'amélioration")
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentMetrics(BaseModel):
    """Métriques d'un agent"""
    agent_type: str = Field(..., description="Type d'agent")
    total_executions: int = Field(..., description="Nombre total d'exécutions")
    successful_executions: int = Field(..., description="Exécutions réussies")
    avg_execution_time: float = Field(..., description="Temps moyen d'exécution")
    avg_quality_score: float = Field(..., description="Score qualité moyen")
    last_execution: Optional[datetime] = Field(None, description="Dernière exécution")
    error_rate: float = Field(..., description="Taux d'erreur", ge=0.0, le=1.0)
    status: str = Field(..., description="Statut de l'agent")


class PlatformMetrics(BaseModel):
    """Métriques globales de la plateforme"""
    total_requests: int = Field(..., description="Total des requêtes")
    active_sessions: int = Field(..., description="Sessions actives")
    avg_response_time: float = Field(..., description="Temps de réponse moyen")
    success_rate: float = Field(..., description="Taux de succès")
    agents_status: Dict[str, AgentMetrics] = Field(..., description="Statut des agents")
    vector_store_status: Dict[str, Any] = Field(..., description="Statut du vector store")
    llm_status: Dict[str, Any] = Field(..., description="Statut du LLM")
    timestamp: datetime = Field(default_factory=datetime.now)


# Modèles de configuration

class AgentConfig(BaseModel):
    """Configuration d'un agent"""
    agent_type: str = Field(..., description="Type d'agent")
    max_iterations: int = Field(3, description="Nombre max d'itérations", ge=1, le=10)
    max_execution_time: int = Field(60, description="Temps max d'exécution", ge=10, le=600)
    verbose: bool = Field(True, description="Mode verbeux")
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)


class WorkflowConfig(BaseModel):
    """Configuration de workflow"""
    workflow_type: WorkflowType = Field(..., description="Type de workflow")
    agents_config: Dict[str, AgentConfig] = Field(..., description="Configuration des agents")
    parallel_execution: bool = Field(False, description="Exécution parallèle")
    validation_required: bool = Field(True, description="Validation requise")
    quality_threshold: float = Field(0.7, description="Seuil de qualité", ge=0.0, le=1.0)
    retry_on_failure: bool = Field(True, description="Retry en cas d'échec")
    max_retries: int = Field(2, description="Nombre max de retries", ge=0, le=5)
