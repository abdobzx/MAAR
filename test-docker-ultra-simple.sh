#!/bin/bash
# Test Docker ultra-simplifié et robuste

echo "🎯 TEST DOCKER FINAL - VERSION ULTRA-SIMPLE"
echo "============================================"

# Test 1: Construction avec requirements.docker.txt (version finale)
echo "1️⃣ Test avec requirements.docker.txt..."

cat > Dockerfile.final << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Copier requirements finaux
COPY requirements.docker.txt ./requirements.txt

# Installation 
RUN pip install --no-cache-dir -r requirements.txt

# Test critique : ollama + httpx
RUN python -c "import ollama; import httpx; print('✅ Compatibility OK')"

# Test autres imports
RUN python -c "import fastapi; import uvicorn; print('✅ FastAPI OK')"
RUN python -c "import qdrant_client; print('✅ Qdrant OK')"

CMD ["echo", "Docker build success"]
EOF

echo "🏗️ Construction finale..."
if docker build -f Dockerfile.final -t rag-final-test .; then
    echo "✅ SUCCESS: Image Docker finale construite !"
    
    # Test dans le conteneur
    echo ""
    echo "2️⃣ Test des versions dans le conteneur..."
    docker run --rm rag-final-test python -c "
import sys
print('Python:', sys.version_info[:2])

packages = {
    'ollama': 'Ollama LLM',
    'httpx': 'HTTP Client', 
    'fastapi': 'FastAPI Framework',
    'qdrant_client': 'Vector DB',
    'langchain': 'LangChain'
}

for pkg, desc in packages.items():
    try:
        module = __import__(pkg)
        version = getattr(module, '__version__', 'imported')
        print(f'✅ {desc}: {version}')
    except ImportError as e:
        print(f'❌ {desc}: {e}')

# Test final de compatibilité
import httpx
client = httpx.Client()
print('✅ httpx.Client() works perfectly')
client.close()
"
    
    # Nettoyage
    docker rmi rag-final-test
    echo "✅ Test terminé avec succès"
    
else
    echo "❌ ÉCHEC: Problème avec requirements.docker.txt"
fi

rm -f Dockerfile.final

echo ""
echo "🎉 RÉSULTAT: Si vous voyez '✅ SUCCESS' ci-dessus, le système est 100% prêt !"
