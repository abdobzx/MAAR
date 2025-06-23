"""
Package des agents IA spécialisés pour la plateforme MAR.
Chaque agent a un rôle spécifique dans le pipeline RAG.
"""

from .retriever.agent import RetrieverAgent
from .summarizer.agent import SummarizerAgent  
from .synthesizer.agent import SynthesizerAgent
from .critic.agent import CriticAgent
from .ranker.agent import RankerAgent

__all__ = [
    "RetrieverAgent",
    "SummarizerAgent", 
    "SynthesizerAgent",
    "CriticAgent",
    "RankerAgent"
]

__version__ = "1.0.0"
