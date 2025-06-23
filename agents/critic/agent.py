"""
Agent Critic - Responsable de la validation, contrôle qualité et évaluation de cohérence.
"""

from typing import List, Dict, Any, Optional, Union
from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import re
import json

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Résultat d'une validation"""
    is_valid: bool = Field(description="Validation réussie")
    overall_score: float = Field(description="Score global (0-1)")
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="Métriques détaillées")
    issues_found: List[Dict[str, Any]] = Field(default_factory=list, description="Problèmes identifiés")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions d'amélioration")
    validation_details: Dict[str, Any] = Field(default_factory=dict, description="Détails de validation")
    timestamp: datetime = Field(default_factory=datetime.now)


class ContentValidationTool(BaseTool):
    """Outil de validation de contenu"""
    
    name: str = "content_validation"
    description: str = "Valide la qualité, cohérence et exactitude du contenu"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _run(
        self,
        content: str,
        content_type: str = "general",
        quality_criteria: Optional[List[str]] = None,
        reference_sources: Optional[List[Dict[str, Any]]] = None
    ) -> ValidationResult:
        """
        Valide le contenu selon différents critères
        
        Args:
            content: Contenu à valider
            content_type: Type de contenu (summary, synthesis, answer)
            quality_criteria: Critères spécifiques
            reference_sources: Sources de référence pour vérification
            
        Returns:
            ValidationResult avec détails de validation
        """
        try:
            logger.info(f"Validation contenu type: {content_type}")
            
            if not content.strip():
                return ValidationResult(
                    is_valid=False,
                    overall_score=0.0,
                    issues_found=[{"type": "empty_content", "severity": "critical", "description": "Contenu vide"}],
                    validation_details={"error": "Contenu vide"}
                )
            
            # Initialiser les métriques
            quality_metrics = {}
            issues_found = []
            suggestions = []
            
            # Validation de base
            basic_validation = self._validate_basic_quality(content)
            quality_metrics.update(basic_validation["metrics"])
            issues_found.extend(basic_validation["issues"])
            suggestions.extend(basic_validation["suggestions"])
            
            # Validation spécifique au type
            type_validation = self._validate_by_type(content, content_type)
            quality_metrics.update(type_validation["metrics"])
            issues_found.extend(type_validation["issues"])
            suggestions.extend(type_validation["suggestions"])
            
            # Validation selon critères personnalisés
            if quality_criteria:
                criteria_validation = self._validate_custom_criteria(content, quality_criteria)
                quality_metrics.update(criteria_validation["metrics"])
                issues_found.extend(criteria_validation["issues"])
                suggestions.extend(criteria_validation["suggestions"])
            
            # Validation contre sources de référence
            if reference_sources:
                source_validation = self._validate_against_sources(content, reference_sources)
                quality_metrics.update(source_validation["metrics"])
                issues_found.extend(source_validation["issues"])
                suggestions.extend(source_validation["suggestions"])
            
            # Calculer le score global
            overall_score = self._calculate_overall_score(quality_metrics)
            
            # Déterminer si c'est valide
            is_valid = overall_score >= 0.7 and not any(
                issue["severity"] == "critical" for issue in issues_found
            )
            
            logger.info(f"Validation terminée: score {overall_score:.2f}, valide: {is_valid}")
            
            return ValidationResult(
                is_valid=is_valid,
                overall_score=overall_score,
                quality_metrics=quality_metrics,
                issues_found=issues_found,
                suggestions=suggestions,
                validation_details={
                    "content_type": content_type,
                    "content_length": len(content),
                    "validation_timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur validation contenu: {e}")
            return ValidationResult(
                is_valid=False,
                overall_score=0.0,
                issues_found=[{"type": "validation_error", "severity": "critical", "description": str(e)}],
                validation_details={"error": str(e)}
            )
    
    def _validate_basic_quality(self, content: str) -> Dict[str, Any]:
        """Validation qualité de base"""
        metrics = {}
        issues = []
        suggestions = []
        
        # Longueur
        word_count = len(content.split())
        char_count = len(content)
        
        if word_count < 10:
            issues.append({
                "type": "too_short",
                "severity": "medium",
                "description": f"Contenu très court ({word_count} mots)"
            })
            suggestions.append("Développer le contenu pour plus de détails")
        
        metrics["word_count"] = word_count
        metrics["char_count"] = char_count
        
        # Structure et ponctuation
        sentences = re.split(r'[.!?]+', content)
        complete_sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(complete_sentences) < 2:
            issues.append({
                "type": "poor_structure",
                "severity": "medium",
                "description": "Structure peu développée (moins de 2 phrases)"
            })
        
        # Vérifier la ponctuation finale
        if not content.strip().endswith(('.', '!', '?')):
            issues.append({
                "type": "missing_punctuation",
                "severity": "low",
                "description": "Ponctuation finale manquante"
            })
            suggestions.append("Ajouter une ponctuation finale appropriée")
        
        metrics["sentence_count"] = len(complete_sentences)
        metrics["avg_sentence_length"] = word_count / len(complete_sentences) if complete_sentences else 0
        
        # Répétitions
        words = content.lower().split()
        unique_words = set(words)
        repetition_ratio = len(unique_words) / len(words) if words else 0
        
        if repetition_ratio < 0.6:
            issues.append({
                "type": "high_repetition",
                "severity": "medium",
                "description": f"Taux de répétition élevé ({repetition_ratio:.1%})"
            })
            suggestions.append("Diversifier le vocabulaire utilisé")
        
        metrics["vocabulary_diversity"] = repetition_ratio
        
        # Lisibilité basique
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        metrics["avg_word_length"] = avg_word_length
        
        if avg_word_length > 8:
            suggestions.append("Simplifier le vocabulaire pour améliorer la lisibilité")
        
        return {
            "metrics": metrics,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _validate_by_type(self, content: str, content_type: str) -> Dict[str, Any]:
        """Validation spécifique au type de contenu"""
        metrics = {}
        issues = []
        suggestions = []
        
        if content_type == "summary":
            return self._validate_summary(content)
        elif content_type == "synthesis":
            return self._validate_synthesis(content)
        elif content_type == "answer":
            return self._validate_answer(content)
        else:
            return {"metrics": metrics, "issues": issues, "suggestions": suggestions}
    
    def _validate_summary(self, content: str) -> Dict[str, Any]:
        """Validation spécifique aux résumés"""
        metrics = {}
        issues = []
        suggestions = []
        
        # Un bon résumé doit être concis
        word_count = len(content.split())
        if word_count > 300:
            issues.append({
                "type": "summary_too_long",
                "severity": "medium",
                "description": f"Résumé trop long ({word_count} mots)"
            })
            suggestions.append("Condenser le résumé pour plus de concision")
        
        # Doit contenir des informations essentielles
        key_indicators = ["important", "principal", "essentiel", "clé", "notamment"]
        if not any(indicator in content.lower() for indicator in key_indicators):
            suggestions.append("Mettre en évidence les points clés avec des mots indicateurs")
        
        metrics["summary_conciseness"] = min(1.0, 200 / word_count) if word_count > 0 else 0
        
        return {"metrics": metrics, "issues": issues, "suggestions": suggestions}
    
    def _validate_synthesis(self, content: str) -> Dict[str, Any]:
        """Validation spécifique aux synthèses"""
        metrics = {}
        issues = []
        suggestions = []
        
        # Une synthèse doit intégrer plusieurs éléments
        integration_indicators = ["par ailleurs", "de plus", "en outre", "cependant", "néanmoins"]
        integration_score = sum(1 for indicator in integration_indicators if indicator in content.lower())
        
        if integration_score == 0:
            issues.append({
                "type": "poor_integration",
                "severity": "medium",
                "description": "Manque d'indicateurs d'intégration entre les idées"
            })
            suggestions.append("Utiliser des connecteurs logiques pour lier les idées")
        
        metrics["integration_score"] = min(1.0, integration_score / 3)
        
        # Vérifier la présence de références/sources
        citation_patterns = [r'\[.*?\]', r'selon.*', r'd\'après.*', r'source.*:']
        citations_found = sum(1 for pattern in citation_patterns 
                             if re.search(pattern, content, re.IGNORECASE))
        
        if citations_found == 0:
            suggestions.append("Inclure des références aux sources utilisées")
        
        metrics["citation_score"] = min(1.0, citations_found / 2)
        
        return {"metrics": metrics, "issues": issues, "suggestions": suggestions}
    
    def _validate_answer(self, content: str) -> Dict[str, Any]:
        """Validation spécifique aux réponses"""
        metrics = {}
        issues = []
        suggestions = []
        
        # Une réponse doit être directe et complète
        if content.lower().startswith(("je ne sais pas", "désolé", "impossible")):
            issues.append({
                "type": "negative_response",
                "severity": "high",
                "description": "Réponse négative ou évasive"
            })
        
        # Vérifier la présence d'exemples ou de détails
        detail_indicators = ["par exemple", "notamment", "c'est-à-dire", "en particulier"]
        has_details = any(indicator in content.lower() for indicator in detail_indicators)
        
        if not has_details and len(content.split()) > 50:
            suggestions.append("Ajouter des exemples concrets pour clarifier")
        
        metrics["completeness_score"] = 0.8 if has_details else 0.6
        
        return {"metrics": metrics, "issues": issues, "suggestions": suggestions}
    
    def _validate_custom_criteria(self, content: str, criteria: List[str]) -> Dict[str, Any]:
        """Validation selon critères personnalisés"""
        metrics = {}
        issues = []
        suggestions = []
        
        for criterion in criteria:
            if criterion.lower() not in content.lower():
                issues.append({
                    "type": "missing_criterion",
                    "severity": "medium",
                    "description": f"Critère manquant: {criterion}"
                })
                suggestions.append(f"Inclure des informations sur: {criterion}")
        
        criteria_met = sum(1 for criterion in criteria if criterion.lower() in content.lower())
        metrics["criteria_coverage"] = criteria_met / len(criteria) if criteria else 1.0
        
        return {"metrics": metrics, "issues": issues, "suggestions": suggestions}
    
    def _validate_against_sources(self, content: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validation contre sources de référence"""
        metrics = {}
        issues = []
        suggestions = []
        
        # Vérifier si le contenu utilise les informations des sources
        source_words = set()
        for source in sources:
            if "content" in source:
                words = source["content"].lower().split()[:100]  # Premiers 100 mots
                source_words.update(words)
        
        content_words = set(content.lower().split())
        common_words = source_words & content_words
        
        if source_words:
            source_usage = len(common_words) / len(source_words)
            metrics["source_usage"] = source_usage
            
            if source_usage < 0.1:
                issues.append({
                    "type": "low_source_usage",
                    "severity": "high",
                    "description": "Faible utilisation des sources fournies"
                })
                suggestions.append("Intégrer davantage d'informations des sources")
        
        return {"metrics": metrics, "issues": issues, "suggestions": suggestions}
    
    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """Calcule le score global de qualité"""
        if not metrics:
            return 0.5
        
        # Pondération des métriques
        weights = {
            "vocabulary_diversity": 0.15,
            "summary_conciseness": 0.20,
            "integration_score": 0.20,
            "citation_score": 0.15,
            "completeness_score": 0.15,
            "criteria_coverage": 0.10,
            "source_usage": 0.15
        }
        
        weighted_score = 0
        total_weight = 0
        
        for metric, value in metrics.items():
            if metric in weights:
                weighted_score += value * weights[metric]
                total_weight += weights[metric]
        
        # Score de base pour les métriques manquantes
        base_score = 0.6 * (1 - total_weight) if total_weight < 1 else 0
        
        return weighted_score + base_score


class FactCheckingTool(BaseTool):
    """Outil de vérification factuelle"""
    
    name: str = "fact_checking"
    description: str = "Vérifie la cohérence factuelle et logique du contenu"
    
    def __init__(self, llm_client=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client
    
    def _run(
        self,
        content: str,
        reference_sources: Optional[List[Dict[str, Any]]] = None,
        check_type: str = "basic"
    ) -> ValidationResult:
        """
        Vérifie la cohérence factuelle
        
        Args:
            content: Contenu à vérifier
            reference_sources: Sources de référence
            check_type: Type de vérification (basic, detailed, cross_reference)
            
        Returns:
            ValidationResult avec analyse factuelle
        """
        try:
            logger.info(f"Vérification factuelle type: {check_type}")
            
            quality_metrics = {}
            issues_found = []
            suggestions = []
            
            # Vérifications de base
            basic_checks = self._perform_basic_checks(content)
            quality_metrics.update(basic_checks["metrics"])
            issues_found.extend(basic_checks["issues"])
            suggestions.extend(basic_checks["suggestions"])
            
            # Vérification avec LLM si disponible
            if self.llm_client and check_type in ["detailed", "cross_reference"]:
                llm_checks = self._perform_llm_checks(content, reference_sources)
                quality_metrics.update(llm_checks["metrics"])
                issues_found.extend(llm_checks["issues"])
                suggestions.extend(llm_checks["suggestions"])
            
            # Score global
            overall_score = sum(quality_metrics.values()) / len(quality_metrics) if quality_metrics else 0.7
            
            is_valid = overall_score >= 0.6 and not any(
                issue["severity"] == "critical" for issue in issues_found
            )
            
            return ValidationResult(
                is_valid=is_valid,
                overall_score=overall_score,
                quality_metrics=quality_metrics,
                issues_found=issues_found,
                suggestions=suggestions,
                validation_details={
                    "check_type": check_type,
                    "sources_used": len(reference_sources) if reference_sources else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur fact-checking: {e}")
            return ValidationResult(
                is_valid=False,
                overall_score=0.0,
                issues_found=[{"type": "fact_check_error", "severity": "critical", "description": str(e)}]
            )
    
    def _perform_basic_checks(self, content: str) -> Dict[str, Any]:
        """Vérifications factuelles de base"""
        metrics = {}
        issues = []
        suggestions = []
        
        # Vérifier les contradictions internes
        sentences = re.split(r'[.!?]+', content)
        contradictions = self._detect_contradictions(sentences)
        
        if contradictions:
            for contradiction in contradictions:
                issues.append({
                    "type": "internal_contradiction",
                    "severity": "high",
                    "description": f"Contradiction possible: {contradiction}"
                })
            suggestions.append("Réviser le contenu pour éliminer les contradictions")
        
        metrics["consistency_score"] = max(0, 1.0 - len(contradictions) * 0.3)
        
        # Vérifier les affirmations absolues
        absolute_terms = ["toujours", "jamais", "tous", "aucun", "impossible", "certain"]
        absolute_count = sum(1 for term in absolute_terms if term in content.lower())
        
        if absolute_count > 2:
            suggestions.append("Nuancer les affirmations absolues avec des termes plus modérés")
        
        metrics["nuance_score"] = max(0.5, 1.0 - absolute_count * 0.1)
        
        return {"metrics": metrics, "issues": issues, "suggestions": suggestions}
    
    def _detect_contradictions(self, sentences: List[str]) -> List[str]:
        """Détecte les contradictions simples"""
        contradictions = []
        
        # Patterns de contradiction simples
        contradiction_patterns = [
            (r'(\w+) est (\w+)', r'\1 n\'est pas \2'),
            (r'augmente', r'diminue'),
            (r'améliore', r'détériore'),
            (r'efficace', r'inefficace')
        ]
        
        content_lower = ' '.join(sentences).lower()
        
        for pos_pattern, neg_pattern in contradiction_patterns:
            if re.search(pos_pattern, content_lower) and re.search(neg_pattern, content_lower):
                contradictions.append(f"Présence de termes contradictoires: {pos_pattern} vs {neg_pattern}")
        
        return contradictions
    
    def _perform_llm_checks(self, content: str, sources: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Vérifications factuelles avec LLM"""
        metrics = {}
        issues = []
        suggestions = []
        
        try:
            # Prompt de vérification factuelle
            sources_text = ""
            if sources:
                sources_text = "\n".join([f"Source: {s.get('content', '')[:200]}..." for s in sources[:3]])
            
            fact_check_prompt = f"""
Analyse le contenu suivant pour identifier d'éventuelles incohérences factuelles ou logiques:

Contenu à analyser:
{content}

{f"Sources de référence: {sources_text}" if sources_text else ""}

Identifie:
1. Les affirmations qui semblent incorrectes ou douteuses
2. Les incohérences logiques
3. Les contradictions avec les sources (si fournies)

Réponds par une liste numérotée des problèmes trouvés, ou "Aucun problème détecté" si le contenu semble cohérent.
"""
            
            response = self.llm_client.generate(fact_check_prompt)
            
            if "aucun problème détecté" not in response.lower():
                # Parser les problèmes identifiés
                lines = [line.strip() for line in response.split('\n') if line.strip()]
                for line in lines:
                    if re.match(r'^\d+\.', line):
                        issues.append({
                            "type": "llm_detected_issue",
                            "severity": "medium",
                            "description": line
                        })
                        suggestions.append("Vérifier et corriger le point mentionné")
            
            metrics["llm_fact_check_score"] = max(0.3, 1.0 - len(issues) * 0.2)
            
        except Exception as e:
            logger.warning(f"Erreur vérification LLM: {e}")
            metrics["llm_fact_check_score"] = 0.7
        
        return {"metrics": metrics, "issues": issues, "suggestions": suggestions}


class CriticAgent:
    """
    Agent Critic - Expert en validation et contrôle qualité
    """
    
    def __init__(
        self,
        llm_client=None,
        agent_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'agent Critic
        
        Args:
            llm_client: Client LLM pour les vérifications avancées
            agent_config: Configuration de l'agent
        """
        self.llm_client = llm_client
        self.config = agent_config or {}
        
        # Configuration des outils
        self.tools = [
            ContentValidationTool(),
            FactCheckingTool(llm_client=llm_client)
        ]
        
        # Création de l'agent CrewAI
        self.agent = Agent(
            role="Expert en Validation et Contrôle Qualité",
            goal="Assurer la qualité, cohérence et exactitude du contenu généré",
            backstory="""Tu es un expert en révision et validation de contenu avec une 
            attention particulière aux détails. Tu excelles à identifier les incohérences, 
            erreurs factuelles et problèmes de qualité pour garantir l'excellence du 
            contenu final.""",
            tools=self.tools,
            verbose=self.config.get("verbose", True),
            memory=True,
            max_iter=self.config.get("max_iterations", 2),
            max_execution_time=self.config.get("max_execution_time", 60)
        )
        
        logger.info("Agent Critic initialisé avec succès")
    
    def validate(
        self,
        content: str,
        content_type: str = "general",
        validation_level: str = "standard",
        reference_sources: Optional[List[Dict[str, Any]]] = None,
        quality_criteria: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Valide le contenu selon les critères spécifiés
        
        Args:
            content: Contenu à valider
            content_type: Type de contenu
            validation_level: Niveau de validation (basic, standard, strict)
            reference_sources: Sources de référence
            quality_criteria: Critères spécifiques
            
        Returns:
            ValidationResult avec détails complets
        """
        try:
            logger.info(f"Validation niveau {validation_level} pour type {content_type}")
            
            # Validation de contenu
            content_tool = next(t for t in self.tools if t.name == "content_validation")
            content_result = content_tool._run(
                content=content,
                content_type=content_type,
                quality_criteria=quality_criteria,
                reference_sources=reference_sources
            )
            
            # Fact-checking si niveau standard ou strict
            if validation_level in ["standard", "strict"]:
                fact_tool = next(t for t in self.tools if t.name == "fact_checking")
                fact_result = fact_tool._run(
                    content=content,
                    reference_sources=reference_sources,
                    check_type="detailed" if validation_level == "strict" else "basic"
                )
                
                # Combiner les résultats
                combined_metrics = {**content_result.quality_metrics, **fact_result.quality_metrics}
                combined_issues = content_result.issues_found + fact_result.issues_found
                combined_suggestions = list(set(content_result.suggestions + fact_result.suggestions))
                
                overall_score = sum(combined_metrics.values()) / len(combined_metrics) if combined_metrics else 0
                
                return ValidationResult(
                    is_valid=content_result.is_valid and fact_result.is_valid,
                    overall_score=overall_score,
                    quality_metrics=combined_metrics,
                    issues_found=combined_issues,
                    suggestions=combined_suggestions,
                    validation_details={
                        "validation_level": validation_level,
                        "content_type": content_type,
                        "validation_methods": ["content_validation", "fact_checking"]
                    }
                )
            
            return content_result
            
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {e}")
            return ValidationResult(
                is_valid=False,
                overall_score=0.0,
                issues_found=[{"type": "validation_error", "severity": "critical", "description": str(e)}],
                validation_details={"error": str(e)}
            )
    
    def create_task(
        self,
        content: str,
        validation_requirements: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Crée une tâche CrewAI pour la validation
        
        Args:
            content: Contenu à valider
            validation_requirements: Exigences de validation
            
        Returns:
            Task CrewAI configurée
        """
        requirements = validation_requirements or {}
        
        task_description = f"""
        Valider et évaluer la qualité du contenu suivant:
        
        Contenu: {content[:300]}{"..." if len(content) > 300 else ""}
        
        Critères de validation:
        - Type: {requirements.get('content_type', 'general')}
        - Niveau: {requirements.get('validation_level', 'standard')}
        - Critères spécifiques: {requirements.get('quality_criteria', 'qualité générale')}
        
        Instructions:
        1. Analyser la qualité générale du contenu
        2. Vérifier la cohérence et la structure
        3. Identifier les problèmes et incohérences
        4. Proposer des améliorations concrètes
        5. Assigner un score de qualité global
        
        Format de sortie: JSON avec validation complète et recommandations
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="JSON contenant l'évaluation détaillée avec score et suggestions"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance de l'agent"""
        return {
            "agent_type": "critic",
            "tools_count": len(self.tools),
            "llm_client_status": "connected" if self.llm_client else "disconnected",
            "validation_levels": ["basic", "standard", "strict"],
            "supported_content_types": ["general", "summary", "synthesis", "answer"],
            "timestamp": datetime.now().isoformat()
        }
