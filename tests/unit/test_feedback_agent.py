"""
Tests unitaires pour l'agent de feedback et mémoire.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import uuid

from agents.feedback.agent import FeedbackMemoryAgent
from core.models import FeedbackEntry, LearningInsight, UserPreference
from core.exceptions import ValidationError, MemoryError


class TestFeedbackMemoryAgent:
    """Tests pour l'agent de feedback et mémoire."""
    
    @pytest.fixture
    async def feedback_agent(self, db_session, mock_redis_client):
        """Instance de l'agent de feedback pour les tests."""
        with patch('agents.feedback.agent.redis.Redis', return_value=mock_redis_client):
            agent = FeedbackMemoryAgent(db_session=db_session)
            yield agent
    
    @pytest.fixture
    def sample_feedback(self, test_user, test_organization):
        """Feedback de test."""
        return FeedbackEntry(
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            feedback_type="quality",
            rating=4,
            content="Cette réponse était très utile et précise.",
            context={
                "query": "Quelle est la politique de congés?",
                "response_id": "resp-123",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def test_store_feedback_success(self, feedback_agent, sample_feedback):
        """Test du stockage réussi d'un feedback."""
        
        feedback_id = await feedback_agent.store_feedback(sample_feedback)
        
        assert feedback_id is not None
        assert isinstance(feedback_id, str)
    
    async def test_store_feedback_validation_error(self, feedback_agent, test_user, test_organization):
        """Test de validation d'erreur lors du stockage de feedback."""
        
        # Feedback invalide (rating hors limite)
        invalid_feedback = FeedbackEntry(
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            feedback_type="quality",
            rating=6,  # Invalide (> 5)
            content="Feedback invalide"
        )
        
        with pytest.raises(ValidationError):
            await feedback_agent.store_feedback(invalid_feedback)
    
    async def test_analyze_sentiment_positive(self, feedback_agent):
        """Test d'analyse de sentiment positif."""
        
        content = "Cette réponse était excellente et très utile!"
        
        sentiment = await feedback_agent._analyze_sentiment(content)
        
        assert sentiment.sentiment == "positive"
        assert sentiment.confidence > 0.5
    
    async def test_analyze_sentiment_negative(self, feedback_agent):
        """Test d'analyse de sentiment négatif."""
        
        content = "Cette réponse était incorrecte et inutile."
        
        sentiment = await feedback_agent._analyze_sentiment(content)
        
        assert sentiment.sentiment == "negative"
        assert sentiment.confidence > 0.5
    
    async def test_analyze_sentiment_neutral(self, feedback_agent):
        """Test d'analyse de sentiment neutre."""
        
        content = "C'est une réponse standard."
        
        sentiment = await feedback_agent._analyze_sentiment(content)
        
        assert sentiment.sentiment == "neutral"
    
    async def test_get_learning_insights(self, feedback_agent, test_organization):
        """Test de génération d'insights d'apprentissage."""
        
        # Mock des patterns de feedback
        with patch.object(feedback_agent, '_analyze_feedback_patterns') as mock_feedback, \
             patch.object(feedback_agent, '_analyze_query_patterns') as mock_query, \
             patch.object(feedback_agent, '_analyze_performance_patterns') as mock_perf:
            
            mock_feedback.return_value = [
                MagicMock(
                    confidence=0.8,
                    pattern_type="feedback_quality",
                    description="Pattern de qualité",
                    frequency=10,
                    recommendations=["Améliorer la précision"]
                )
            ]
            mock_query.return_value = []
            mock_perf.return_value = []
            
            insights = await feedback_agent.get_learning_insights(
                test_organization["organization_id"], 
                timeframe_days=7
            )
            
            assert len(insights) > 0
            assert isinstance(insights[0], LearningInsight)
            assert insights[0].type == "feedback_analysis"
    
    async def test_update_user_preferences(self, feedback_agent, test_user):
        """Test de mise à jour des préférences utilisateur."""
        
        preferences = UserPreference(
            user_id=test_user["user_id"],
            language="fr",
            response_length="detailed",
            topics_of_interest=["technologie", "politique"],
            preferred_sources=["documents officiels"]
        )
        
        result = await feedback_agent.update_user_preferences(
            test_user["user_id"], 
            preferences
        )
        
        assert result is True
    
    async def test_get_user_preferences(self, feedback_agent, test_user):
        """Test de récupération des préférences utilisateur."""
        
        # Mock du cache Redis
        with patch.object(feedback_agent, 'redis_client') as mock_redis:
            mock_redis.get.return_value = '{"language": "fr", "response_length": "concise"}'
            
            preferences = await feedback_agent._get_user_preferences(test_user["user_id"])
            
            assert preferences["language"] == "fr"
            assert preferences["response_length"] == "concise"
    
    async def test_store_interaction_memory(self, feedback_agent, test_user, test_organization):
        """Test de stockage de la mémoire d'interaction."""
        
        interaction = {
            "user_id": test_user["user_id"],
            "organization_id": test_organization["organization_id"],
            "query": "Comment utiliser le système?",
            "response": "Voici comment utiliser le système...",
            "timestamp": datetime.utcnow(),
            "context": {"session_id": "session-123"}
        }
        
        result = await feedback_agent.store_interaction_memory(interaction)
        
        assert result is True
    
    async def test_analyze_feedback_patterns(self, feedback_agent, test_organization):
        """Test d'analyse des patterns de feedback."""
        
        # Mock de la session de base de données
        with patch.object(feedback_agent.db_manager, 'get_session') as mock_session:
            mock_feedback_obj = MagicMock()
            mock_feedback_obj.feedback_type = "quality"
            mock_feedback_obj.rating = 4
            mock_feedback_obj.content = "Bonne réponse"
            
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = [
                mock_feedback_obj, mock_feedback_obj, mock_feedback_obj
            ]
            
            patterns = await feedback_agent._analyze_feedback_patterns(
                test_organization["organization_id"], 
                timeframe_days=7
            )
            
            assert len(patterns) > 0
            assert patterns[0].pattern_type == "feedback_quality"
    
    async def test_analyze_query_patterns(self, feedback_agent, test_organization):
        """Test d'analyse des patterns de requêtes."""
        
        with patch.object(feedback_agent.db_manager, 'get_session') as mock_session:
            mock_query_obj = MagicMock()
            mock_query_obj.query_text = "Comment configurer le système?"
            
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = [
                mock_query_obj, mock_query_obj, mock_query_obj, mock_query_obj, mock_query_obj
            ]
            
            patterns = await feedback_agent._analyze_query_patterns(
                test_organization["organization_id"],
                timeframe_days=7
            )
            
            assert len(patterns) > 0
            assert patterns[0].pattern_type == "query_frequency"
    
    async def test_analyze_performance_patterns(self, feedback_agent, test_organization):
        """Test d'analyse des patterns de performance."""
        
        with patch.object(feedback_agent.db_manager, 'get_session') as mock_session:
            # Mock de métriques avec temps de réponse élevé
            mock_metrics = []
            for _ in range(10):
                mock_metric = MagicMock()
                mock_metric.metric_name = "response_time"
                mock_metric.value = 6.0  # 6 secondes (élevé)
                mock_metrics.append(mock_metric)
            
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = mock_metrics
            
            patterns = await feedback_agent._analyze_performance_patterns(
                test_organization["organization_id"],
                timeframe_days=7
            )
            
            assert len(patterns) > 0
            assert patterns[0].pattern_type == "performance_slow"
    
    async def test_process_critical_feedback(self, feedback_agent, test_user, test_organization):
        """Test de traitement de feedback critique."""
        
        critical_feedback = FeedbackEntry(
            user_id=test_user["user_id"],
            organization_id=test_organization["organization_id"],
            feedback_type="accuracy",
            rating=1,  # Très mauvais
            content="Cette réponse était complètement incorrecte et dangereuse!"
        )
        
        sentiment = MagicMock()
        sentiment.sentiment = "negative"
        sentiment.confidence = 0.9
        
        # Mock de la notification
        with patch.object(feedback_agent, '_send_alert_notification') as mock_alert:
            await feedback_agent._process_critical_feedback(critical_feedback, sentiment)
            
            mock_alert.assert_called_once()
    
    async def test_conversation_memory_context(self, feedback_agent, test_user):
        """Test de gestion du contexte de conversation."""
        
        conversation_id = "conv-123"
        
        # Ajouter des messages à la conversation
        messages = [
            {"role": "user", "content": "Première question"},
            {"role": "assistant", "content": "Première réponse"},
            {"role": "user", "content": "Question de suivi"}
        ]
        
        for message in messages:
            await feedback_agent.add_conversation_context(
                conversation_id, 
                test_user["user_id"],
                message
            )
        
        # Récupérer le contexte
        context = await feedback_agent.get_conversation_context(
            conversation_id, 
            max_messages=10
        )
        
        assert len(context) == 3
        assert context[0]["content"] == "Première question"
    
    async def test_learning_threshold_filtering(self, feedback_agent, test_organization):
        """Test de filtrage par seuil d'apprentissage."""
        
        # Mock avec patterns de confiance variée
        with patch.object(feedback_agent, '_analyze_feedback_patterns') as mock_patterns:
            mock_patterns.return_value = [
                MagicMock(confidence=0.9, pattern_type="high_confidence"),  # Au-dessus du seuil
                MagicMock(confidence=0.4, pattern_type="low_confidence"),   # En-dessous du seuil
            ]
            
            with patch.object(feedback_agent, '_analyze_query_patterns', return_value=[]), \
                 patch.object(feedback_agent, '_analyze_performance_patterns', return_value=[]):
                
                insights = await feedback_agent.get_learning_insights(
                    test_organization["organization_id"]
                )
                
                # Seul le pattern avec confiance >= 0.5 doit être inclus
                assert len(insights) == 1
                assert "high_confidence" in insights[0].title
    
    async def test_feedback_metrics_calculation(self, feedback_agent):
        """Test de calcul des métriques de feedback."""
        
        # Simuler des métriques de feedback
        feedback_agent.feedback_metrics = {
            "total_feedback": 100,
            "positive_feedback": 70,
            "negative_feedback": 20,
            "neutral_feedback": 10
        }
        
        await feedback_agent._calculate_periodic_metrics()
        
        # Vérifier que le taux de satisfaction est calculé
        assert "satisfaction_rate" in feedback_agent.memory_metrics
        assert feedback_agent.memory_metrics["satisfaction_rate"] == 0.7
    
    async def test_expired_memory_cleanup(self, feedback_agent):
        """Test de nettoyage de la mémoire expirée."""
        
        # Ajouter des éléments dans le cache avec TTL expiré
        old_timestamp = datetime.utcnow() - timedelta(hours=25)  # Plus de 24h
        
        feedback_agent.conversation_cache["old-conv"] = {
            "timestamp": old_timestamp,
            "messages": []
        }
        
        feedback_agent.user_preferences_cache["old-user"] = {
            "timestamp": old_timestamp,
            "preferences": {}
        }
        
        # Nettoyage
        await feedback_agent._cleanup_expired_memory()
        
        # Vérifier que les éléments expirés ont été supprimés
        assert "old-conv" not in feedback_agent.conversation_cache
        assert "old-user" not in feedback_agent.user_preferences_cache
    
    async def test_insight_priority_calculation(self, feedback_agent):
        """Test de calcul de priorité des insights."""
        
        # Pattern critique
        critical_pattern = MagicMock()
        critical_pattern.confidence = 0.95
        critical_pattern.frequency = 15
        
        priority = feedback_agent._calculate_insight_priority(critical_pattern)
        assert priority == "critical"
        
        # Pattern haute priorité
        high_pattern = MagicMock()
        high_pattern.confidence = 0.8
        high_pattern.frequency = 8
        
        priority = feedback_agent._calculate_insight_priority(high_pattern)
        assert priority == "high"
        
        # Pattern basse priorité
        low_pattern = MagicMock()
        low_pattern.confidence = 0.3
        low_pattern.frequency = 2
        
        priority = feedback_agent._calculate_insight_priority(low_pattern)
        assert priority == "low"
    
    async def test_concurrent_feedback_processing(self, feedback_agent, test_user, test_organization):
        """Test de traitement concurrent de feedbacks."""
        
        import asyncio
        
        async def submit_feedback(index):
            feedback = FeedbackEntry(
                user_id=test_user["user_id"],
                organization_id=test_organization["organization_id"],
                feedback_type="quality",
                rating=index % 5 + 1,
                content=f"Feedback concurrent {index}"
            )
            return await feedback_agent.store_feedback(feedback)
        
        # Soumettre 10 feedbacks en parallèle
        tasks = [submit_feedback(i) for i in range(10)]
        feedback_ids = await asyncio.gather(*tasks)
        
        assert len(feedback_ids) == 10
        assert all(feedback_id for feedback_id in feedback_ids)
        
        # Vérifier que tous les IDs sont uniques
        assert len(set(feedback_ids)) == 10
