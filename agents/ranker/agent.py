"""
Agent Ranker - Responsable du classement, scoring et priorisation de contenu.
"""

from typing import List, Dict, Any, Optional, Tuple
from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class RankingResult(BaseModel):
    """Résultat d'un classement"""
    ranked_items: List[Dict[str, Any]] = Field(description="Items classés par ordre de pertinence")
    ranking_scores: List[float] = Field(description="Scores de classement")
    ranking_criteria: List[str] = Field(description="Critères utilisés")
    methodology: str = Field(description="Méthode de classement utilisée")
    confidence_score: float = Field(description="Confiance dans le classement")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class RelevanceRankingTool(BaseTool):
    """Outil de classement par pertinence"""
    
    name: str = "relevance_ranking"
    description: str = "Classe les items par pertinence selon une requête"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _run(
        self,
        query: str,
        items: List[Dict[str, Any]],
        ranking_method: str = "tf_idf",
        weights: Optional[Dict[str, float]] = None
    ) -> RankingResult:
        """
        Classe les items par pertinence
        
        Args:
            query: Requête de référence
            items: Items à classer
            ranking_method: Méthode de classement
            weights: Poids pour différents critères
            
        Returns:
            RankingResult avec items classés
        """
        try:
            logger.info(f"Classement par pertinence: {len(items)} items, méthode: {ranking_method}")
            
            if not items:
                return RankingResult(
                    ranked_items=[],
                    ranking_scores=[],
                    ranking_criteria=["relevance"],
                    methodology=ranking_method,
                    confidence_score=0.0,
                    metadata={"warning": "Aucun item à classer"}
                )
            
            # Calculer les scores selon la méthode
            if ranking_method == "tf_idf":
                scores = self._calculate_tf_idf_scores(query, items)
            elif ranking_method == "keyword_overlap":
                scores = self._calculate_keyword_overlap_scores(query, items)
            elif ranking_method == "weighted":
                scores = self._calculate_weighted_scores(query, items, weights or {})
            else:
                scores = self._calculate_simple_scores(query, items)
            
            # Associer items et scores
            item_score_pairs = list(zip(items, scores))
            
            # Trier par score décroissant
            item_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # Séparer items et scores
            ranked_items = [item for item, score in item_score_pairs]
            ranking_scores = [score for item, score in item_score_pairs]
            
            # Calculer la confiance
            confidence_score = self._calculate_ranking_confidence(ranking_scores)
            
            logger.info(f"Classement terminé: meilleur score {max(ranking_scores):.3f}")
            
            return RankingResult(
                ranked_items=ranked_items,
                ranking_scores=ranking_scores,
                ranking_criteria=["relevance", "query_match"],
                methodology=ranking_method,
                confidence_score=confidence_score,
                metadata={
                    "query_length": len(query.split()),
                    "items_count": len(items),
                    "score_range": [min(ranking_scores), max(ranking_scores)] if ranking_scores else [0, 0]
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur classement par pertinence: {e}")
            return RankingResult(
                ranked_items=items,  # Retourner dans l'ordre original
                ranking_scores=[0.5] * len(items),
                ranking_criteria=["error"],
                methodology=ranking_method,
                confidence_score=0.0,
                metadata={"error": str(e)}
            )
    
    def _calculate_tf_idf_scores(self, query: str, items: List[Dict[str, Any]]) -> List[float]:
        """Calcule les scores TF-IDF"""
        query_words = set(query.lower().split())
        scores = []
        
        # Calculer IDF pour chaque mot de la requête
        doc_count = len(items)
        idf_scores = {}
        
        for word in query_words:
            docs_with_word = sum(1 for item in items 
                               if word in item.get("content", "").lower())
            if docs_with_word > 0:
                idf_scores[word] = math.log(doc_count / docs_with_word)
            else:
                idf_scores[word] = 0
        
        # Calculer score pour chaque item
        for item in items:
            content = item.get("content", "").lower()
            content_words = content.split()
            
            tf_idf_score = 0
            for word in query_words:
                tf = content_words.count(word) / len(content_words) if content_words else 0
                tf_idf_score += tf * idf_scores.get(word, 0)
            
            scores.append(tf_idf_score)
        
        return scores
    
    def _calculate_keyword_overlap_scores(self, query: str, items: List[Dict[str, Any]]) -> List[float]:
        """Calcule les scores par chevauchement de mots-clés"""
        query_words = set(query.lower().split())
        scores = []
        
        for item in items:
            content = item.get("content", "").lower()
            content_words = set(content.split())
            
            # Intersection des mots
            common_words = query_words & content_words
            
            # Score basé sur le pourcentage de mots communs
            if query_words:
                overlap_score = len(common_words) / len(query_words)
            else:
                overlap_score = 0
            
            # Bonus pour position des mots (début du contenu)
            content_start = " ".join(content.split()[:50])  # Premiers 50 mots
            start_matches = sum(1 for word in common_words if word in content_start)
            position_bonus = start_matches * 0.1
            
            scores.append(overlap_score + position_bonus)
        
        return scores
    
    def _calculate_weighted_scores(
        self,
        query: str,
        items: List[Dict[str, Any]],
        weights: Dict[str, float]
    ) -> List[float]:
        """Calcule les scores pondérés"""
        scores = []
        
        for item in items:
            total_score = 0
            
            # Score de pertinence textuelle
            if "relevance" in weights:
                relevance_score = self._calculate_keyword_overlap_scores(query, [item])[0]
                total_score += relevance_score * weights["relevance"]
            
            # Score de qualité (si disponible)
            if "quality" in weights and "quality_score" in item:
                quality_score = item["quality_score"]
                total_score += quality_score * weights["quality"]
            
            # Score de fraîcheur (si disponible)
            if "recency" in weights and "timestamp" in item:
                try:
                    item_date = datetime.fromisoformat(item["timestamp"])
                    days_old = (datetime.now() - item_date).days
                    recency_score = max(0, 1 - (days_old / 365))  # Décroît sur 1 an
                    total_score += recency_score * weights["recency"]
                except:
                    pass
            
            # Score d'autorité de la source
            if "authority" in weights and "source_authority" in item:
                authority_score = item["source_authority"]
                total_score += authority_score * weights["authority"]
            
            scores.append(total_score)
        
        return scores
    
    def _calculate_simple_scores(self, query: str, items: List[Dict[str, Any]]) -> List[float]:
        """Calcule des scores simples par fréquence"""
        query_words = query.lower().split()
        scores = []
        
        for item in items:
            content = item.get("content", "").lower()
            
            # Compter les occurrences des mots de la requête
            score = 0
            for word in query_words:
                score += content.count(word)
            
            # Normaliser par la longueur du contenu
            content_length = len(content.split())
            if content_length > 0:
                score = score / content_length
            
            scores.append(score)
        
        return scores
    
    def _calculate_ranking_confidence(self, scores: List[float]) -> float:
        """Calcule la confiance dans le classement"""
        if len(scores) < 2:
            return 1.0 if scores else 0.0
        
        # Calculer la variance des scores
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        
        # Plus la variance est élevée, plus on est confiant dans le classement
        max_variance = 0.25  # Variance maximale attendue
        confidence = min(1.0, variance / max_variance)
        
        return confidence


class QualityRankingTool(BaseTool):
    """Outil de classement par qualité"""
    
    name: str = "quality_ranking"
    description: str = "Classe les items selon des critères de qualité"
    
    def __init__(self, llm_client=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client
    
    def _run(
        self,
        items: List[Dict[str, Any]],
        quality_criteria: List[str],
        use_llm: bool = False
    ) -> RankingResult:
        """
        Classe les items par qualité
        
        Args:
            items: Items à classer
            quality_criteria: Critères de qualité
            use_llm: Utiliser LLM pour l'évaluation
            
        Returns:
            RankingResult avec items classés par qualité
        """
        try:
            logger.info(f"Classement par qualité: {len(items)} items, {len(quality_criteria)} critères")
            
            if not items:
                return RankingResult(
                    ranked_items=[],
                    ranking_scores=[],
                    ranking_criteria=quality_criteria,
                    methodology="quality_assessment",
                    confidence_score=0.0
                )
            
            # Évaluer la qualité de chaque item
            if use_llm and self.llm_client:
                scores = self._evaluate_quality_with_llm(items, quality_criteria)
            else:
                scores = self._evaluate_quality_heuristic(items, quality_criteria)
            
            # Associer et trier
            item_score_pairs = list(zip(items, scores))
            item_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            ranked_items = [item for item, score in item_score_pairs]
            ranking_scores = [score for item, score in item_score_pairs]
            
            confidence_score = self._calculate_ranking_confidence(ranking_scores)
            
            logger.info(f"Classement qualité terminé: meilleur score {max(ranking_scores):.3f}")
            
            return RankingResult(
                ranked_items=ranked_items,
                ranking_scores=ranking_scores,
                ranking_criteria=quality_criteria,
                methodology="quality_assessment_with_llm" if use_llm else "quality_assessment_heuristic",
                confidence_score=confidence_score,
                metadata={
                    "use_llm": use_llm,
                    "criteria_count": len(quality_criteria)
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur classement par qualité: {e}")
            return RankingResult(
                ranked_items=items,
                ranking_scores=[0.5] * len(items),
                ranking_criteria=quality_criteria,
                methodology="error",
                confidence_score=0.0,
                metadata={"error": str(e)}
            )
    
    def _evaluate_quality_heuristic(
        self,
        items: List[Dict[str, Any]],
        criteria: List[str]
    ) -> List[float]:
        """Évalue la qualité avec des heuristiques"""
        scores = []
        
        for item in items:
            content = item.get("content", "")
            total_score = 0
            
            # Longueur appropriée
            if "length" in criteria:
                word_count = len(content.split())
                if 50 <= word_count <= 500:  # Longueur idéale
                    total_score += 0.2
                elif word_count > 10:
                    total_score += 0.1
            
            # Structure (phrases complètes)
            if "structure" in criteria:
                sentences = content.count('.') + content.count('!') + content.count('?')
                if sentences >= 2:
                    total_score += 0.2
            
            # Richesse vocabulaire
            if "vocabulary" in criteria:
                words = content.lower().split()
                unique_words = set(words)
                if words and len(unique_words) / len(words) > 0.7:
                    total_score += 0.2
            
            # Présence de détails
            if "detail" in criteria:
                detail_indicators = ["par exemple", "notamment", "c'est-à-dire", "en particulier"]
                if any(indicator in content.lower() for indicator in detail_indicators):
                    total_score += 0.2
            
            # Cohérence (pas de contradictions évidentes)
            if "coherence" in criteria:
                contradiction_words = ["mais", "cependant", "toutefois", "néanmoins"]
                contradictions = sum(1 for word in contradiction_words if word in content.lower())
                if contradictions <= 2:  # Quelques nuances OK
                    total_score += 0.2
            
            scores.append(total_score)
        
        return scores
    
    def _evaluate_quality_with_llm(
        self,
        items: List[Dict[str, Any]],
        criteria: List[str]
    ) -> List[float]:
        """Évalue la qualité avec LLM"""
        scores = []
        
        criteria_text = ", ".join(criteria)
        
        for item in items:
            content = item.get("content", "")
            
            if not content.strip():
                scores.append(0.0)
                continue
            
            try:
                evaluation_prompt = f"""
Évalue la qualité du contenu suivant selon ces critères: {criteria_text}

Contenu:
{content}

Donne un score de 0 à 1 pour chaque critère, puis un score global de 0 à 1.
Format: Critère1: X.X, Critère2: X.X, Score global: X.X
"""
                
                response = self.llm_client.generate(evaluation_prompt)
                
                # Parser le score global
                import re
                global_match = re.search(r'score global:?\s*(\d*\.?\d+)', response.lower())
                if global_match:
                    score = float(global_match.group(1))
                    scores.append(min(1.0, max(0.0, score)))
                else:
                    scores.append(0.5)  # Score par défaut
                    
            except Exception as e:
                logger.warning(f"Erreur évaluation LLM: {e}")
                scores.append(0.5)
        
        return scores
    
    def _calculate_ranking_confidence(self, scores: List[float]) -> float:
        """Calcule la confiance dans le classement qualité"""
        if len(scores) < 2:
            return 1.0 if scores else 0.0
        
        # Calculer l'écart-type
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = math.sqrt(variance)
        
        # Confiance basée sur la dispersion
        confidence = min(1.0, std_dev * 2)  # Plus de dispersion = plus de confiance
        
        return confidence


class RankerAgent:
    """
    Agent Ranker - Expert en classement et priorisation
    """
    
    def __init__(
        self,
        llm_client=None,
        agent_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'agent Ranker
        
        Args:
            llm_client: Client LLM pour évaluations avancées
            agent_config: Configuration de l'agent
        """
        self.llm_client = llm_client
        self.config = agent_config or {}
        
        # Configuration des outils
        self.tools = [
            RelevanceRankingTool(),
            QualityRankingTool(llm_client=llm_client)
        ]
        
        # Création de l'agent CrewAI
        self.agent = Agent(
            role="Expert en Classement et Priorisation",
            goal="Classer et prioriser le contenu selon différents critères de pertinence et qualité",
            backstory="""Tu es un expert en analyse comparative et évaluation de contenu. 
            Tu excelles à identifier les critères pertinents pour classer l'information et 
            à appliquer des méthodes rigoureuses pour établir des classements fiables.""",
            tools=self.tools,
            verbose=self.config.get("verbose", True),
            memory=True,
            max_iter=self.config.get("max_iterations", 2),
            max_execution_time=self.config.get("max_execution_time", 45)
        )
        
        logger.info("Agent Ranker initialisé avec succès")
    
    def rank(
        self,
        items: List[Dict[str, Any]],
        ranking_type: str = "relevance",
        query: Optional[str] = None,
        criteria: Optional[List[str]] = None,
        **kwargs
    ) -> RankingResult:
        """
        Classe les items selon le type spécifié
        
        Args:
            items: Items à classer
            ranking_type: Type de classement ('relevance' ou 'quality')
            query: Requête pour classement par pertinence
            criteria: Critères pour classement par qualité
            **kwargs: Arguments additionnels
            
        Returns:
            RankingResult avec items classés
        """
        try:
            logger.info(f"Classement {ranking_type} de {len(items)} items")
            
            if ranking_type == "quality":
                tool = next(t for t in self.tools if t.name == "quality_ranking")
                result = tool._run(
                    items=items,
                    quality_criteria=criteria or ["length", "structure", "coherence"],
                    **kwargs
                )
            else:  # relevance
                if not query:
                    raise ValueError("Query requise pour classement par pertinence")
                
                tool = next(t for t in self.tools if t.name == "relevance_ranking")
                result = tool._run(
                    query=query,
                    items=items,
                    **kwargs
                )
            
            logger.info(f"Classement terminé: confiance {result.confidence_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du classement: {e}")
            return RankingResult(
                ranked_items=items,
                ranking_scores=[0.5] * len(items),
                ranking_criteria=criteria or ["error"],
                methodology="error",
                confidence_score=0.0,
                metadata={"error": str(e)}
            )
    
    def multi_criteria_rank(
        self,
        items: List[Dict[str, Any]],
        criteria_weights: Dict[str, float],
        query: Optional[str] = None
    ) -> RankingResult:
        """
        Classement multi-critères avec pondération
        
        Args:
            items: Items à classer
            criteria_weights: Poids pour chaque critère
            query: Requête pour critères de pertinence
            
        Returns:
            RankingResult combiné
        """
        try:
            logger.info(f"Classement multi-critères: {len(criteria_weights)} critères")
            
            combined_scores = [0.0] * len(items)
            all_criteria = []
            
            # Classement par pertinence si requis
            if "relevance" in criteria_weights and query:
                relevance_result = self.rank(items, "relevance", query=query)
                weight = criteria_weights["relevance"]
                
                for i, score in enumerate(relevance_result.ranking_scores):
                    combined_scores[i] += score * weight
                
                all_criteria.extend(relevance_result.ranking_criteria)
            
            # Classement par qualité si requis
            quality_criteria = [k for k in criteria_weights.keys() if k != "relevance"]
            if quality_criteria:
                quality_result = self.rank(items, "quality", criteria=quality_criteria)
                
                # Appliquer les poids individuels
                for criterion in quality_criteria:
                    if criterion in criteria_weights:
                        weight = criteria_weights[criterion]
                        
                        for i, score in enumerate(quality_result.ranking_scores):
                            combined_scores[i] += score * weight
                
                all_criteria.extend(quality_result.ranking_criteria)
            
            # Normaliser les scores
            max_score = max(combined_scores) if combined_scores else 1
            if max_score > 0:
                combined_scores = [score / max_score for score in combined_scores]
            
            # Trier les items
            item_score_pairs = list(zip(items, combined_scores))
            item_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            ranked_items = [item for item, score in item_score_pairs]
            ranking_scores = [score for item, score in item_score_pairs]
            
            # Calculer confiance
            confidence = self._calculate_multi_criteria_confidence(criteria_weights, ranking_scores)
            
            return RankingResult(
                ranked_items=ranked_items,
                ranking_scores=ranking_scores,
                ranking_criteria=list(set(all_criteria)),
                methodology="multi_criteria_weighted",
                confidence_score=confidence,
                metadata={
                    "criteria_weights": criteria_weights,
                    "total_weight": sum(criteria_weights.values())
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur classement multi-critères: {e}")
            return RankingResult(
                ranked_items=items,
                ranking_scores=[0.5] * len(items),
                ranking_criteria=list(criteria_weights.keys()),
                methodology="error",
                confidence_score=0.0,
                metadata={"error": str(e)}
            )
    
    def _calculate_multi_criteria_confidence(
        self,
        criteria_weights: Dict[str, float],
        scores: List[float]
    ) -> float:
        """Calcule la confiance pour classement multi-critères"""
        
        # Confiance basée sur la distribution des poids
        weight_values = list(criteria_weights.values())
        weight_balance = 1.0 - max(weight_values) if weight_values else 0.5
        
        # Confiance basée sur la dispersion des scores
        if len(scores) >= 2:
            mean_score = sum(scores) / len(scores)
            variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
            score_confidence = min(1.0, variance * 4)
        else:
            score_confidence = 0.5
        
        # Combinaison des deux facteurs
        return (weight_balance + score_confidence) / 2
    
    def create_task(
        self,
        items: List[Dict[str, Any]],
        ranking_requirements: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Crée une tâche CrewAI pour le classement
        
        Args:
            items: Items à classer
            ranking_requirements: Exigences de classement
            
        Returns:
            Task CrewAI configurée
        """
        requirements = ranking_requirements or {}
        
        task_description = f"""
        Classer et prioriser {len(items)} items selon les critères spécifiés.
        
        Type de classement: {requirements.get('ranking_type', 'relevance')}
        Critères: {requirements.get('criteria', 'pertinence générale')}
        Requête: {requirements.get('query', 'Non spécifiée')}
        
        Instructions:
        1. Analyser chaque item selon les critères
        2. Appliquer la méthode de classement appropriée
        3. Calculer les scores de classement
        4. Ordonner les items par ordre décroissant
        5. Évaluer la confiance dans le classement
        
        Format de sortie: JSON avec items classés et métadonnées
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="JSON contenant le classement complet avec scores et confiance"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance de l'agent"""
        return {
            "agent_type": "ranker",
            "tools_count": len(self.tools),
            "llm_client_status": "connected" if self.llm_client else "disconnected",
            "ranking_types": ["relevance", "quality", "multi_criteria"],
            "ranking_methods": ["tf_idf", "keyword_overlap", "weighted", "heuristic", "llm_based"],
            "timestamp": datetime.now().isoformat()
        }
