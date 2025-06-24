#!/bin/bash
# Script pour installer les dépendances manquantes pour Pydantic v2

echo "=== Installation des dépendances manquantes pour Pydantic v2 ==="

# 1. Installation directe dans le conteneur Docker
echo "1. Installation des dépendances dans le conteneur Docker..."
docker exec -it mar-api pip install email-validator

# Si la commande précédente échoue, on va modifier le Dockerfile et reconstruire l'image
if [ $? -ne 0 ]; then
    echo "⚠️ L'installation directe a échoué. Modification du fichier requirements.txt..."
    
    # Vérifier si le fichier existe
    if [ ! -f "requirements.txt" ]; then
        echo "❌ Erreur: Le fichier requirements.txt n'existe pas."
        exit 1
    fi
    
    # Sauvegarde du fichier requirements.txt
    cp requirements.txt requirements.txt.backup
    echo "✓ Sauvegarde créée: requirements.txt.backup"
    
    # Ajouter email-validator aux dépendances si elle n'existe pas déjà
    if ! grep -q "email-validator" requirements.txt; then
        echo "email-validator>=2.0.0" >> requirements.txt
        echo "✓ Dépendance 'email-validator' ajoutée au fichier requirements.txt"
    else
        echo "✓ La dépendance 'email-validator' existe déjà dans requirements.txt"
    fi
    
    # Reconstruire et redémarrer le conteneur
    echo "2. Reconstruction et redémarrage du conteneur mar-api..."
    docker-compose build --no-cache mar-api
    docker-compose up -d mar-api
    
    echo "✓ Le conteneur mar-api a été reconstruit et redémarré."
else
    echo "✓ Installation de la dépendance 'email-validator' réussie."
    
    # Redémarrer le service API
    echo "2. Redémarrage du service API..."
    docker-compose restart mar-api
    echo "✓ Le service API a été redémarré."
fi

# Attendre que le service démarre
echo "3. Attente du démarrage du service..."
sleep 10

# Vérifier les logs
echo "4. Vérification des logs de l'API..."
docker logs mar-api --tail 30

echo "=== Installation des dépendances terminée ==="
