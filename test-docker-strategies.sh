#!/bin/bash

# Script pour tester différentes approches Docker
# Usage: ./test-docker-strategies.sh [monolith|microservices|hybrid]

set -e

STRATEGY=${1:-"monolith"}
PROJECT_NAME="rag-test"

echo "🚀 Test de la stratégie Docker: $STRATEGY"

case $STRATEGY in
  "monolith")
    echo "📦 Lancement avec approche monolithe (actuelle)..."
    docker-compose -f docker-compose.staging.yml -p $PROJECT_NAME up -d
    ;;
    
  "microservices")
    echo "🔧 Lancement avec microservices séparés..."
    
    # Build des images spécialisées
    echo "Building API image..."
    docker build -f infrastructure/docker/api.Dockerfile -t rag-api:latest .
    
    echo "Building Agents image..."
    docker build -f infrastructure/docker/agents.Dockerfile -t rag-agents:latest .
    
    echo "Building Scheduler image..."
    docker build -f infrastructure/docker/scheduler.Dockerfile -t rag-scheduler:latest .
    
    # Lancement avec docker-compose hybride
    docker-compose -f docker-compose.hybrid.yml -p $PROJECT_NAME up -d
    ;;
    
  "hybrid")
    echo "🔄 Lancement avec approche hybride..."
    docker-compose -f docker-compose.hybrid.yml -p $PROJECT_NAME up -d
    ;;
    
  *)
    echo "❌ Stratégie inconnue: $STRATEGY"
    echo "Usage: $0 [monolith|microservices|hybrid]"
    exit 1
    ;;
esac

echo ""
echo "✅ Containers lancés avec la stratégie: $STRATEGY"
echo ""
echo "📊 Status des containers:"
docker-compose -p $PROJECT_NAME ps

echo ""
echo "🔍 Pour tester l'API:"
echo "curl http://localhost:8000/health"

echo ""
echo "🛑 Pour arrêter:"
echo "docker-compose -p $PROJECT_NAME down"
