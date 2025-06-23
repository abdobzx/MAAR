"""
Agent Retriever - Responsable de la récupération vectorielle et de la recherche sémantique.
"""

from typing import List, Dict, Any, Optional
from crewai import Agent, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    """Résultat d'une recherche vectorielle"""
    documents: List[Dict[str, Any]] = Field(description="Documents récupérés")
    scores: List[float] = Field(description="Scores de similarité")
    query: str = Field(description="Requête originale")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorSearchTool(BaseTool):
    """Outil de recherche vectorielle"""
    
    name: str = "vector_search"
    description: str = "Recherche des documents similaires dans l'index vectoriel"
    
    def __init__(self, vector_store=None, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = vector_store
    
    def _run(
        self, 
        query: str, 
        top_k: int = 5, 
        threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Exécute une recherche vectorielle
        
        Args:
            query: Requête de recherche
            top_k: Nombre de résultats à retourner
            threshold: Seuil de similarité minimum
            filters: Filtres optionnels sur les métadonnées
            
        Returns:
            RetrievalResult avec documents et scores
        """
        try:
            logger.info(f"Recherche vectorielle pour: {query}")
            
            if not self.vector_store:
                logger.warning("Vector store non initialisé")
                return RetrievalResult(
                    documents=[],
                    scores=[],
                    query=query,
                    metadata={"error": "Vector store non disponible"}
                )
            
            # Recherche dans le vector store
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
                score_threshold=threshold,
                filter=filters
            )
            
            documents = []
            scores = []
            
            for doc, score in results:
                if score >= threshold:
                    documents.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "source": doc.metadata.get("source", "unknown")
                    })
                    scores.append(float(score))
            
            logger.info(f"Trouvé {len(documents)} documents pertinents")
            
            return RetrievalResult(
                documents=documents,
                scores=scores,
                query=query,
                metadata={
                    "total_results": len(results),
                    "filtered_results": len(documents),
                    "avg_score": sum(scores) / len(scores) if scores else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche vectorielle: {e}")
            return RetrievalResult(
                documents=[],
                scores=[],
                query=query,
                metadata={"error": str(e)}
            )


class ContextualSearchTool(BaseTool):
    """Outil de recherche contextuelle avancée"""
    
    name: str = "contextual_search"
    description: str = "Recherche contextuelle avec expansion de requête et re-ranking"
    
    def __init__(self, vector_store=None, llm_client=None, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = vector_store
        self.llm_client = llm_client
    
    def _run(
        self,
        query: str,
        context: Optional[str] = None,
        expand_query: bool = True,
        re_rank: bool = True,
        top_k: int = 10
    ) -> RetrievalResult:
        """
        Recherche contextuelle avec expansion et re-ranking
        
        Args:
            query: Requête originale
            context: Contexte additionnel
            expand_query: Activer l'expansion de requête
            re_rank: Activer le re-ranking
            top_k: Nombre de résultats
            
        Returns:
            RetrievalResult optimisé
        """
        try:
            effective_query = query
            
            # Expansion de requête avec LLM
            if expand_query and self.llm_client:
                expansion_prompt = f"""
                Requête originale: {query}
                Contexte: {context or 'Aucun'}
                
                Génère 3-5 variantes de cette requête pour améliorer la recherche vectorielle.
                Retourne seulement les variantes, une par ligne.
                """
                
                try:
                    expanded = self.llm_client.generate(expansion_prompt)
                    variants = [line.strip() for line in expanded.split('\n') if line.strip()]
                    effective_query = f"{query} {' '.join(variants[:3])}"
                    logger.info(f"Requête étendue: {effective_query}")
                except Exception as e:
                    logger.warning(f"Erreur expansion requête: {e}")
            
            # Recherche initiale
            search_tool = VectorSearchTool(vector_store=self.vector_store)
            initial_results = search_tool._run(
                query=effective_query,
                top_k=top_k * 2,  # Récupérer plus pour le re-ranking
                threshold=0.5  # Seuil plus bas pour le re-ranking
            )
            
            if not initial_results.documents or not re_rank:
                return initial_results
            
            # Re-ranking avec LLM
            if self.llm_client and len(initial_results.documents) > 1:
                try:
                    reranked = self._rerank_documents(
                        query=query,
                        documents=initial_results.documents,
                        scores=initial_results.scores,
                        top_k=top_k
                    )
                    
                    return RetrievalResult(
                        documents=reranked["documents"],
                        scores=reranked["scores"],
                        query=query,
                        metadata={
                            **initial_results.metadata,
                            "reranked": True,
                            "original_count": len(initial_results.documents)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Erreur re-ranking: {e}")
            
            # Retourner les résultats initiaux si re-ranking échoue
            return RetrievalResult(
                documents=initial_results.documents[:top_k],
                scores=initial_results.scores[:top_k],
                query=query,
                metadata=initial_results.metadata
            )
            
        except Exception as e:
            logger.error(f"Erreur recherche contextuelle: {e}")
            return RetrievalResult(
                documents=[],
                scores=[],
                query=query,
                metadata={"error": str(e)}
            )
    
    def _rerank_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        scores: List[float],
        top_k: int
    ) -> Dict[str, List]:
        """Re-classe les documents avec LLM"""
        
        # Préparer le prompt de re-ranking
        docs_text = ""
        for i, doc in enumerate(documents[:10]):  # Limiter à 10 pour le LLM
            docs_text += f"Document {i+1}:\n{doc['content'][:500]}...\n\n"
        
        rerank_prompt = f"""
        Requête: {query}
        
        Documents à classer par pertinence:
        {docs_text}
        
        Classe ces documents du plus pertinent au moins pertinent pour la requête.
        Retourne seulement les numéros des documents dans l'ordre (ex: 3,1,5,2,4).
        """
        
        try:
            response = self.llm_client.generate(rerank_prompt)
            # Parser la réponse pour extraire l'ordre
            order_str = response.strip().split('\n')[0]
            order_indices = [int(x.strip()) - 1 for x in order_str.split(',') if x.strip().isdigit()]
            
            # Réorganiser selon le nouvel ordre
            reranked_docs = []
            reranked_scores = []
            
            for idx in order_indices[:top_k]:
                if 0 <= idx < len(documents):
                    reranked_docs.append(documents[idx])
                    reranked_scores.append(scores[idx] * 1.1)  # Bonus pour le re-ranking
            
            return {
                "documents": reranked_docs,
                "scores": reranked_scores
            }
            
        except Exception as e:
            logger.warning(f"Erreur parsing re-ranking: {e}")
            return {
                "documents": documents[:top_k],
                "scores": scores[:top_k]
            }


class RetrieverAgent:
    """
    Agent Retriever - Expert en récupération vectorielle et recherche sémantique
    """
    
    def __init__(
        self,
        vector_store=None,
        llm_client=None,
        agent_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'agent Retriever
        
        Args:
            vector_store: Instance du vector store
            llm_client: Client LLM pour l'expansion de requête
            agent_config: Configuration de l'agent
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.config = agent_config or {}
        
        # Configuration des outils
        self.tools = [
            VectorSearchTool(vector_store=vector_store),
            ContextualSearchTool(vector_store=vector_store, llm_client=llm_client)
        ]
        
        # Création de l'agent CrewAI
        self.agent = Agent(
            role="Expert en Récupération d'Information",
            goal="Récupérer les documents les plus pertinents pour répondre aux requêtes utilisateur",
            backstory="""Tu es un expert en recherche d'information avec une spécialisation 
            en recherche vectorielle et sémantique. Tu excelles à comprendre les nuances des 
            requêtes et à identifier les documents les plus pertinents dans de vastes corpus.""",
            tools=self.tools,
            verbose=self.config.get("verbose", True),
            memory=True,
            max_iter=self.config.get("max_iterations", 3),
            max_execution_time=self.config.get("max_execution_time", 60)
        )
        
        logger.info("Agent Retriever initialisé avec succès")
    
    def retrieve(
        self,
        query: str,
        context: Optional[str] = None,
        retrieval_strategy: str = "contextual",
        **kwargs
    ) -> RetrievalResult:
        """
        Récupère des documents pertinents pour une requête
        
        Args:
            query: Requête de recherche
            context: Contexte optionnel
            retrieval_strategy: Stratégie ('basic' ou 'contextual')
            **kwargs: Arguments additionnels
            
        Returns:
            RetrievalResult avec documents récupérés
        """
        try:
            logger.info(f"Début récupération pour: {query}")
            
            if retrieval_strategy == "contextual":
                tool = next(t for t in self.tools if t.name == "contextual_search")
                result = tool._run(
                    query=query,
                    context=context,
                    **kwargs
                )
            else:
                tool = next(t for t in self.tools if t.name == "vector_search")
                result = tool._run(query=query, **kwargs)
            
            logger.info(f"Récupération terminée: {len(result.documents)} documents")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération: {e}")
            return RetrievalResult(
                documents=[],
                scores=[],
                query=query,
                metadata={"error": str(e)}
            )
    
    def create_task(self, query: str, context: Optional[str] = None) -> Task:
        """
        Crée une tâche CrewAI pour la récupération
        
        Args:
            query: Requête de recherche
            context: Contexte optionnel
            
        Returns:
            Task CrewAI configurée
        """
        task_description = f"""
        Récupérer les documents les plus pertinents pour la requête: "{query}"
        
        {"Contexte: " + context if context else ""}
        
        Instructions:
        1. Analyser la requête pour comprendre l'intention
        2. Utiliser la recherche contextuelle si approprié
        3. Filtrer les résultats selon la pertinence
        4. Retourner les documents avec leurs scores
        
        Format de sortie: Structure JSON avec documents et métadonnées
        """
        
        return Task(
            description=task_description,
            agent=self.agent,
            expected_output="JSON contenant les documents récupérés avec scores et métadonnées"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance de l'agent"""
        return {
            "agent_type": "retriever",
            "tools_count": len(self.tools),
            "vector_store_status": "connected" if self.vector_store else "disconnected",
            "llm_client_status": "connected" if self.llm_client else "disconnected",
            "timestamp": datetime.now().isoformat()
        }
