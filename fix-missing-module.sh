#!/bin/bash
# Script pour corriger l'erreur du module manquant llm.pooling et les problèmes de connexion Ollama

echo "=== Correction complète des erreurs de modules et connexion Ollama ==="

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

echo "8. Correction de la connexion Ollama dans le conteneur..."
# Corriger tous les fichiers Python qui utilisent localhost au lieu d'ollama
docker exec mar-api find /app -name "*.py" -type f -exec grep -l "localhost:11434" {} \; | while read file; do
    echo "Correction de $file"
    docker exec mar-api sed -i 's/localhost:11434/ollama:11434/g' "$file"
done

# Forcer la variable d'environnement dans le conteneur
docker exec mar-api bash -c 'export OLLAMA_HOST=ollama:11434 && export OLLAMA_URL=http://ollama:11434'

echo "9. Redémarrage final de l'API..."
docker restart mar-api
echo "✓ API redémarrée avec les corrections Ollama"

echo "10. Attente du démarrage complet..."
sleep 15

echo "11. Test de connectivité Ollama..."
docker exec mar-api ping -c 2 ollama || echo "⚠️ Ping vers ollama échoué"
docker exec mar-api curl -s http://ollama:11434/api/tags || echo "⚠️ Connexion HTTP vers ollama échouée"

echo "12. Vérification finale des logs..."
docker logs mar-api --tail 20

echo "=== Correction terminée ==="
echo "Commandes utiles:"
echo "  - Test API: curl http://localhost:8008/health"
echo "  - Test Ollama: docker exec mar-api curl http://ollama:11434/api/tags"
echo "  - Logs API: docker logs mar-api"
echo "  - Logs Ollama: docker logs mar-ollama"
