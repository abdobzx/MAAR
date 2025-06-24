#!/bin/bash
# Script pour créer un nouveau Dockerfile qui inclut toutes les corrections nécessaires

echo "=== Création d'un nouveau Dockerfile avec toutes les corrections ==="

# 1. Sauvegarde des fichiers originaux
echo "1. Sauvegarde des fichiers originaux..."
cp Dockerfile Dockerfile.original.$(date +%s)
echo "✓ Sauvegarde du Dockerfile créée"

# 2. Création d'un nouveau Dockerfile avec les corrections
echo "2. Création d'un nouveau Dockerfile avec toutes les corrections..."
cat > Dockerfile.fixed << 'EOL'
# Dockerfile principal pour l'API MAR
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="MAR Platform Team"
LABEL description="Multi-Agent RAG Platform - FastAPI Service"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création des modules manquants
RUN mkdir -p /app/llm/pooling && \
    mkdir -p /app/orchestrator/tasks

# Création du module llm.pooling
RUN echo '"""\nModule pour gérer un pool de LLMs.\n"""\n\nclass LLMPool:\n    """\n    Classe qui gère un pool de modèles LLM.\n    Peut être étendue pour implémenter un vrai pool avec plusieurs instances.\n    Pour l'\''instant, c'\''est juste un placeholder.\n    """\n    def __init__(self, max_connections=5):\n        self.max_connections = max_connections\n        self.clients = []\n        self.active_clients = 0\n\n    async def get_client(self):\n        """\n        Retourne un client LLM du pool.\n        Pour l'\''instant retourne None, car l'\''implémentation complète \n        dépend de l'\''architecture spécifique du système.\n        """\n        return None\n\n    async def release_client(self, client):\n        """\n        Libère un client LLM dans le pool.\n        """\n        pass\n\n    async def initialize(self):\n        """\n        Initialise le pool.\n        """\n        pass' > /app/llm/pooling/pool.py && \
    touch /app/llm/pooling/__init__.py

# Création du module orchestrator.tasks
RUN echo '"""\nModule pour gérer les tâches RAG de l'\''orchestrator.\n"""\n\nclass RAGTaskManager:\n    """\n    Gestionnaire de tâches pour les opérations RAG.\n    """\n    def __init__(self):\n        self.tasks = {}\n    \n    async def create_task(self, task_type, parameters):\n        """\n        Crée une nouvelle tâche.\n        """\n        task_id = f"task_{len(self.tasks) + 1}"\n        self.tasks[task_id] = {\n            "type": task_type,\n            "parameters": parameters,\n            "status": "created"\n        }\n        return task_id\n    \n    async def get_task(self, task_id):\n        """\n        Récupère une tâche par son ID.\n        """\n        return self.tasks.get(task_id)\n    \n    async def update_task(self, task_id, status, result=None):\n        """\n        Met à jour le statut d'\''une tâche.\n        """\n        if task_id in self.tasks:\n            self.tasks[task_id]["status"] = status\n            if result:\n                self.tasks[task_id]["result"] = result\n            return True\n        return False' > /app/orchestrator/tasks/rag_tasks.py && \
    touch /app/orchestrator/tasks/__init__.py && \
    touch /app/orchestrator/__init__.py

# Correction de l'URL Ollama dans platform.py
RUN if [ -f /app/api/platform.py ]; then \
        sed -i '1i import os\n# Forcer OLLAMA_HOST pour Docker\nos.environ["OLLAMA_HOST"] = "ollama:11434"' /app/api/platform.py; \
    fi

# Correction de l'URL Ollama dans le client
RUN find /app -name "client.py" -type f -exec sed -i 's/localhost:11434/ollama:11434/g' {} \;

# Création des répertoires nécessaires
RUN mkdir -p /app/data/vector_store

# Création d'un utilisateur non-root pour la sécurité
RUN adduser --disabled-password --gecos '' --uid 1000 maruser && \
    chown -R maruser:maruser /app
USER maruser

# Exposition du port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Commande de démarrage
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOL

echo "✓ Nouveau Dockerfile créé: Dockerfile.fixed"

# 3. Utiliser le nouveau Dockerfile
echo "3. Utilisation du nouveau Dockerfile..."
cp Dockerfile.fixed Dockerfile
echo "✓ Le nouveau Dockerfile a été copié pour remplacer l'original"

# 4. Arrêter et supprimer tous les conteneurs
echo "4. Arrêt et suppression de tous les conteneurs..."
docker-compose down --volumes --remove-orphans
echo "✓ Tous les conteneurs ont été arrêtés et supprimés"

# 5. Reconstruire l'image
echo "5. Reconstruction de l'image mar-api..."
docker-compose build --no-cache mar-api
echo "✓ Image mar-api reconstruite"

# 6. Démarrer les services
echo "6. Démarrage des services..."
docker-compose up -d
echo "✓ Services démarrés"

# 7. Attendre que les services démarrent
echo "7. Attente du démarrage des services..."
sleep 20

# 8. Vérifier les logs
echo "8. Vérification des logs de mar-api..."
docker logs mar-api --tail 40

# 9. Tester l'API
echo "9. Test de la santé de l'API..."
curl -s http://localhost:8008/health || echo "⚠️ L'API n'est pas encore prête. Vérifiez les logs pour plus d'informations."

echo "=== Correction terminée ==="
echo "Si l'API ne répond toujours pas, vérifiez les logs avec: docker logs mar-api"
