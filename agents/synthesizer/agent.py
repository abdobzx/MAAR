"""
Agent Synthesizer - Responsable de la génération contextualisée et de la synthèse.
"""

from typing import List, Dict, Any, Optional
from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class SynthesisResult(BaseModel):
    """Résultat d'une synthèse"""
    synthesis: str = Field(description="Synthèse générée")
    sources_used: List[Dict[str, Any]] = Field(default_factory=list, description="Sources utilisées")
    coherence_score: float = Field(description="Score de cohérence")
    completeness_score: float = Field(description="Score de complétude")
    citations: List[str] = Field(default_factory=list, description="Citations référencées")
    confidence_level: str = Field(description="Niveau de confiance")
    word_count: int = Field(description="Nombre de mots")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextualSynthesisTool(BaseTool):
    """Outil de synthèse contextuelle"""
    
    name: str = "contextual_synthesis"
    description: str = "Génère une synthèse contextualisée à partir de multiples sources"
    
    def __init__(self, llm_client=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client
    
    def _run(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        synthesis_style: str = "comprehensive",
        max_length: int = 500,
        include_citations: bool = True,
        focus_areas: Optional[List[str]] = None
    ) -> SynthesisResult:
        """
        Génère une synthèse contextuelle
        
        Args:
            query: Question ou demande de l'utilisateur
            sources: Sources d'information
            synthesis_style: Style de synthèse
            max_length: Longueur maximum en mots
            include_citations: Inclure les citations
            focus_areas: Domaines à privilégier
            
        Returns:
            SynthesisResult avec synthèse générée
        """
        try:
            logger.info(f"Génération synthèse contextuelle pour: {query}")
            
            if not self.llm_client:
                return SynthesisResult(
                    synthesis="Erreur: LLM client non disponible",
                    coherence_score=0,
                    completeness_score=0,
                    confidence_level="none",
                    word_count=0,
                    metadata={"error": "LLM client requis"}
                )
            
            if not sources:
                return SynthesisResult(
                    synthesis="Aucune source disponible pour générer une synthèse.",
                    coherence_score=0,
                    completeness_score=0,
                    confidence_level="low",
                    word_count=0,
                    metadata={"warning": "Aucune source fournie"}
                )
            
            # Préparer le contexte à partir des sources
            context = self._prepare_context(sources, focus_areas)
            
            # Construire le prompt de synthèse
            prompt = self._build_synthesis_prompt(
                query, context, synthesis_style, max_length, include_citations
            )
            
            # Générer la synthèse
            synthesis = self.llm_client.generate(prompt)
            synthesis = synthesis.strip()
            
            # Extraire les citations si demandées
            citations = self._extract_citations(synthesis) if include_citations else []
            
            # Évaluer la qualité
            quality_metrics = self._evaluate_synthesis_quality(
                query, synthesis, sources, focus_areas
            )
            
            # Calculer les métriques
            word_count = len(synthesis.split())
            confidence_level = self._determine_confidence_level(quality_metrics, len(sources))
            
            logger.info(f"Synthèse générée: {word_count} mots, confiance: {confidence_level}")
            
            return SynthesisResult(
                synthesis=synthesis,
                sources_used=sources,
                coherence_score=quality_metrics["coherence"],
                completeness_score=quality_metrics["completeness"],
                citations=citations,
                confidence_level=confidence_level,
                word_count=word_count,
                metadata={
                    "style": synthesis_style,
                    "sources_count": len(sources),
                    "focus_areas": focus_areas,
                    "include_citations": include_citations
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur synthèse contextuelle: {e}")
            return SynthesisResult(
                synthesis="",
                coherence_score=0,
                completeness_score=0,
                confidence_level="error",
                word_count=0,
                metadata={"error": str(e)}
            )
    
    def _prepare_context(
        self,
        sources: List[Dict[str, Any]],
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """Prépare le contexte à partir des sources"""
        context_parts = []
        
        for i, source in enumerate(sources[:10]):  # Limite à 10 sources
            content = source.get("content", "")
            source_info = source.get("metadata", {})
            
            # Filtrer le contenu selon les focus areas si spécifiées
            if focus_areas:
                content = self._filter_content_by_focus(content, focus_areas)
            
            source_entry = f"Source {i+1}"
            if source_info.get("source"):
                source_entry += f" ({source_info['source']})"
            source_entry += f":\n{content}\n"
            
            context_parts.append(source_entry)
        
        return "\n".join(context_parts)
    
    def _filter_content_by_focus(self, content: str, focus_areas: List[str]) -> str:
        """Filtre le contenu selon les domaines de focus"""
        # Implémentation simple : rechercher les focus areas dans le contenu
        filtered_sentences = []
        sentences = content.split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and any(focus.lower() in sentence.lower() for focus in focus_areas):
                filtered_sentences.append(sentence)
        
        # Si aucune phrase filtrée, retourner le contenu original tronqué
        if not filtered_sentences:
            return content[:1000] + "..." if len(content) > 1000 else content
        
        return '. '.join(filtered_sentences[:5]) + '.'
    
    def _build_synthesis_prompt(
        self,
        query: str,
        context: str,
        style: str,
        max_length: int,
        include_citations: bool
    ) -> str:
        """Construit le prompt pour la synthèse"""
        
        style_instructions = {
            "comprehensive": "Fournis une synthèse complète et détaillée.",
            "concise": "Sois concis et va à l'essentiel.",
            "analytical": "Adopte une approche analytique avec arguments structurés.",
            "narrative": "Utilise un style narratif fluide.",
            "academic": "Emploie un style académique rigoureux.",
            "practical": "Concentre-toi sur les aspects pratiques et actionables."
        }
        
        style_instruction = style_instructions.get(style, style_instructions["comprehensive"])
        citation_instruction = ""
        
        if include_citations:
            citation_instruction = """
Inclus des références aux sources en utilisant le format [Source X] dans le texte.
"""
        
        prompt = f"""
Basé sur les sources suivantes, réponds à cette question/demande: {query}

{style_instruction}
{citation_instruction}

Consignes:
- Maximum {max_length} mots
- Utilise uniquement les informations des sources fournies
- Synthétise de manière cohérente et logique
- Si les sources sont contradictoires, mentionne-le
- Si l'information est insuffisante, indique-le clairement

Sources:
{context}

Synthèse:
"""
        return prompt
    
    def _extract_citations(self, synthesis: str) -> List[str]:
        """Extrait les citations du texte de synthèse"""
        import re
        citation_pattern = r'\[Source \d+\]'
        citations = re.findall(citation_pattern, synthesis)
        return list(set(citations))  # Enlever les doublons
    
    def _evaluate_synthesis_quality(
        self,
        query: str,
        synthesis: str,
        sources: List[Dict[str, Any]],
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """Évalue la qualité de la synthèse"""
        
        # Score de cohérence (basé sur la structure et la fluidité)
        coherence_score = 0.8  # Score de base
        
        # Vérifier la structure (phrases complètes, ponctuation)
        sentences = synthesis.split('.')
        complete_sentences = [s for s in sentences if s.strip() and len(s.strip()) > 10]
        if len(complete_sentences) >= 2:
            coherence_score += 0.1
        
        # Score de complétude (basé sur l'utilisation des sources)
        completeness_score = 0.7  # Score de base
        
        # Vérifier si les sources sont utilisées
        source_keywords = []
        for source in sources:
            content = source.get("content", "")
            words = content.lower().split()[:50]  # Premiers mots de chaque source
            source_keywords.extend(words)
        
        synthesis_words = synthesis.lower().split()
        common_words = set(source_keywords) & set(synthesis_words)
        
        if source_keywords and len(common_words) > len(source_keywords) * 0.1:
            completeness_score += 0.2
        
        # Bonus pour focus areas
        if focus_areas:
            focus_mentioned = any(focus.lower() in synthesis.lower() for focus in focus_areas)
            if focus_mentioned:
                completeness_score += 0.1
        
        return {
            "coherence": min(coherence_score, 1.0),
            "completeness": min(completeness_score, 1.0)
        }
    
    def _determine_confidence_level(
        self,
        quality_metrics: Dict[str, float],
        sources_count: int
    ) -> str:
        """Détermine le niveau de confiance"""
        avg_quality = (quality_metrics["coherence"] + quality_metrics["completeness"]) / 2
        
        if avg_quality >= 0.8 and sources_count >= 3:
            return "high"
        elif avg_quality >= 0.6 and sources_count >= 2:
            return "medium"
        elif avg_quality >= 0.4:
            return "low"
        else:
            return "very_low"


class ComparativeSynthesisTool(BaseTool):
    """Outil de synthèse comparative"""
    
    name: str = "comparative_synthesis"
    description: str = "Compare et synthétise différents points de vue ou approches"
    
    def __init__(self, llm_client=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_client = llm_client
    
    def _run(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        comparison_aspects: List[str],
        include_conclusion: bool = True
    ) -> SynthesisResult:
        """
        Génère une synthèse comparative
        
        Args:
            query: Question de comparaison
            sources: Sources à comparer
            comparison_aspects: Aspects à comparer
            include_conclusion: Inclure une conclusion
            
        Returns:
            SynthesisResult avec analyse comparative
        """
        try:
            logger.info(f"Génération synthèse comparative: {len(sources)} sources")
            
            if not self.llm_client:
                return SynthesisResult(
                    synthesis="Erreur: LLM client non disponible",
                    coherence_score=0,
                    completeness_score=0,
                    confidence_level="none",
                    word_count=0,
                    metadata={"error": "LLM client requis"}
                )
            
            if len(sources) < 2:
                return SynthesisResult(
                    synthesis="Au moins 2 sources sont nécessaires pour une comparaison.",
                    coherence_score=0,
                    completeness_score=0,
                    confidence_level="low",
                    word_count=0,
                    metadata={"warning": "Sources insuffisantes"}
                )
            
            # Préparer le prompt de comparaison
            prompt = self._build_comparison_prompt(
                query, sources, comparison_aspects, include_conclusion
            )
            
            # Générer la synthèse comparative
            synthesis = self.llm_client.generate(prompt)
            synthesis = synthesis.strip()
            
            # Évaluer la qualité
            quality_metrics = self._evaluate_comparison_quality(
                synthesis, sources, comparison_aspects
            )
            
            word_count = len(synthesis.split())
            confidence_level = self._determine_confidence_level(quality_metrics, len(sources))
            
            logger.info(f"Synthèse comparative générée: {word_count} mots")
            
            return SynthesisResult(
                synthesis=synthesis,
                sources_used=sources,
                coherence_score=quality_metrics["coherence"],
                completeness_score=quality_metrics["completeness"],
                citations=[],
                confidence_level=confidence_level,
                word_count=word_count,
                metadata={
                    "type": "comparative",
                    "comparison_aspects": comparison_aspects,
                    "include_conclusion": include_conclusion
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur synthèse comparative: {e}")
            return SynthesisResult(
                synthesis="",
                coherence_score=0,
                completeness_score=0,
                confidence_level="error",
                word_count=0,
                metadata={"error": str(e)}
            )
    
    def _build_comparison_prompt(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        aspects: List[str],
        include_conclusion: bool
    ) -> str:
        """Construit le prompt de comparaison"""
        
        sources_text = ""
        for i, source in enumerate(sources):
            content = source.get("content", "")
            source_info = source.get("metadata", {})
            
            sources_text += f"\nPosition/Source {i+1}:\n{content}\n"
        
        aspects_text = "\n".join([f"- {aspect}" for aspect in aspects])
        
        conclusion_instruction = ""
        if include_conclusion:
            conclusion_instruction = """
4. Tire une conclusion nuancée qui synthétise les différentes perspectives
"""
        
        prompt = f"""
Compare et analyse les différentes sources/positions suivantes concernant: {query}

Aspects à comparer:
{aspects_text}

Sources à analyser:
{sources_text}

Structure ta réponse ainsi:
1. Introduction du sujet et des perspectives analysées
2. Comparaison détaillée pour chaque aspect mentionné
3. Identification des points de convergence et de divergence
{conclusion_instruction}

Consignes:
- Reste objectif et équitable envers toutes les positions
- Mentionne clairement les différences et similitudes
- Utilise des exemples concrets des sources
- Si des informations manquent, indique-le

Analyse comparative:
"""
        return prompt
    
    def _evaluate_comparison_quality(
        self,
        synthesis: str,
        sources: List[Dict[str, Any]],
        aspects: List[str]
    ) -> Dict[str, float]:
        """Évalue la qualité de la comparaison"""
        
        coherence_score = 0.7
        completeness_score = 0.7
        
        # Vérifier la mention des aspects
        mentioned_aspects = sum(1 for aspect in aspects if aspect.lower() in synthesis.lower())
        if aspects:
            completeness_score += 0.2 * (mentioned_aspects / len(aspects))
        
        # Vérifier la mention des sources
        for i in range(len(sources)):
            if f"source {i+1}" in synthesis.lower() or f"position {i+1}" in synthesis.lower():
                completeness_score += 0.1
        
        # Vérifier la structure comparative
        comparison_indicators = ["d'autre part", "en revanche", "tandis que", "alors que", "contrairement"]
        if any(indicator in synthesis.lower() for indicator in comparison_indicators):
            coherence_score += 0.2
        
        return {
            "coherence": min(coherence_score, 1.0),
            "completeness": min(completeness_score, 1.0)
        }
    
    def _determine_confidence_level(
        self,
        quality_metrics: Dict[str, float],
        sources_count: int
    ) -> str:
        """Détermine le niveau de confiance pour la comparaison"""
        avg_quality = (quality_metrics["coherence"] + quality_metrics["completeness"]) / 2
        
        if avg_quality >= 0.8 and sources_count >= 3:
            return "high"
        elif avg_quality >= 0.6 and sources_count >= 2:
            return "medium"
        else:
            return "low"


class SynthesizerAgent:
    """
    Agent Synthesizer - Expert en génération contextualisée et synthèse
    """
    
    def __init__(
        self,
        llm_client=None,
        agent_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'agent Synthesizer
        
        Args:
            llm_client: Client LLM pour la génération
            agent_config: Configuration de l'agent
        """
        self.llm_client = llm_client
        self.config = agent_config or {}
        
        # Configuration des outils
        self.tools = [
            ContextualSynthesisTool(llm_client=llm_client),
            ComparativeSynthesisTool(llm_client=llm_client)
        ]
        
        # Création de l'agent CrewAI
        self.agent = Agent(
            role="Expert en Synthèse et Génération Contextuelle",
            goal="Créer des synthèses cohérentes et informatives en combinant multiples sources",
            backstory="""Tu es un expert en analyse et synthèse d'informations complexes. 
            Tu excelles à combiner des informations provenant de sources diverses pour créer 
            des synthèses claires, structurées et nuancées qui répondent précisément aux 
            besoins de l'utilisateur.""",
            tools=self.tools,
            verbose=self.config.get("verbose", True),
            memory=True,
            max_iter=self.config.get("max_iterations", 3),
            max_execution_time=self.config.get("max_execution_time", 90)
        )
        
        logger.info("Agent Synthesizer initialisé avec succès")
    
    def synthesize(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        synthesis_type: str = "contextual",
        **kwargs
    ) -> SynthesisResult:
        """
        Génère une synthèse à partir des sources
        
        Args:
            query: Question/demande de l'utilisateur
            sources: Sources d'information
            synthesis_type: Type de synthèse ('contextual' ou 'comparative')
            **kwargs: Arguments spécifiques au type
            
        Returns:
            SynthesisResult avec synthèse générée
        """
        try:
            logger.info(f"Début synthèse {synthesis_type} pour: {query}")
            
            if synthesis_type == "comparative":
                tool = next(t for t in self.tools if t.name == "comparative_synthesis")
                result = tool._run(query=query, sources=sources, **kwargs)
            else:
                tool = next(t for t in self.tools if t.name == "contextual_synthesis")
                result = tool._run(query=query, sources=sources, **kwargs)
            
            logger.info(f"Synthèse générée: {result.word_count} mots, confiance: {result.confidence_level}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la synthèse: {e}")
            return SynthesisResult(
                synthesis="",
                coherence_score=0,
                completeness_score=0,
                confidence_level="error",
                word_count=0,
                metadata={"error": str(e)}
            )
    
    def create_task(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        synthesis_requirements: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Crée une tâche CrewAI pour la synthèse
        
        Args:
            query: Question/demande
            sources: Sources d'information
            synthesis_requirements: Exigences spécifiques
            
        Returns:
            Task CrewAI configurée
        """
        requirements = synthesis_requirements or {}
        
        task_description = f"""
        Synthétiser les informations des sources pour répondre à: "{query}"
        
        Sources disponibles: {len(sources)} documents
        
        Exigences:
        - Type: {requirements.get('type', 'contextual')}
        - Style: {requirements.get('style', 'comprehensive')}
        - Longueur max: {requirements.get('max_length', 500)} mots
        - Citations: {requirements.get('include_citations', True)}
        - Focus: {requirements.get('focus_areas', 'tous aspects')}
        
        Instructions:
        1. Analyser toutes les sources fournies
        2. Identifier les informations pertinentes pour la requête
        3. Synthétiser de manière cohérente et structurée
        4. Inclure les références appropriées
        5. Évaluer la qualité et la complétude
        
        Format de sortie: JSON avec synthèse complète et métriques
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="JSON contenant la synthèse avec évaluation qualité"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance de l'agent"""
        return {
            "agent_type": "synthesizer",
            "tools_count": len(self.tools),
            "llm_client_status": "connected" if self.llm_client else "disconnected",
            "supported_synthesis_types": ["contextual", "comparative"],
            "supported_styles": ["comprehensive", "concise", "analytical", "narrative", "academic", "practical"],
            "timestamp": datetime.now().isoformat()
        }
