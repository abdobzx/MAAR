#!/bin/bash
# Script pour corriger le problème de l'application ASGI non trouvée

echo "=== Correction du problème d'application ASGI ==="

# 1. Vérification et sauvegarde des fichiers
echo "1. Sauvegarde des fichiers..."
cp api/main.py api/main.py.backup
cp Dockerfile Dockerfile.backup
echo "✓ Sauvegardes créées: api/main.py.backup et Dockerfile.backup"

# 2. Application des corrections
echo "2. Modification du fichier api/main.py..."
# Vérification si l'instance app est déjà créée
if ! grep -q "app = create_app()" api/main.py; then
    # Ajouter l'instance app après la définition de la fonction create_app
    sed -i '/def create_app().*:/,/return app/{/return app/a\\n\n# Création de l'\''application FastAPI pour une utilisation directe par Uvicorn\napp = create_app()\n\n}' api/main.py
    echo "✓ Instance app ajoutée au module api.main"
else
    echo "✓ Instance app déjà présente dans le module api.main"
fi

echo "3. Reconstruction et redémarrage des conteneurs..."
docker-compose down
docker-compose build --no-cache mar-api
docker-compose up -d

echo "✓ Les conteneurs ont été reconstruits et redémarrés."

# Attendre que le service démarre
echo "4. Attente du démarrage du service..."
sleep 15

# Vérifier les logs
echo "5. Vérification des logs de l'API..."
docker logs mar-api --tail 30

# Vérifier l'état des conteneurs
echo "6. Vérification de l'état des conteneurs..."
docker-compose ps

echo "=== Correction terminée ==="
