"""
API Gateway FastAPI pour la plateforme MAR.
Unifie l'accès aux agents et orchestrateur.
"""

from .main import create_app

__all__ = ["create_app"]
__version__ = "1.0.0"
