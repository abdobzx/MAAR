#!/bin/bash
# Script pour corriger les conflits de ports et les conteneurs orphelins

echo "=== Correction des conflits de ports et des conteneurs orphelins ==="

# 1. Arrêter tous les conteneurs, y compris les orphelins
echo "1. Arrêt de tous les conteneurs Docker, y compris les orphelins..."
docker-compose down --remove-orphans
echo "✓ Tous les conteneurs ont été arrêtés"

# 2. Vérifier si quelque chose utilise encore le port 3000
echo "2. Vérification si le port 3000 est toujours utilisé..."
if command -v lsof &> /dev/null; then
    PROCESS=$(sudo lsof -i :3000 -t)
elif command -v netstat &> /dev/null; then
    PROCESS=$(sudo netstat -tuln | grep 3000)
else
    PROCESS=""
    echo "⚠️ Impossible de vérifier si le port 3000 est utilisé (lsof et netstat non disponibles)"
fi

if [ ! -z "$PROCESS" ]; then
    echo "⚠️ Le port 3000 est toujours utilisé. Modification du port de Grafana..."
    # Modifier le port de Grafana dans docker-compose.yml
    sed -i 's/- "3000:3000"/- "3002:3000"/' docker-compose.yml
    echo "✓ Port de Grafana modifié de 3000 à 3002 dans docker-compose.yml"
else
    echo "✓ Le port 3000 est disponible"
fi

# 3. Vérification des permissions du répertoire data
echo "3. Vérification des permissions du répertoire de données..."
mkdir -p data/vector_store
chmod -R 777 data
echo "✓ Permissions du répertoire data vérifiées et corrigées"

# 4. Redémarrer les conteneurs
echo "4. Redémarrage des conteneurs..."
docker-compose up -d
echo "✓ Les conteneurs ont été redémarrés"

# 5. Vérifier l'état des conteneurs
echo "5. Vérification de l'état des conteneurs..."
docker-compose ps
echo ""

# 6. Vérifier les logs de mar-api
echo "6. Vérification des logs de mar-api..."
docker logs mar-api --tail 20
echo ""

echo "=== Correction terminée ==="
echo "Si vous avez besoin d'accéder à Grafana, il est maintenant disponible sur le port 3002"
