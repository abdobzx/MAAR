"""
MARCrew - Orchestrateur principal pour coordonner les agents MAR.
"""

from typing import List, Dict, Any, Optional
from crewai import Crew, Process
from crewai.agent import Agent
from crewai.task import Task
import logging
from datetime import datetime
import json

# Import des agents
from agents.retriever.agent import RetrieverAgent
from agents.summarizer.agent import SummarizerAgent
from agents.synthesizer.agent import SynthesizerAgent
from agents.critic.agent import CriticAgent
from agents.ranker.agent import RankerAgent

logger = logging.getLogger(__name__)


class MARCrew:
    """
    Orchestrateur principal MAR (Multi-Agent RAG)
    Coordonne les agents pour des workflows RAG complets
    """
    
    def __init__(
        self,
        vector_store=None,
        llm_client=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le crew MAR
        
        Args:
            vector_store: Store vectoriel pour recherche
            llm_client: Client LLM pour génération
            config: Configuration du crew
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.config = config or {}
        
        # Initialisation des agents
        self.agents = self._initialize_agents()
        
        # Historique des exécutions
        self.execution_history = []
        
        logger.info("MARCrew initialisé avec succès")
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialise tous les agents spécialisés"""
        
        agent_config = self.config.get("agents", {})
        
        agents = {
            "retriever": RetrieverAgent(
                vector_store=self.vector_store,
                llm_client=self.llm_client,
                agent_config=agent_config.get("retriever", {})
            ),
            "summarizer": SummarizerAgent(
                llm_client=self.llm_client,
                agent_config=agent_config.get("summarizer", {})
            ),
            "synthesizer": SynthesizerAgent(
                llm_client=self.llm_client,
                agent_config=agent_config.get("synthesizer", {})
            ),
            "critic": CriticAgent(
                llm_client=self.llm_client,
                agent_config=agent_config.get("critic", {})
            ),
            "ranker": RankerAgent(
                llm_client=self.llm_client,
                agent_config=agent_config.get("ranker", {})
            )
        }
        
        logger.info(f"Agents initialisés: {list(agents.keys())}")
        return agents
    
    def execute_simple_rag(
        self,
        query: str,
        max_documents: int = 5,
        include_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Exécute un workflow RAG simple
        
        Args:
            query: Requête utilisateur
            max_documents: Nombre max de documents à récupérer
            include_validation: Inclure validation par le critic
            
        Returns:
            Résultat complet du workflow
        """
        try:
            execution_id = f"simple_rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Début workflow RAG simple [{execution_id}]: {query}")
            
            start_time = datetime.now()
            results = {
                "execution_id": execution_id,
                "query": query,
                "workflow_type": "simple_rag",
                "start_time": start_time.isoformat(),
                "steps": {}
            }
            
            # Étape 1: Récupération de documents
            logger.info("Étape 1: Récupération de documents")
            retrieval_result = self.agents["retriever"].retrieve(
                query=query,
                top_k=max_documents,
                retrieval_strategy="contextual"
            )
            
            results["steps"]["retrieval"] = {
                "status": "completed",
                "documents_found": len(retrieval_result.documents),
                "avg_score": sum(retrieval_result.scores) / len(retrieval_result.scores) if retrieval_result.scores else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            if not retrieval_result.documents:
                results["final_answer"] = "Aucun document pertinent trouvé pour cette requête."
                results["status"] = "completed_no_sources"
                return results
            
            # Étape 2: Synthèse contextuelle
            logger.info("Étape 2: Synthèse contextuelle")
            synthesis_result = self.agents["synthesizer"].synthesize(
                query=query,
                sources=retrieval_result.documents,
                synthesis_type="contextual",
                max_length=300,
                include_citations=True
            )
            
            results["steps"]["synthesis"] = {
                "status": "completed",
                "word_count": synthesis_result.word_count,
                "confidence_level": synthesis_result.confidence_level,
                "coherence_score": synthesis_result.coherence_score,
                "timestamp": datetime.now().isoformat()
            }
            
            # Étape 3: Validation (optionnelle)
            if include_validation and synthesis_result.synthesis:
                logger.info("Étape 3: Validation")
                validation_result = self.agents["critic"].validate(
                    content=synthesis_result.synthesis,
                    content_type="synthesis",
                    validation_level="standard",
                    reference_sources=retrieval_result.documents
                )
                
                results["steps"]["validation"] = {
                    "status": "completed",
                    "is_valid": validation_result.is_valid,
                    "overall_score": validation_result.overall_score,
                    "issues_count": len(validation_result.issues_found),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Si validation échoue, tenter une amélioration
                if not validation_result.is_valid and validation_result.suggestions:
                    logger.info("Tentative d'amélioration suite à validation")
                    improved_query = f"{query} (Améliorations: {'; '.join(validation_result.suggestions[:2])})"
                    
                    improved_synthesis = self.agents["synthesizer"].synthesize(
                        query=improved_query,
                        sources=retrieval_result.documents,
                        synthesis_type="contextual",
                        max_length=350,
                        include_citations=True
                    )
                    
                    if improved_synthesis.coherence_score > synthesis_result.coherence_score:
                        synthesis_result = improved_synthesis
                        results["steps"]["improvement"] = {
                            "status": "completed",
                            "improvement_applied": True,
                            "timestamp": datetime.now().isoformat()
                        }
            
            # Finalisation
            end_time = datetime.now()
            execution_duration = (end_time - start_time).total_seconds()
            
            results.update({
                "final_answer": synthesis_result.synthesis,
                "sources_used": retrieval_result.documents,
                "citations": synthesis_result.citations,
                "confidence_level": synthesis_result.confidence_level,
                "status": "completed",
                "end_time": end_time.isoformat(),
                "execution_duration": execution_duration,
                "metadata": {
                    "total_sources": len(retrieval_result.documents),
                    "synthesis_word_count": synthesis_result.word_count,
                    "validation_included": include_validation
                }
            })
            
            # Ajouter à l'historique
            self.execution_history.append(results)
            
            logger.info(f"Workflow RAG simple terminé [{execution_id}]: {execution_duration:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Erreur workflow RAG simple: {e}")
            return {
                "execution_id": execution_id if 'execution_id' in locals() else "error",
                "query": query,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def execute_comparative_rag(
        self,
        query: str,
        comparison_aspects: List[str],
        max_documents: int = 8
    ) -> Dict[str, Any]:
        """
        Exécute un workflow RAG comparatif
        
        Args:
            query: Requête de comparaison
            comparison_aspects: Aspects à comparer
            max_documents: Nombre max de documents
            
        Returns:
            Résultat de l'analyse comparative
        """
        try:
            execution_id = f"comparative_rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Début workflow RAG comparatif [{execution_id}]: {query}")
            
            start_time = datetime.now()
            results = {
                "execution_id": execution_id,
                "query": query,
                "comparison_aspects": comparison_aspects,
                "workflow_type": "comparative_rag",
                "start_time": start_time.isoformat(),
                "steps": {}
            }
            
            # Étape 1: Récupération étendue
            logger.info("Étape 1: Récupération pour comparaison")
            retrieval_result = self.agents["retriever"].retrieve(
                query=query,
                top_k=max_documents,
                retrieval_strategy="contextual",
                expand_query=True
            )
            
            results["steps"]["retrieval"] = {
                "status": "completed",
                "documents_found": len(retrieval_result.documents),
                "timestamp": datetime.now().isoformat()
            }
            
            if len(retrieval_result.documents) < 2:
                results["final_answer"] = "Pas assez de sources pour effectuer une comparaison."
                results["status"] = "insufficient_sources"
                return results
            
            # Étape 2: Classement par pertinence
            logger.info("Étape 2: Classement des sources")
            ranking_result = self.agents["ranker"].rank(
                items=retrieval_result.documents,
                ranking_type="relevance",
                query=query,
                ranking_method="tf_idf"
            )
            
            results["steps"]["ranking"] = {
                "status": "completed",
                "confidence_score": ranking_result.confidence_score,
                "timestamp": datetime.now().isoformat()
            }
            
            # Utiliser les meilleures sources
            top_sources = ranking_result.ranked_items[:6]
            
            # Étape 3: Synthèse comparative
            logger.info("Étape 3: Synthèse comparative")
            comparative_synthesis = self.agents["synthesizer"].synthesize(
                query=query,
                sources=top_sources,
                synthesis_type="comparative",
                comparison_aspects=comparison_aspects,
                include_conclusion=True
            )
            
            results["steps"]["comparative_synthesis"] = {
                "status": "completed",
                "word_count": comparative_synthesis.word_count,
                "confidence_level": comparative_synthesis.confidence_level,
                "timestamp": datetime.now().isoformat()
            }
            
            # Étape 4: Validation critique
            logger.info("Étape 4: Validation comparative")
            validation_result = self.agents["critic"].validate(
                content=comparative_synthesis.synthesis,
                content_type="synthesis",
                validation_level="standard",
                reference_sources=top_sources,
                quality_criteria=["objectivity", "balance", "evidence"]
            )
            
            results["steps"]["validation"] = {
                "status": "completed",
                "is_valid": validation_result.is_valid,
                "overall_score": validation_result.overall_score,
                "timestamp": datetime.now().isoformat()
            }
            
            # Finalisation
            end_time = datetime.now()
            execution_duration = (end_time - start_time).total_seconds()
            
            results.update({
                "final_answer": comparative_synthesis.synthesis,
                "sources_used": top_sources,
                "comparison_quality": {
                    "coherence_score": comparative_synthesis.coherence_score,
                    "completeness_score": comparative_synthesis.completeness_score,
                    "validation_score": validation_result.overall_score
                },
                "status": "completed",
                "end_time": end_time.isoformat(),
                "execution_duration": execution_duration
            })
            
            self.execution_history.append(results)
            
            logger.info(f"Workflow RAG comparatif terminé [{execution_id}]: {execution_duration:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Erreur workflow RAG comparatif: {e}")
            return {
                "execution_id": execution_id if 'execution_id' in locals() else "error",
                "query": query,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def execute_summarization_workflow(
        self,
        documents: List[Dict[str, Any]],
        summary_type: str = "abstractive",
        max_length: int = 200
    ) -> Dict[str, Any]:
        """
        Exécute un workflow de résumé de documents
        
        Args:
            documents: Documents à résumer
            summary_type: Type de résumé
            max_length: Longueur maximum
            
        Returns:
            Résultats du résumé
        """
        try:
            execution_id = f"summarization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Début workflow résumé [{execution_id}]: {len(documents)} documents")
            
            start_time = datetime.now()
            results = {
                "execution_id": execution_id,
                "workflow_type": "summarization",
                "documents_count": len(documents),
                "start_time": start_time.isoformat(),
                "steps": {}
            }
            
            # Étape 1: Résumés individuels
            logger.info("Étape 1: Résumés individuels")
            individual_summaries = []
            
            for i, doc in enumerate(documents):
                content = doc.get("content", "")
                if content:
                    summary_result = self.agents["summarizer"].summarize(
                        text=content,
                        summary_type=summary_type,
                        max_length=max_length
                    )
                    
                    individual_summaries.append({
                        "document_index": i,
                        "summary": summary_result.summary,
                        "compression_ratio": summary_result.compression_ratio,
                        "confidence_score": summary_result.confidence_score
                    })
            
            results["steps"]["individual_summaries"] = {
                "status": "completed",
                "summaries_count": len(individual_summaries),
                "avg_compression": sum(s["compression_ratio"] for s in individual_summaries) / len(individual_summaries) if individual_summaries else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            # Étape 2: Résumé global
            logger.info("Étape 2: Résumé global")
            if individual_summaries:
                combined_text = "\n\n".join([s["summary"] for s in individual_summaries])
                
                global_summary = self.agents["summarizer"].summarize(
                    text=combined_text,
                    summary_type=summary_type,
                    max_length=max_length * 2,
                    style="comprehensive"
                )
                
                results["steps"]["global_summary"] = {
                    "status": "completed",
                    "word_count": global_summary.word_count,
                    "confidence_score": global_summary.confidence_score,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Étape 3: Validation qualité
            logger.info("Étape 3: Validation des résumés")
            validation_results = []
            
            for summary in individual_summaries[:3]:  # Valider les 3 premiers
                validation = self.agents["critic"].validate(
                    content=summary["summary"],
                    content_type="summary",
                    validation_level="basic"
                )
                validation_results.append(validation.overall_score)
            
            avg_quality = sum(validation_results) / len(validation_results) if validation_results else 0
            
            results["steps"]["validation"] = {
                "status": "completed",
                "avg_quality_score": avg_quality,
                "validated_summaries": len(validation_results),
                "timestamp": datetime.now().isoformat()
            }
            
            # Finalisation
            end_time = datetime.now()
            execution_duration = (end_time - start_time).total_seconds()
            
            results.update({
                "individual_summaries": individual_summaries,
                "global_summary": global_summary.summary if 'global_summary' in locals() else None,
                "quality_metrics": {
                    "avg_compression_ratio": results["steps"]["individual_summaries"]["avg_compression"],
                    "avg_quality_score": avg_quality,
                    "global_confidence": global_summary.confidence_score if 'global_summary' in locals() else 0
                },
                "status": "completed",
                "end_time": end_time.isoformat(),
                "execution_duration": execution_duration
            })
            
            self.execution_history.append(results)
            
            logger.info(f"Workflow résumé terminé [{execution_id}]: {execution_duration:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Erreur workflow résumé: {e}")
            return {
                "execution_id": execution_id if 'execution_id' in locals() else "error",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def create_crew_for_workflow(
        self,
        workflow_type: str,
        agents_needed: List[str]
    ) -> Crew:
        """
        Crée un crew CrewAI pour un workflow spécifique
        
        Args:
            workflow_type: Type de workflow
            agents_needed: Liste des agents nécessaires
            
        Returns:
            Crew CrewAI configuré
        """
        try:
            # Sélectionner les agents
            selected_agents = []
            for agent_name in agents_needed:
                if agent_name in self.agents:
                    selected_agents.append(self.agents[agent_name].agent)
            
            if not selected_agents:
                raise ValueError("Aucun agent valide sélectionné")
            
            # Configuration du processus
            process_type = Process.sequential  # Par défaut séquentiel
            if workflow_type in ["comparative_rag", "complex_analysis"]:
                process_type = Process.hierarchical
            
            # Créer le crew
            crew = Crew(
                agents=selected_agents,
                process=process_type,
                verbose=self.config.get("verbose", True),
                memory=self.config.get("enable_memory", True)
            )
            
            logger.info(f"Crew créé pour {workflow_type}: {len(selected_agents)} agents")
            return crew
            
        except Exception as e:
            logger.error(f"Erreur création crew: {e}")
            raise
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'exécution"""
        if not self.execution_history:
            return {"total_executions": 0}
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for exec in self.execution_history if exec.get("status") == "completed")
        
        avg_duration = 0
        durations = [exec.get("execution_duration", 0) for exec in self.execution_history if exec.get("execution_duration")]
        if durations:
            avg_duration = sum(durations) / len(durations)
        
        workflow_types = {}
        for exec in self.execution_history:
            wf_type = exec.get("workflow_type", "unknown")
            workflow_types[wf_type] = workflow_types.get(wf_type, 0) + 1
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "avg_execution_duration": avg_duration,
            "workflow_types": workflow_types,
            "last_execution": self.execution_history[-1].get("end_time") if self.execution_history else None
        }
    
    def get_agent_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de tous les agents"""
        metrics = {}
        for agent_name, agent_instance in self.agents.items():
            metrics[agent_name] = agent_instance.get_metrics()
        
        return metrics
