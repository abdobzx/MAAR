#!/bin/bash

# Script d'arrêt d'urgence et build rapide
echo "🚨 ARRÊT D'URGENCE - BUILD TROP LENT"
echo "===================================="

echo "⏹️  Arrêt du build en cours..."
docker-compose down --remove-orphans

echo "🧹 Nettoyage des images partielles..."
docker system prune -f

echo "🚀 Lancement du build rapide optimisé..."

# Build avec le Dockerfile rapide
echo "📦 Build de l'image rapide..."
docker build -f Dockerfile.fast -t rag-api-fast . || {
    echo "❌ Échec du build rapide"
    exit 1
}

echo "✅ Build rapide terminé!"
echo "🔍 Test de l'image:"
docker run --rm rag-api-fast python -c "
import fastapi
import pydantic
import ollama
import langchain
import langsmith
print('✅ Toutes les dépendances critiques importées!')
print('✅ Image fonctionnelle!')
"

echo ""
echo "🎯 SOLUTIONS POUR ACCÉLÉRER LE BUILD:"
echo "1. Utiliser requirements.txt au lieu de requirements.staging.txt"
echo "2. Build avec cache Docker: docker build --cache-from rag-api-fast"
echo "3. Utiliser requirements minimal avec versions fixes"

echo ""
echo "📋 PROCHAINES ÉTAPES:"
echo "   docker run -p 8000:8000 rag-api-fast  # Test rapide"
echo "   ./deploy-production.sh --fast          # Déploiement rapide"
