"""
Agent Summarizer - Responsable du résumé et de la condensation de contenu.
"""

from typing import List, Dict, Any, Optional
from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class SummaryResult(BaseModel):
    """Résultat d'un résumé"""
    summary: str = Field(description="Résumé généré")
    original_length: int = Field(description="Longueur du texte original")
    summary_length: int = Field(description="Longueur du résumé")
    compression_ratio: float = Field(description="Ratio de compression")
    key_points: List[str] = Field(default_factory=list, description="Points clés identifiés")
    confidence_score: float = Field(description="Score de confiance")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractiveSummaryTool(BaseTool):
    """Outil de résumé extractif"""
    
    name: str = "extractive_summary"
    description: str = "Génère un résumé extractif en sélectionnant les phrases les plus importantes"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _run(
        self,
        text: str,
        max_sentences: int = 5,
        importance_threshold: float = 0.6
    ) -> SummaryResult:
        """
        Génère un résumé extractif
        
        Args:
            text: Texte à résumer
            max_sentences: Nombre maximum de phrases
            importance_threshold: Seuil d'importance
            
        Returns:
            SummaryResult avec résumé extractif
        """
        try:
            logger.info(f"Génération résumé extractif ({max_sentences} phrases max)")
            
            if not text.strip():
                return SummaryResult(
                    summary="",
                    original_length=0,
                    summary_length=0,
                    compression_ratio=0,
                    confidence_score=0,
                    metadata={"error": "Texte vide"}
                )
            
            # Diviser en phrases
            sentences = self._split_sentences(text)
            if len(sentences) <= max_sentences:
                return SummaryResult(
                    summary=text,
                    original_length=len(text),
                    summary_length=len(text),
                    compression_ratio=1.0,
                    key_points=sentences,
                    confidence_score=1.0,
                    metadata={"method": "no_compression_needed"}
                )
            
            # Scorer les phrases
            sentence_scores = self._score_sentences(sentences, text)
            
            # Sélectionner les meilleures phrases
            top_sentences = self._select_top_sentences(
                sentences, 
                sentence_scores, 
                max_sentences,
                importance_threshold
            )
            
            # Construire le résumé
            summary = ". ".join(top_sentences) + "."
            key_points = top_sentences
            
            # Calculer les métriques
            original_length = len(text)
            summary_length = len(summary)
            compression_ratio = summary_length / original_length if original_length > 0 else 0
            confidence_score = self._calculate_confidence(sentence_scores, len(top_sentences))
            
            logger.info(f"Résumé extractif généré: {compression_ratio:.2%} compression")
            
            return SummaryResult(
                summary=summary,
                original_length=original_length,
                summary_length=summary_length,
                compression_ratio=compression_ratio,
                key_points=key_points,
                confidence_score=confidence_score,
                metadata={
                    "method": "extractive",
                    "sentences_analyzed": len(sentences),
                    "sentences_selected": len(top_sentences)
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur résumé extractif: {e}")
            return SummaryResult(
                summary="",
                original_length=len(text) if text else 0,
                summary_length=0,
                compression_ratio=0,
                confidence_score=0,
                metadata={"error": str(e)}
            )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Divise le texte en phrases"""
        import re
        # Pattern simple pour diviser les phrases
        sentence_pattern = r'[.!?]+\s+'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _score_sentences(self, sentences: List[str], full_text: str) -> List[float]:
        """Score les phrases selon leur importance"""
        scores = []
        
        # Mots-clés fréquents
        words = full_text.lower().split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        for sentence in sentences:
            score = 0
            sentence_words = sentence.lower().split()
            
            # Score basé sur la fréquence des mots
            for word in sentence_words:
                if word in word_freq:
                    score += word_freq[word]
            
            # Normaliser par la longueur de la phrase
            if len(sentence_words) > 0:
                score = score / len(sentence_words)
            
            # Bonus pour position (début et fin)
            position_bonus = 0
            idx = sentences.index(sentence)
            if idx < len(sentences) * 0.2:  # Début
                position_bonus = 0.1
            elif idx > len(sentences) * 0.8:  # Fin
                position_bonus = 0.05
            
            scores.append(score + position_bonus)
        
        return scores
    
    def _select_top_sentences(
        self,
        sentences: List[str],
        scores: List[float],
        max_sentences: int,
        threshold: float
    ) -> List[str]:
        """Sélectionne les meilleures phrases"""
        # Associer phrases et scores
        sentence_score_pairs = list(zip(sentences, scores))
        
        # Trier par score décroissant
        sentence_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Sélectionner les top phrases
        selected = []
        for sentence, score in sentence_score_pairs:
            if len(selected) >= max_sentences:
                break
            if score >= threshold or len(selected) < max_sentences // 2:
                selected.append(sentence)
        
        return selected
    
    def _calculate_confidence(self, scores: List[float], selected_count: int) -> float:
        """Calcule le score de confiance"""
        if not scores:
            return 0.0
        
        avg_score = sum(scores) / len(scores)
        max_score = max(scores) if scores else 0
        
        # Score basé sur la qualité moyenne et le nombre sélectionné
        quality_score = avg_score / max_score if max_score > 0 else 0
        coverage_score = min(selected_count / 5, 1.0)  # Idéal autour de 5 phrases
        
        return (quality_score + coverage_score) / 2


class AbstractiveSummaryTool(BaseTool):
    """Outil de résumé abstractif avec LLM"""
    
    name: str = "abstractive_summary"
    description: str = "Génère un résumé abstractif en reformulant le contenu"
    
    def __init__(self, llm_client=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client
    
    def _run(
        self,
        text: str,
        max_length: int = 200,
        style: str = "neutral",
        focus: Optional[str] = None
    ) -> SummaryResult:
        """
        Génère un résumé abstractif
        
        Args:
            text: Texte à résumer
            max_length: Longueur maximum en mots
            style: Style du résumé (neutral, academic, business)
            focus: Aspect à privilégier
            
        Returns:
            SummaryResult avec résumé abstractif
        """
        try:
            logger.info(f"Génération résumé abstractif ({max_length} mots max)")
            
            if not self.llm_client:
                logger.warning("LLM client non disponible, fallback vers extractif")
                extractive_tool = ExtractiveSummaryTool()
                return extractive_tool._run(text, max_sentences=3)
            
            if not text.strip():
                return SummaryResult(
                    summary="",
                    original_length=0,
                    summary_length=0,
                    compression_ratio=0,
                    confidence_score=0,
                    metadata={"error": "Texte vide"}
                )
            
            # Construire le prompt selon le style
            prompt = self._build_summary_prompt(text, max_length, style, focus)
            
            # Générer le résumé
            summary = self.llm_client.generate(prompt)
            summary = summary.strip()
            
            # Extraire les points clés
            key_points = self._extract_key_points(text, summary)
            
            # Calculer les métriques
            original_length = len(text)
            summary_length = len(summary)
            compression_ratio = summary_length / original_length if original_length > 0 else 0
            confidence_score = self._evaluate_summary_quality(text, summary)
            
            logger.info(f"Résumé abstractif généré: {compression_ratio:.2%} compression")
            
            return SummaryResult(
                summary=summary,
                original_length=original_length,
                summary_length=summary_length,
                compression_ratio=compression_ratio,
                key_points=key_points,
                confidence_score=confidence_score,
                metadata={
                    "method": "abstractive",
                    "style": style,
                    "focus": focus,
                    "model_used": getattr(self.llm_client, 'model_name', 'unknown')
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur résumé abstractif: {e}")
            return SummaryResult(
                summary="",
                original_length=len(text) if text else 0,
                summary_length=0,
                compression_ratio=0,
                confidence_score=0,
                metadata={"error": str(e)}
            )
    
    def _build_summary_prompt(
        self,
        text: str,
        max_length: int,
        style: str,
        focus: Optional[str]
    ) -> str:
        """Construit le prompt pour le résumé"""
        
        style_instructions = {
            "neutral": "Utilise un ton neutre et objectif.",
            "academic": "Utilise un style académique avec terminologie précise.",
            "business": "Utilise un style professionnel orienté business.",
            "casual": "Utilise un style décontracté et accessible."
        }
        
        style_instruction = style_instructions.get(style, style_instructions["neutral"])
        focus_instruction = f"Mets l'accent sur: {focus}." if focus else ""
        
        prompt = f"""
Résume le texte suivant en maximum {max_length} mots.

{style_instruction}
{focus_instruction}

Consignes:
- Conserve les informations essentielles
- Utilise tes propres mots (résumé abstractif)
- Assure-toi que le résumé est cohérent et fluide
- Évite les répétitions

Texte à résumer:
{text}

Résumé:
"""
        return prompt
    
    def _extract_key_points(self, original_text: str, summary: str) -> List[str]:
        """Extrait les points clés du résumé"""
        if not self.llm_client:
            return []
        
        prompt = f"""
À partir du résumé suivant, identifie 3-5 points clés principaux.
Retourne seulement la liste des points, un par ligne.

Résumé: {summary}

Points clés:
"""
        try:
            response = self.llm_client.generate(prompt)
            points = [line.strip() for line in response.split('\n') if line.strip()]
            return points[:5]  # Limite à 5 points
        except Exception as e:
            logger.warning(f"Erreur extraction points clés: {e}")
            return []
    
    def _evaluate_summary_quality(self, original_text: str, summary: str) -> float:
        """Évalue la qualité du résumé"""
        try:
            # Métriques simples de qualité
            quality_score = 0.8  # Score de base
            
            # Vérifier la longueur appropriée
            orig_words = len(original_text.split())
            summ_words = len(summary.split())
            
            if orig_words > 0:
                compression = summ_words / orig_words
                if 0.1 <= compression <= 0.5:  # Compression appropriée
                    quality_score += 0.1
            
            # Vérifier la cohérence (phrases complètes)
            if summary.endswith('.') or summary.endswith('!') or summary.endswith('?'):
                quality_score += 0.05
            
            # Bonus si pas de répétitions obvies
            words = summary.lower().split()
            unique_words = set(words)
            if len(unique_words) / len(words) > 0.7:  # Peu de répétitions
                quality_score += 0.05
            
            return min(quality_score, 1.0)
            
        except Exception:
            return 0.5  # Score par défaut


class SummarizerAgent:
    """
    Agent Summarizer - Expert en résumé et condensation de contenu
    """
    
    def __init__(
        self,
        llm_client=None,
        agent_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'agent Summarizer
        
        Args:
            llm_client: Client LLM pour les résumés abstractifs
            agent_config: Configuration de l'agent
        """
        self.llm_client = llm_client
        self.config = agent_config or {}
        
        # Configuration des outils
        self.tools = [
            ExtractiveSummaryTool(),
            AbstractiveSummaryTool(llm_client=llm_client)
        ]
        
        # Création de l'agent CrewAI
        self.agent = Agent(
            role="Expert en Résumé et Synthèse",
            goal="Créer des résumés clairs, concis et informatifs à partir de contenus volumineux",
            backstory="""Tu es un expert en communication et synthèse d'information. 
            Tu excelles à identifier l'essentiel dans des textes longs et à le reformuler 
            de manière claire et accessible pour différents publics.""",
            tools=self.tools,
            verbose=self.config.get("verbose", True),
            memory=True,
            max_iter=self.config.get("max_iterations", 2),
            max_execution_time=self.config.get("max_execution_time", 45)
        )
        
        logger.info("Agent Summarizer initialisé avec succès")
    
    def summarize(
        self,
        text: str,
        summary_type: str = "abstractive",
        max_length: int = 200,
        style: str = "neutral",
        focus: Optional[str] = None
    ) -> SummaryResult:
        """
        Résume un texte donné
        
        Args:
            text: Texte à résumer
            summary_type: Type de résumé ('extractive' ou 'abstractive')
            max_length: Longueur maximum
            style: Style du résumé
            focus: Aspect à privilégier
            
        Returns:
            SummaryResult avec le résumé généré
        """
        try:
            logger.info(f"Début résumé {summary_type} pour {len(text)} caractères")
            
            if summary_type == "extractive":
                tool = next(t for t in self.tools if t.name == "extractive_summary")
                max_sentences = max(1, max_length // 40)  # ~40 mots par phrase
                result = tool._run(text, max_sentences=max_sentences)
            else:
                tool = next(t for t in self.tools if t.name == "abstractive_summary")
                result = tool._run(text, max_length=max_length, style=style, focus=focus)
            
            logger.info(f"Résumé généré: {result.compression_ratio:.2%} compression")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du résumé: {e}")
            return SummaryResult(
                summary="",
                original_length=len(text) if text else 0,
                summary_length=0,
                compression_ratio=0,
                confidence_score=0,
                metadata={"error": str(e)}
            )
    
    def summarize_multiple(
        self,
        texts: List[str],
        individual_summaries: bool = True,
        global_summary: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Résume plusieurs textes
        
        Args:
            texts: Liste de textes à résumer
            individual_summaries: Générer des résumés individuels
            global_summary: Générer un résumé global
            **kwargs: Arguments pour le résumé
            
        Returns:
            Dictionnaire avec résumés individuels et/ou global
        """
        results = {
            "individual_summaries": [],
            "global_summary": None,
            "metadata": {
                "total_texts": len(texts),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            # Résumés individuels
            if individual_summaries:
                for i, text in enumerate(texts):
                    result = self.summarize(text, **kwargs)
                    results["individual_summaries"].append({
                        "index": i,
                        "result": result
                    })
            
            # Résumé global
            if global_summary and texts:
                combined_text = "\n\n".join(texts)
                global_result = self.summarize(combined_text, **kwargs)
                results["global_summary"] = global_result
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur résumé multiple: {e}")
            results["metadata"]["error"] = str(e)
            return results
    
    def create_task(
        self,
        text: str,
        summary_requirements: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Crée une tâche CrewAI pour le résumé
        
        Args:
            text: Texte à résumer
            summary_requirements: Exigences spécifiques
            
        Returns:
            Task CrewAI configurée
        """
        requirements = summary_requirements or {}
        
        task_description = f"""
        Résumer le texte suivant selon les exigences spécifiées.
        
        Texte à résumer: {text[:500]}{"..." if len(text) > 500 else ""}
        
        Exigences:
        - Type: {requirements.get('type', 'abstractive')}
        - Longueur max: {requirements.get('max_length', 200)} mots
        - Style: {requirements.get('style', 'neutral')}
        - Focus: {requirements.get('focus', 'informations essentielles')}
        
        Instructions:
        1. Analyser le contenu pour identifier les éléments clés
        2. Créer un résumé respectant les exigences
        3. Valider la qualité et la cohérence
        4. Extraire les points clés principaux
        
        Format de sortie: JSON avec résumé, métriques et métadonnées
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="JSON contenant le résumé avec métriques de qualité"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance de l'agent"""
        return {
            "agent_type": "summarizer",
            "tools_count": len(self.tools),
            "llm_client_status": "connected" if self.llm_client else "disconnected",
            "supported_summary_types": ["extractive", "abstractive"],
            "supported_styles": ["neutral", "academic", "business", "casual"],
            "timestamp": datetime.now().isoformat()
        }
