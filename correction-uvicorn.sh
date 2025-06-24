#!/bin/bash
# Script pour corriger la commande de démarrage du serveur ASGI

echo "=== Correction de la commande de démarrage ASGI ==="

# 1. Vérification et sauvegarde du Dockerfile
echo "1. Sauvegarde du Dockerfile..."
cp Dockerfile Dockerfile.backup.$(date +%s)
echo "✓ Sauvegarde créée: Dockerfile.backup.$(date +%s)"

# 2. Vérification de l'instance app dans api/main.py
echo "2. Vérification de l'instance app dans api/main.py..."
if ! grep -q "app = create_app()" api/main.py; then
    echo "⚠️ Attention: L'instance app ne semble pas être définie dans api/main.py"
    echo "   Cette correction peut ne pas fonctionner sans cette modification."
    
    # Demander confirmation pour continuer
    read -p "Voulez-vous continuer quand même? (o/N) " response
    if [[ ! "$response" =~ ^[oO]$ ]]; then
        echo "Opération annulée par l'utilisateur."
        exit 1
    fi
else
    echo "✓ L'instance app est correctement définie dans api/main.py"
fi

# 3. Correction de la commande de démarrage dans le Dockerfile
echo "3. Correction de la commande de démarrage dans le Dockerfile..."
sed -i 's/CMD \["uvicorn", "api\.main:create_app()", "--host", "0\.0\.0\.0", "--port", "8000"\]/CMD \["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"\]/g' Dockerfile
echo "✓ Commande de démarrage corrigée dans le Dockerfile"

# 4. Reconstruire et redémarrer le conteneur
echo "4. Reconstruction et redémarrage du conteneur mar-api..."
docker-compose down
docker-compose build --no-cache mar-api
docker-compose up -d

echo "✓ Le conteneur mar-api a été reconstruit et redémarré."

# Attendre que le service démarre
echo "5. Attente du démarrage du service..."
sleep 15

# Vérifier les logs
echo "6. Vérification des logs de l'API..."
docker logs mar-api --tail 30

# Vérifier l'état des conteneurs
echo "7. Vérification de l'état des conteneurs..."
docker-compose ps

echo "=== Correction terminée ==="
echo "Si vous voyez encore des erreurs, vérifiez que le fichier api/main.py définit bien l'objet 'app = create_app()'."
