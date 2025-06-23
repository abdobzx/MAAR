"""
Package orchestrateur CrewAI pour coordonner les agents spécialisés.
"""

from .crew.mar_crew import MARCrew
from .tasks.rag_tasks import RAGTaskManager
from .tools.shared_tools import SharedToolsManager

__all__ = [
    "MARCrew",
    "RAGTaskManager", 
    "SharedToolsManager"
]

__version__ = "1.0.0"
