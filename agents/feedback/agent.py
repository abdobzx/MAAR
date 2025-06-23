"""
Agent de feedback et de mémoire pour collecter les retours utilisateurs 
et gérer la mémoire conversationnelle du système RAG.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import FeedbackError, MemoryError, ValidationError
from core.logging import get_logger
from core.models import (
    SearchQuery, SearchResult, FeedbackEntry, FeedbackType,
    MemoryEntry, MemoryType, ConversationContext, UserPreference,
    LearningInsight, ProcessingStatus
)
from database.manager import DatabaseManager
from database.models import (
    Feedback, Query, User, Organization, Document, 
    DocumentChunk, AgentTask, Metric
)


class FeedbackSentiment(str, Enum):
    """Sentiment du feedback utilisateur."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class MemoryPriority(str, Enum):
    """Priorité des entrées mémoire."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"


class LearningPattern(BaseModel):
    """Pattern d'apprentissage détecté."""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    confidence: float
    examples: List[str]
    recommendations: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationMemory(BaseModel):
    """Mémoire conversationnelle."""
    conversation_id: str
    user_id: str
    organization_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class FeedbackMemoryAgent:
    """Agent de feedback et de mémoire pour l'amélioration continue du système."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.db_manager = DatabaseManager()
        
        # Caches mémoire pour les performances
        self.conversation_cache: Dict[str, ConversationMemory] = {}
        self.user_preferences_cache: Dict[str, Dict[str, Any]] = {}
        self.learning_patterns_cache: Dict[str, LearningPattern] = {}
        
        # Files pour le traitement asynchrone
        self.feedback_queue = deque()
        self.memory_update_queue = deque()
        
        # Configuration de la mémoire
        self.max_conversation_length = 50
        self.memory_retention_days = 30
        self.learning_threshold = 0.7
        
        # Métriques de performance
        self.feedback_metrics = defaultdict(int)
        self.memory_metrics = defaultdict(float)
        
        # Démarrage des tâches de maintenance
        asyncio.create_task(self._start_background_tasks())
    
    async def collect_feedback(
        self,
        feedback_entry: FeedbackEntry
    ) -> Dict[str, Any]:
        """Collecte et traite un feedback utilisateur."""
        
        try:
            self.logger.info(
                "Collecte de feedback utilisateur",
                extra={
                    "user_id": feedback_entry.user_id,
                    "feedback_type": feedback_entry.feedback_type,
                    "query_id": feedback_entry.query_id
                }
            )
            
            # Validation du feedback
            await self._validate_feedback(feedback_entry)
            
            # Analyse de sentiment
            sentiment = await self._analyze_sentiment(feedback_entry.content)
            
            # Stockage en base de données
            feedback_id = await self._store_feedback(feedback_entry, sentiment)
            
            # Traitement immédiat pour les feedbacks critiques
            if feedback_entry.rating <= 2 or sentiment == FeedbackSentiment.NEGATIVE:
                await self._process_critical_feedback(feedback_entry, sentiment)
            
            # Ajout à la queue pour traitement asynchrone
            self.feedback_queue.append({
                "feedback_id": feedback_id,
                "feedback_entry": feedback_entry,
                "sentiment": sentiment,
                "timestamp": datetime.utcnow()
            })
            
            # Mise à jour des métriques
            self.feedback_metrics[f"{feedback_entry.feedback_type}_{sentiment}"] += 1
            self.feedback_metrics["total_feedback"] += 1
            
            # Apprentissage et amélioration
            await self._extract_learning_insights(feedback_entry, sentiment)
            
            self.logger.info(
                "Feedback collecté avec succès",
                extra={
                    "feedback_id": feedback_id,
                    "sentiment": sentiment
                }
            )
            
            return {
                "feedback_id": feedback_id,
                "status": "processed",
                "sentiment": sentiment,
                "learning_insights": await self._get_relevant_insights(feedback_entry)
            }
            
        except Exception as e:
            self.logger.error(
                "Erreur lors de la collecte de feedback",
                extra={
                    "user_id": feedback_entry.user_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise FeedbackError(f"Impossible de traiter le feedback: {str(e)}")
    
    async def store_conversation_memory(
        self,
        user_id: str,
        organization_id: str,
        query: SearchQuery,
        result: SearchResult,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Stocke une interaction dans la mémoire conversationnelle."""
        
        try:
            conversation_id = f"{user_id}_{datetime.utcnow().date()}"
            
            # Récupération ou création de la conversation
            if conversation_id in self.conversation_cache:
                conversation = self.conversation_cache[conversation_id]
            else:
                conversation = ConversationMemory(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    organization_id=organization_id,
                    expires_at=datetime.utcnow() + timedelta(days=self.memory_retention_days)
                )
            
            # Ajout de l'interaction
            interaction = {
                "timestamp": datetime.utcnow().isoformat(),
                "query": query.dict(),
                "result": result.dict(),
                "context": context or {},
                "interaction_id": str(uuid.uuid4())
            }
            
            conversation.messages.append(interaction)
            conversation.updated_at = datetime.utcnow()
            
            # Limitation de la taille de la conversation
            if len(conversation.messages) > self.max_conversation_length:
                conversation.messages = conversation.messages[-self.max_conversation_length:]
            
            # Mise à jour du cache et de la base
            self.conversation_cache[conversation_id] = conversation
            await self._persist_conversation_memory(conversation)
            
            # Extraction de préférences utilisateur
            await self._extract_user_preferences(user_id, query, result)
            
            self.logger.info(
                "Mémoire conversationnelle mise à jour",
                extra={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "messages_count": len(conversation.messages)
                }
            )
            
            return conversation_id
            
        except Exception as e:
            self.logger.error(
                "Erreur lors du stockage en mémoire",
                extra={
                    "user_id": user_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise MemoryError(f"Impossible de stocker la mémoire: {str(e)}")
    
    async def get_conversation_context(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> ConversationContext:
        """Récupère le contexte conversationnel pour un utilisateur."""
        
        try:
            if not conversation_id:
                conversation_id = f"{user_id}_{datetime.utcnow().date()}"
            
            # Récupération de la conversation
            conversation = None
            if conversation_id in self.conversation_cache:
                conversation = self.conversation_cache[conversation_id]
            else:
                conversation = await self._load_conversation_memory(conversation_id)
            
            if not conversation:
                return ConversationContext(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    recent_queries=[],
                    preferences={},
                    context={}
                )
            
            # Extraction des requêtes récentes
            recent_queries = []
            for message in conversation.messages[-10:]:  # 10 dernières interactions
                if "query" in message:
                    recent_queries.append(SearchQuery(**message["query"]))
            
            # Récupération des préférences utilisateur
            preferences = await self._get_user_preferences(user_id)
            
            # Construction du contexte
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                recent_queries=recent_queries,
                preferences=preferences,
                context=conversation.context,
                last_interaction=conversation.updated_at
            )
            
            return context
            
        except Exception as e:
            self.logger.error(
                "Erreur lors de la récupération du contexte",
                extra={
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise MemoryError(f"Impossible de récupérer le contexte: {str(e)}")
    
    async def get_learning_insights(
        self,
        organization_id: str,
        timeframe_days: int = 7
    ) -> List[LearningInsight]:
        """Génère des insights d'apprentissage basés sur les feedbacks et interactions."""
        
        try:
            insights = []
            
            # Analyse des patterns de feedback
            feedback_patterns = await self._analyze_feedback_patterns(
                organization_id, timeframe_days
            )
            
            # Analyse des patterns de requêtes
            query_patterns = await self._analyze_query_patterns(
                organization_id, timeframe_days
            )
            
            # Analyse de performance
            performance_insights = await self._analyze_performance_patterns(
                organization_id, timeframe_days
            )
            
            # Génération des insights
            for pattern in feedback_patterns:
                if pattern.confidence >= self.learning_threshold:
                    insight = LearningInsight(
                        insight_id=str(uuid.uuid4()),
                        type="feedback_analysis",
                        title=f"Pattern de feedback détecté: {pattern.description}",
                        description=f"Fréquence: {pattern.frequency}, Confiance: {pattern.confidence:.2f}",
                        recommendations=pattern.recommendations,
                        confidence_score=pattern.confidence,
                        evidence=pattern.examples,
                        priority=self._calculate_insight_priority(pattern)
                    )
                    insights.append(insight)
            
            for pattern in query_patterns:
                if pattern.confidence >= self.learning_threshold:
                    insight = LearningInsight(
                        insight_id=str(uuid.uuid4()),
                        type="query_analysis",
                        title=f"Pattern de requête identifié: {pattern.description}",
                        description=f"Fréquence: {pattern.frequency}, Confiance: {pattern.confidence:.2f}",
                        recommendations=pattern.recommendations,
                        confidence_score=pattern.confidence,
                        evidence=pattern.examples,
                        priority=self._calculate_insight_priority(pattern)
                    )
                    insights.append(insight)
            
            # Tri par priorité et confiance
            insights.sort(key=lambda x: (x.priority, x.confidence_score), reverse=True)
            
            self.logger.info(
                "Insights d'apprentissage générés",
                extra={
                    "organization_id": organization_id,
                    "insights_count": len(insights),
                    "timeframe_days": timeframe_days
                }
            )
            
            return insights
            
        except Exception as e:
            self.logger.error(
                "Erreur lors de la génération d'insights",
                extra={
                    "organization_id": organization_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise MemoryError(f"Impossible de générer les insights: {str(e)}")
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: UserPreference
    ) -> bool:
        """Met à jour les préférences utilisateur."""
        
        try:
            # Validation des préférences
            if not preferences.preference_data:
                raise ValidationError("Les données de préférence sont requises")
            
            # Mise à jour du cache
            self.user_preferences_cache[user_id] = preferences.preference_data
            
            # Persistance en base
            async with self.db_manager.get_session() as session:
                # Recherche de l'utilisateur
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    raise ValidationError(f"Utilisateur non trouvé: {user_id}")
                
                # Mise à jour des préférences
                if not user.preferences:
                    user.preferences = {}
                
                user.preferences.update(preferences.preference_data)
                user.updated_at = datetime.utcnow()
                
                await session.commit()
            
            self.logger.info(
                "Préférences utilisateur mises à jour",
                extra={
                    "user_id": user_id,
                    "preferences_count": len(preferences.preference_data)
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Erreur lors de la mise à jour des préférences",
                extra={
                    "user_id": user_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return False
    
    # Méthodes privées
    
    async def _validate_feedback(self, feedback: FeedbackEntry):
        """Valide un feedback avant traitement."""
        
        if not feedback.user_id:
            raise ValidationError("L'ID utilisateur est requis")
        
        if feedback.rating < 1 or feedback.rating > 5:
            raise ValidationError("La note doit être entre 1 et 5")
        
        if not feedback.content.strip():
            raise ValidationError("Le contenu du feedback ne peut pas être vide")
    
    async def _analyze_sentiment(self, content: str) -> FeedbackSentiment:
        """Analyse le sentiment d'un feedback (version simplifiée)."""
        
        # Mots-clés pour l'analyse de sentiment
        positive_words = {
            "excellent", "parfait", "génial", "super", "merci", 
            "satisfait", "content", "bon", "bien", "utile",
            "précis", "rapide", "efficace", "pertinent"
        }
        
        negative_words = {
            "mauvais", "nul", "terrible", "horrible", "erreur",
            "lent", "inutile", "faux", "incorrect", "décevant",
            "frustrant", "problème", "bug", "cassé"
        }
        
        content_lower = content.lower()
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            return FeedbackSentiment.POSITIVE
        elif negative_count > positive_count:
            return FeedbackSentiment.NEGATIVE
        elif positive_count == negative_count and positive_count > 0:
            return FeedbackSentiment.MIXED
        else:
            return FeedbackSentiment.NEUTRAL
    
    async def _store_feedback(
        self, 
        feedback: FeedbackEntry, 
        sentiment: FeedbackSentiment
    ) -> str:
        """Stocke le feedback en base de données."""
        
        async with self.db_manager.get_session() as session:
            db_feedback = Feedback(
                user_id=feedback.user_id,
                organization_id=feedback.organization_id,
                query_id=feedback.query_id,
                feedback_type=feedback.feedback_type,
                rating=feedback.rating,
                content=feedback.content,
                metadata={
                    "sentiment": sentiment,
                    "tags": feedback.tags,
                    "context": feedback.context
                }
            )
            
            session.add(db_feedback)
            await session.commit()
            await session.refresh(db_feedback)
            
            return str(db_feedback.id)
    
    async def _process_critical_feedback(
        self, 
        feedback: FeedbackEntry, 
        sentiment: FeedbackSentiment
    ):
        """Traite immédiatement les feedbacks critiques."""
        
        self.logger.warning(
            "Feedback critique détecté",
            extra={
                "user_id": feedback.user_id,
                "rating": feedback.rating,
                "sentiment": sentiment,
                "content": feedback.content[:100]
            }
        )
        
        # Ici, on pourrait déclencher des alertes, notifications, etc.
        # Par exemple: envoyer un email à l'équipe support
    
    async def _extract_learning_insights(
        self, 
        feedback: FeedbackEntry, 
        sentiment: FeedbackSentiment
    ):
        """Extrait des insights d'apprentissage du feedback."""
        
        # Analyse des patterns récurrents
        pattern_key = f"{feedback.feedback_type}_{sentiment}"
        
        if pattern_key not in self.learning_patterns_cache:
            self.learning_patterns_cache[pattern_key] = LearningPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type=pattern_key,
                description=f"Feedback {feedback.feedback_type} avec sentiment {sentiment}",
                frequency=1,
                confidence=0.1,
                examples=[feedback.content[:100]],
                recommendations=[]
            )
        else:
            pattern = self.learning_patterns_cache[pattern_key]
            pattern.frequency += 1
            pattern.confidence = min(1.0, pattern.confidence + 0.1)
            if len(pattern.examples) < 5:
                pattern.examples.append(feedback.content[:100])
    
    async def _get_relevant_insights(self, feedback: FeedbackEntry) -> List[str]:
        """Récupère les insights pertinents pour un feedback."""
        
        relevant_insights = []
        
        for pattern in self.learning_patterns_cache.values():
            if (pattern.pattern_type.startswith(feedback.feedback_type) and 
                pattern.confidence >= 0.5):
                relevant_insights.append(pattern.description)
        
        return relevant_insights
    
    async def _persist_conversation_memory(self, conversation: ConversationMemory):
        """Persiste la mémoire conversationnelle en base."""
        
        # Ici, on stockerait dans une table dédiée ou un cache Redis
        # Pour la simplicité, on utilise les métadonnées des requêtes
        pass
    
    async def _load_conversation_memory(self, conversation_id: str) -> Optional[ConversationMemory]:
        """Charge la mémoire conversationnelle depuis la base."""
        
        # Simulation du chargement
        return None
    
    async def _extract_user_preferences(
        self, 
        user_id: str, 
        query: SearchQuery, 
        result: SearchResult
    ):
        """Extrait les préférences utilisateur des interactions."""
        
        if user_id not in self.user_preferences_cache:
            self.user_preferences_cache[user_id] = {}
        
        preferences = self.user_preferences_cache[user_id]
        
        # Analyse des patterns de requête
        if "language" not in preferences:
            preferences["language"] = query.language or "fr"
        
        if "domains" not in preferences:
            preferences["domains"] = []
        
        # Extraction des domaines préférés (simulation)
        if hasattr(query, 'metadata') and query.metadata:
            domain = query.metadata.get('domain')
            if domain and domain not in preferences["domains"]:
                preferences["domains"].append(domain)
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Récupère les préférences utilisateur."""
        
        if user_id in self.user_preferences_cache:
            return self.user_preferences_cache[user_id]
        
        # Chargement depuis la base
        async with self.db_manager.get_session() as session:
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user and user.preferences:
                self.user_preferences_cache[user_id] = user.preferences
                return user.preferences
        
        return {}
    
    async def _analyze_feedback_patterns(
        self, 
        organization_id: str, 
        timeframe_days: int
    ) -> List[LearningPattern]:
        """Analyse les patterns de feedback."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        async with self.db_manager.get_session() as session:
            # Récupération des feedbacks récents
            feedback_result = await session.execute(
                select(Feedback)
                .where(
                    and_(
                        Feedback.organization_id == organization_id,
                        Feedback.created_at >= cutoff_date
                    )
                )
            )
            feedbacks = feedback_result.scalars().all()
            
            # Analyse des patterns
            patterns = []
            feedback_by_type = defaultdict(list)
            
            for feedback in feedbacks:
                feedback_by_type[feedback.feedback_type].append(feedback)
            
            for feedback_type, type_feedbacks in feedback_by_type.items():
                if len(type_feedbacks) >= 3:  # Minimum pour détecter un pattern
                    avg_rating = np.mean([f.rating for f in type_feedbacks])
                    
                    pattern = LearningPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type=f"feedback_{feedback_type}",
                        description=f"Pattern de feedback {feedback_type}",
                        frequency=len(type_feedbacks),
                        confidence=min(1.0, len(type_feedbacks) / 10),
                        examples=[f.content[:100] for f in type_feedbacks[:3]],
                        recommendations=self._generate_feedback_recommendations(
                            feedback_type, avg_rating
                        )
                    )
                    patterns.append(pattern)
            
            return patterns
    
    async def _analyze_query_patterns(
        self, 
        organization_id: str, 
        timeframe_days: int
    ) -> List[LearningPattern]:
        """Analyse les patterns de requêtes."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        async with self.db_manager.get_session() as session:
            # Récupération des requêtes récentes
            query_result = await session.execute(
                select(Query)
                .where(
                    and_(
                        Query.organization_id == organization_id,
                        Query.created_at >= cutoff_date
                    )
                )
            )
            queries = query_result.scalars().all()
            
            # Analyse des patterns de mots-clés
            patterns = []
            query_texts = [q.query_text for q in queries if q.query_text]
            
            # Simulation d'analyse de patterns
            if len(query_texts) >= 5:
                pattern = LearningPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type="query_frequency",
                    description="Patterns de requêtes fréquentes",
                    frequency=len(query_texts),
                    confidence=0.8,
                    examples=query_texts[:3],
                    recommendations=[
                        "Optimiser les réponses pour ces types de requêtes",
                        "Créer du contenu spécialisé",
                        "Améliorer la vectorisation pour ces sujets"
                    ]
                )
                patterns.append(pattern)
            
            return patterns
    
    async def _analyze_performance_patterns(
        self, 
        organization_id: str, 
        timeframe_days: int
    ) -> List[LearningPattern]:
        """Analyse les patterns de performance."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
        
        async with self.db_manager.get_session() as session:
            # Récupération des métriques de performance
            metrics_result = await session.execute(
                select(Metric)
                .where(
                    and_(
                        Metric.organization_id == organization_id,
                        Metric.created_at >= cutoff_date
                    )
                )
            )
            metrics = metrics_result.scalars().all()
            
            patterns = []
            
            # Analyse des temps de réponse
            response_times = [
                m.value for m in metrics 
                if m.metric_name == "response_time" and m.value is not None
            ]
            
            if len(response_times) >= 10:
                avg_response_time = np.mean(response_times)
                if avg_response_time > 5.0:  # Plus de 5 secondes
                    pattern = LearningPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type="performance_slow",
                        description="Temps de réponse élevé détecté",
                        frequency=len(response_times),
                        confidence=0.9,
                        examples=[f"{t:.2f}s" for t in response_times[:3]],
                        recommendations=[
                            "Optimiser les requêtes de base de données",
                            "Améliorer le cache des embeddings",
                            "Réduire la taille des chunks",
                            "Optimiser les appels LLM"
                        ]
                    )
                    patterns.append(pattern)
            
            return patterns
    
    def _generate_feedback_recommendations(
        self, 
        feedback_type: str, 
        avg_rating: float
    ) -> List[str]:
        """Génère des recommandations basées sur les patterns de feedback."""
        
        recommendations = []
        
        if avg_rating < 3.0:
            recommendations.extend([
                f"Améliorer la qualité des réponses pour {feedback_type}",
                "Réviser les prompts et templates",
                "Augmenter la précision de la recherche"
            ])
        elif avg_rating >= 4.0:
            recommendations.extend([
                f"Maintenir la qualité pour {feedback_type}",
                "Utiliser comme modèle pour d'autres types"
            ])
        
        return recommendations
    
    def _calculate_insight_priority(self, pattern: LearningPattern) -> str:
        """Calcule la priorité d'un insight."""
        
        if pattern.confidence >= 0.9 and pattern.frequency >= 10:
            return "critical"
        elif pattern.confidence >= 0.7 and pattern.frequency >= 5:
            return "high"
        elif pattern.confidence >= 0.5:
            return "medium"
        else:
            return "low"
    
    async def _start_background_tasks(self):
        """Démarre les tâches de maintenance en arrière-plan."""
        
        # Traitement des feedbacks en queue
        asyncio.create_task(self._process_feedback_queue())
        
        # Nettoyage de la mémoire
        asyncio.create_task(self._cleanup_expired_memory())
        
        # Calcul des métriques
        asyncio.create_task(self._calculate_periodic_metrics())
    
    async def _process_feedback_queue(self):
        """Traite la queue des feedbacks de manière asynchrone."""
        
        while True:
            try:
                if self.feedback_queue:
                    feedback_data = self.feedback_queue.popleft()
                    # Traitement avancé du feedback
                    await self._advanced_feedback_processing(feedback_data)
                else:
                    await asyncio.sleep(5)  # Attente avant la prochaine vérification
            except Exception as e:
                self.logger.error(
                    "Erreur dans le traitement de la queue feedback",
                    extra={"error": str(e)},
                    exc_info=True
                )
                await asyncio.sleep(10)
    
    async def _cleanup_expired_memory(self):
        """Nettoie la mémoire expirée."""
        
        while True:
            try:
                current_time = datetime.utcnow()
                expired_conversations = []
                
                for conv_id, conversation in self.conversation_cache.items():
                    if (conversation.expires_at and 
                        conversation.expires_at < current_time):
                        expired_conversations.append(conv_id)
                
                for conv_id in expired_conversations:
                    self.conversation_cache.pop(conv_id, None)
                    self.logger.info(
                        "Conversation expirée nettoyée",
                        extra={"conversation_id": conv_id}
                    )
                
                await asyncio.sleep(3600)  # Nettoyage chaque heure
                
            except Exception as e:
                self.logger.error(
                    "Erreur lors du nettoyage mémoire",
                    extra={"error": str(e)},
                    exc_info=True
                )
                await asyncio.sleep(3600)
    
    async def _calculate_periodic_metrics(self):
        """Calcule les métriques de performance périodiquement."""
        
        while True:
            try:
                # Calcul des métriques de feedback
                total_feedback = self.feedback_metrics.get("total_feedback", 0)
                if total_feedback > 0:
                    positive_feedback = sum(
                        count for key, count in self.feedback_metrics.items()
                        if "positive" in key
                    )
                    satisfaction_rate = positive_feedback / total_feedback
                    self.memory_metrics["satisfaction_rate"] = satisfaction_rate
                
                # Calcul des métriques de mémoire
                self.memory_metrics["active_conversations"] = len(self.conversation_cache)
                self.memory_metrics["cached_preferences"] = len(self.user_preferences_cache)
                self.memory_metrics["learning_patterns"] = len(self.learning_patterns_cache)
                
                await asyncio.sleep(300)  # Calcul toutes les 5 minutes
                
            except Exception as e:
                self.logger.error(
                    "Erreur lors du calcul des métriques",
                    extra={"error": str(e)},
                    exc_info=True
                )
                await asyncio.sleep(300)
    
    async def _advanced_feedback_processing(self, feedback_data: Dict[str, Any]):
        """Traitement avancé d'un feedback."""
        
        # Ici on pourrait implémenter:
        # - Analyse NLP avancée
        # - Détection d'anomalies
        # - Corrélation avec d'autres métriques
        # - Génération d'actions automatiques
        pass
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques de mémoire et feedback."""
        
        return {
            "feedback_metrics": dict(self.feedback_metrics),
            "memory_metrics": dict(self.memory_metrics),
            "cache_stats": {
                "conversations": len(self.conversation_cache),
                "preferences": len(self.user_preferences_cache),
                "patterns": len(self.learning_patterns_cache)
            },
            "queue_stats": {
                "feedback_queue_size": len(self.feedback_queue),
                "memory_update_queue_size": len(self.memory_update_queue)
            }
        }
