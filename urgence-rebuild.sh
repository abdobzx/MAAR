#!/bin/bash

# 🚨 SCRIPT D'URGENCE - ARRÊT ET REBUILD RAPIDE
# Utilisation : ./urgence-rebuild.sh sur serveur Ubuntu

set -e

echo "🚨 URGENCE : Arrêt du build Docker lent (43 min)"
echo "=============================================="

echo "📍 1. Arrêt des conteneurs en cours..."
docker-compose down --remove-orphans || true

echo "📍 2. Nettoyage du cache Docker..."
docker system prune -f
docker builder prune -f

echo "📍 3. Vérification de l'espace disque..."
df -h

echo "📍 4. Build optimisé avec Dockerfile.fast..."
if [ -f "Dockerfile.fast" ] && [ -f "requirements.fast.txt" ]; then
    echo "✅ Fichiers optimisés trouvés"
    time docker build -f Dockerfile.fast -t rag-api-fast .
else
    echo "❌ Fichiers optimisés manquants - Build standard"
    time docker-compose build --no-cache
fi

echo "📍 5. Démarrage des services..."
if [ -f "docker-compose.fast.yml" ]; then
    docker-compose -f docker-compose.fast.yml up -d
else
    docker-compose up -d
fi

echo "📍 6. Vérification du déploiement..."
sleep 10
curl -f http://localhost:8000/health || echo "❌ Health check échoué"

echo "📍 7. Status final..."
docker ps
docker-compose logs --tail=20

echo "✅ Rebuild d'urgence terminé !"
echo "Temps total : $(date)"
