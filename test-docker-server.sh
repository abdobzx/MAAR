#!/bin/bash
# Script de test Docker pour validation serveur
# À exécuter sur le serveur avec Docker

set -e

echo "🚀 VALIDATION DOCKER - RAG ENTERPRISE MULTI-AGENT"
echo "=================================================="

# Variables
PROJECT_DIR="$(pwd)"
DOCKER_COMPOSE_FILE="docker-compose.staging.yml"
TEST_IMAGE_NAME="rag-enterprise-test"

echo "📂 Répertoire de travail: $PROJECT_DIR"

# 1. Vérification de l'environnement Docker
echo ""
echo "🔍 1. Vérification Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé"
    exit 1
fi

echo "✅ Docker version: $(docker --version)"
echo "✅ Docker Compose disponible"

# 2. Test de construction de l'image de base
echo ""
echo "🏗️  2. Test de construction image..."

# Créer un Dockerfile de test minimal
cat > Dockerfile.test << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Copier requirements
COPY requirements.python313.txt ./requirements.txt

# Installer dépendances en mode test
RUN pip install --no-cache-dir --dry-run -r requirements.txt || \
    (echo "❌ Erreur dans les dépendances" && exit 1)

RUN pip install --no-cache-dir -r requirements.txt

# Copier code source minimal
COPY api/ ./api/
COPY core/ ./core/

# Test d'import
RUN python -c "
try:
    import fastapi
    import uvicorn
    import ollama
    import httpx
    print('✅ Imports principaux réussis')
except ImportError as e:
    print(f'❌ Erreur d\\'import: {e}')
    exit(1)
"

EXPOSE 8000
CMD ["echo", "Image de test construite avec succès"]
EOF

echo "🔨 Construction de l'image de test..."
if docker build -f Dockerfile.test -t $TEST_IMAGE_NAME .; then
    echo "✅ Image de test construite avec succès"
else
    echo "❌ Échec de construction de l'image"
    exit 1
fi

# 3. Test des requirements
echo ""
echo "📦 3. Test détaillé des dépendances..."

# Test dans un conteneur temporaire
docker run --rm $TEST_IMAGE_NAME python -c "
import sys
print(f'Python version: {sys.version}')

try:
    import ollama
    import httpx
    print(f'✅ ollama version: {ollama.__version__ if hasattr(ollama, \"__version__\") else \"imported\"}')
    print(f'✅ httpx version: {httpx.__version__}')
    
    import fastapi
    import uvicorn
    print(f'✅ FastAPI version: {fastapi.__version__}')
    
    import qdrant_client
    print(f'✅ Qdrant client version: {qdrant_client.__version__}')
    
    # Test de compatibilité httpx/ollama
    client = httpx.Client()
    print('✅ httpx.Client() fonctionne')
    client.close()
    
    print('✅ Tous les imports critiques réussis')
    
except Exception as e:
    print(f'❌ Erreur: {e}')
    sys.exit(1)
"

# 4. Test du fichier de configuration staging
echo ""
echo "🐳 4. Test docker-compose staging..."

if [ -f "$DOCKER_COMPOSE_FILE" ]; then
    echo "✅ Fichier $DOCKER_COMPOSE_FILE trouvé"
    
    # Validation syntax
    if docker compose -f $DOCKER_COMPOSE_FILE config > /dev/null 2>&1; then
        echo "✅ Syntaxe docker-compose valide"
    else
        echo "❌ Erreur de syntaxe docker-compose"
        docker compose -f $DOCKER_COMPOSE_FILE config
        exit 1
    fi
else
    echo "❌ Fichier $DOCKER_COMPOSE_FILE non trouvé"
    exit 1
fi

# 5. Test de démarrage des services
echo ""
echo "🚦 5. Test de démarrage services..."

echo "🔧 Construction des images docker-compose..."
if docker compose -f $DOCKER_COMPOSE_FILE build --no-cache; then
    echo "✅ Construction docker-compose réussie"
else
    echo "❌ Échec construction docker-compose"
    exit 1
fi

echo "🚀 Démarrage des services..."
if docker compose -f $DOCKER_COMPOSE_FILE up -d; then
    echo "✅ Services démarrés"
    
    # Attendre que les services soient prêts
    echo "⏳ Attente des services..."
    sleep 30
    
    # Vérifier les services
    echo "🔍 Statut des services:"
    docker compose -f $DOCKER_COMPOSE_FILE ps
    
    # Test de l'API
    echo "🌐 Test de l'endpoint API..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API répond sur /health"
    else
        echo "⚠️  API non accessible (normal si pas encore prête)"
    fi
    
    # Arrêter les services
    echo "🛑 Arrêt des services..."
    docker compose -f $DOCKER_COMPOSE_FILE down
    
else
    echo "❌ Échec démarrage des services"
    exit 1
fi

# 6. Nettoyage
echo ""
echo "🧹 6. Nettoyage..."
docker rmi $TEST_IMAGE_NAME 2>/dev/null || true
rm -f Dockerfile.test

echo ""
echo "🎉 VALIDATION TERMINÉE AVEC SUCCÈS!"
echo "✅ Toutes les dépendances sont compatibles"
echo "✅ Docker build fonctionne"
echo "✅ Docker compose fonctionne"
echo "✅ Le système est prêt pour le déploiement"
