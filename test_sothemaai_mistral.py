#!/usr/bin/env python3
"""
Test rapide pour valider SothemaAI avec Mistral 7B
et préparer la migration vers LLAMA 4
"""

import asyncio
import sys
import os
sys.path.append('/Users/abderrahman/Documents/MAR')

from agents.vectorization.agent import VectorizationAgent, SothemaAIEmbeddingProvider
from core.config import settings
from core.models import Document, DocumentMetadata
from uuid import uuid4

async def test_sothemaai_mistral():
    """Test SothemaAI avec Mistral 7B"""
    
    print("🔍 Test SothemaAI avec Mistral 7B")
    print("=" * 50)
    
    try:
        # Initialiser l'agent de vectorisation
        agent = VectorizationAgent()
        
        # Vérifier les providers disponibles
        print(f"📋 Providers disponibles: {list(agent.embedding_providers.keys())}")
        print(f"🎯 Provider par défaut: {agent.default_provider.model_name}")
        
        # Test avec un document simple
        test_doc = Document(
            id=uuid4(),
            content="Ceci est un test pour valider l'intégration SothemaAI avec Mistral 7B. Le système devrait être capable de générer des embeddings de haute qualité.",
            metadata=DocumentMetadata(
                filename="test_mistral.txt",
                source="test",
                content_type="text/plain"
            )
        )
        
        print(f"\n📄 Test document: {test_doc.content[:100]}...")
        
        # Générer les embeddings
        chunks = await agent.vectorize_document(test_doc)
        
        print(f"\n✅ Vectorisation réussie!")
        print(f"📊 Nombre de chunks: {len(chunks)}")
        print(f"🔢 Dimension des embeddings: {len(chunks[0].embedding) if chunks else 'N/A'}")
        print(f"🏷️  Modèle utilisé: {chunks[0].metadata.get('embedding_model') if chunks else 'N/A'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sothemaai_mistral())
    if success:
        print("\n🎉 Test réussi! SothemaAI avec Mistral 7B fonctionne correctement.")
        print("🚀 Prêt pour la migration vers LLAMA 4!")
    else:
        print("\n⚠️  Test échoué. Vérifiez la configuration SothemaAI.")
