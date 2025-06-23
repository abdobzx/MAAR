"""
Package de gestion des LLMs locaux via Ollama.
Support pour LLaMA3, Mistral, Phi-3, Code Llama et autres modèles.
"""

from .ollama.client import OllamaClient
from .models.manager import ModelManager
from .pooling.pool import LLMPool

__all__ = [
    "OllamaClient",
    "ModelManager", 
    "LLMPool"
]

__version__ = "1.0.0"
