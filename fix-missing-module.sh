#!/bin/bash
# Script pour corriger l'erreur du module manquant llm.pooling

echo "=== Correction de l'erreur 'No module named llm.pooling' ==="

# 1. Créer le répertoire pooling s'il n'existe pas
echo "1. Vérification du répertoire llm/pooling..."
docker exec mar-api ls -la /app/llm/ || true

echo "2. Création du module pooling dans le conteneur..."
cat > pool.py << 'EOL'
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

echo "3. Création du répertoire pooling dans le conteneur..."
docker exec mar-api mkdir -p /app/llm/pooling || true
docker cp pool.py mar-api:/app/llm/pooling/pool.py
docker exec mar-api bash -c "touch /app/llm/pooling/__init__.py"
echo "✓ Module pooling créé"

echo "4. Vérification de la structure du module..."
docker exec mar-api ls -la /app/llm/pooling/

echo "5. Redémarrage de l'API..."
docker restart mar-api
echo "✓ API redémarrée"

echo "6. Attente du démarrage de l'API..."
sleep 10

echo "7. Vérification des logs de l'API..."
docker logs mar-api --tail 30

echo "=== Correction terminée ==="
echo "Vérifiez l'état de l'API avec: curl http://localhost:8008/health"
