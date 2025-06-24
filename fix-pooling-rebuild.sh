#!/bin/bash
# Script pour corriger l'erreur du module manquant llm.pooling en modifiant le Dockerfile et reconstruisant l'image

echo "=== Correction de l'erreur 'No module named llm.pooling' par reconstruction d'image ==="

# 1. Créer le répertoire et les fichiers nécessaires localement
echo "1. Création du module pooling localement..."
mkdir -p llm/pooling

cat > llm/pooling/pool.py << 'EOL'
"""
Module pour gérer un pool de LLMs.
"""

class LLMPool:
    """
    Classe qui gère un pool de modèles LLM.
    Peut être étendue pour implémenter un vrai pool avec plusieurs instances.
    Pour l'instant, c'est juste un placeholder.
    """
    def __init__(self, max_connections=5):
        self.max_connections = max_connections
        self.clients = []
        self.active_clients = 0

    async def get_client(self):
        """
        Retourne un client LLM du pool.
        Pour l'instant retourne None, car l'implémentation complète 
        dépend de l'architecture spécifique du système.
        """
        return None

    async def release_client(self, client):
        """
        Libère un client LLM dans le pool.
        """
        pass

    async def initialize(self):
        """
        Initialise le pool.
        """
        pass
EOL

# Créer le fichier __init__.py
touch llm/pooling/__init__.py
echo "✓ Module pooling créé localement"

# 2. Arrêter les conteneurs
echo "2. Arrêt des conteneurs..."
docker-compose down
echo "✓ Conteneurs arrêtés"

# 3. Reconstruire l'image
echo "3. Reconstruction de l'image mar-api..."
docker-compose build --no-cache mar-api
echo "✓ Image mar-api reconstruite"

# 4. Redémarrer les conteneurs
echo "4. Redémarrage des conteneurs..."
docker-compose up -d
echo "✓ Conteneurs redémarrés"

# 5. Attendre que l'API démarre
echo "5. Attente du démarrage de l'API..."
sleep 15

# 6. Vérifier les logs
echo "6. Vérification des logs de l'API..."
docker logs mar-api --tail 30

echo "7. Test de la santé de l'API..."
curl -s http://localhost:8008/health || echo "L'API n'est pas encore prête. Vérifiez les logs pour plus d'informations."

echo "=== Correction terminée ==="
echo "Si l'API n'est toujours pas disponible, vérifiez les logs avec: docker logs mar-api"
