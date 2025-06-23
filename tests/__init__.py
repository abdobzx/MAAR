"""
Tests for Enterprise RAG System
===============================

This package contains comprehensive tests for the Enterprise RAG System,
including unit tests, integration tests, and load tests.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator

# Configuration pytest pour les tests asynchrones
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Créer une boucle d'événements pour la session de test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def app():
    """Fixture pour l'application FastAPI."""
    from api.main import app
    return app


@pytest.fixture(scope="session")
async def db_session():
    """Fixture pour la session de base de données de test."""
    from database.manager import DatabaseManager
    
    db_manager = DatabaseManager(test_mode=True)
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        yield session
    
    await db_manager.close()
