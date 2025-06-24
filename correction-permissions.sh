#!/bin/bash
# Script pour corriger les problèmes de permissions des répertoires de données

echo "=== Correction des problèmes de permissions des répertoires de données ==="

# 1. Vérification et sauvegarde du Dockerfile
echo "1. Sauvegarde du Dockerfile..."
cp Dockerfile Dockerfile.backup.$(date +%s)
echo "✓ Sauvegarde créée: Dockerfile.backup.$(date +%s)"

# 2. Modification du Dockerfile pour créer les répertoires nécessaires
echo "2. Modification du Dockerfile pour créer les répertoires de données..."
if ! grep -q "mkdir -p /app/data/vector_store" Dockerfile; then
    # Ajouter la commande mkdir avant la création de l'utilisateur
    sed -i '/# Création d'\''un utilisateur non-root/i # Création des répertoires nécessaires\nRUN mkdir -p /app/data/vector_store\n' Dockerfile
    echo "✓ Commande pour créer le répertoire /app/data/vector_store ajoutée au Dockerfile"
else
    echo "✓ Le répertoire /app/data/vector_store est déjà créé dans le Dockerfile"
fi

# 3. Vérification du fichier docker-compose.yml pour les volumes
echo "3. Vérification du fichier docker-compose.yml pour les volumes..."
if grep -q "- ./data:/app/data" docker-compose.yml; then
    echo "✓ Un volume pour /app/data est déjà configuré dans docker-compose.yml"
else
    echo "⚠️ Attention: Il n'y a pas de volume monté pour /app/data dans docker-compose.yml."
    echo "   Il est recommandé d'ajouter un volume pour persister les données entre les redémarrages:"
    echo "   volumes:"
    echo "     - ./data:/app/data"
    
    # Demande si on doit ajouter le volume au fichier docker-compose.yml
    read -p "Voulez-vous ajouter ce volume au fichier docker-compose.yml? (o/N) " response
    if [[ "$response" =~ ^[oO]$ ]]; then
        # Ajouter le volume au service mar-api
        sed -i '/mar-api:/,/^[^ ]/s/^    [^ ].*$/&\n    volumes:\n      - .\/data:\/app\/data/' docker-compose.yml
        echo "✓ Volume ajouté au fichier docker-compose.yml"
    else
        echo "⚠️ Le volume n'a pas été ajouté. Les données ne seront pas persistantes."
    fi
fi

# 4. Création du répertoire de données local
echo "4. Création du répertoire de données local..."
mkdir -p data/vector_store
echo "✓ Répertoire local data/vector_store créé"

# 5. Attribution des permissions appropriées
echo "5. Attribution des permissions appropriées..."
chmod -R 777 data
echo "✓ Permissions attribuées au répertoire data"

# 6. Reconstruire et redémarrer le conteneur
echo "6. Reconstruction et redémarrage du conteneur mar-api..."
docker-compose down
docker-compose build --no-cache mar-api
docker-compose up -d

echo "✓ Le conteneur mar-api a été reconstruit et redémarré."

# Attendre que le service démarre
echo "7. Attente du démarrage du service..."
sleep 15

# Vérifier les logs
echo "8. Vérification des logs de l'API..."
docker logs mar-api --tail 30

# Vérifier l'état des conteneurs
echo "9. Vérification de l'état des conteneurs..."
docker-compose ps

echo "=== Correction terminée ==="
