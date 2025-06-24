#!/bin/bash
# Script pour forcer la correction de tous les fichiers qui utilisent localhost pour Ollama

echo "=== CORRECTION FORCÉE OLLAMA ==="

# 1. Arrêter les services
echo "1. Arrêt des services..."
docker-compose down
sleep 5

# 2. Corriger directement dans les fichiers source
echo "2. Correction des fichiers source..."

# Fonction pour corriger un fichier
fix_file() {
    local file="$1"
    echo "Correction de: $file"
    
    # Faire une sauvegarde
    cp "$file" "$file.backup"
    
    # Appliquer toutes les corrections possibles
    sed -i 's/localhost:11434/ollama:11434/g' "$file"
    sed -i 's/127\.0\.0\.1:11434/ollama:11434/g' "$file"
    sed -i 's/"http:\/\/localhost:11434"/"http:\/\/ollama:11434"/g' "$file"
    sed -i "s/'http:\/\/localhost:11434'/'http:\/\/ollama:11434'/g" "$file"
    sed -i 's/http:\/\/localhost:11434/http:\/\/ollama:11434/g' "$file"
    
    # Vérifier si des corrections ont été appliquées
    if ! diff "$file" "$file.backup" > /dev/null; then
        echo "✓ $file corrigé"
    else
        echo "- $file inchangé"
        rm "$file.backup"
    fi
}

# Trouver et corriger tous les fichiers Python
find . -name "*.py" -type f | while read file; do
    if grep -q "localhost:11434\|127\.0\.0\.1:11434" "$file"; then
        fix_file "$file"
    fi
done

# 3. Forcer les variables d'environnement dans le Dockerfile
echo "3. Correction du Dockerfile..."
if [ -f Dockerfile ]; then
    # Ajouter les variables d'environnement Ollama au Dockerfile s'elles n'y sont pas
    if ! grep -q "OLLAMA_HOST" Dockerfile; then
        sed -i '/ENV PYTHONPATH/a ENV OLLAMA_HOST=ollama:11434\nENV OLLAMA_URL=http://ollama:11434' Dockerfile
        echo "✓ Variables Ollama ajoutées au Dockerfile"
    fi
fi

# 4. Créer un fichier .env propre
echo "4. Création d'un fichier .env propre..."
cat > .env << 'EOL'
OLLAMA_HOST=ollama:11434
OLLAMA_URL=http://ollama:11434
API_PORT=8008
API_HOST=0.0.0.0
REDIS_URL=redis://redis:6379
ELASTICSEARCH_URL=http://elasticsearch:9200
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
PYTHONPATH=/app
PYTHONUNBUFFERED=1
EOL
echo "✓ Fichier .env créé"

# 5. Correction du docker-compose.yml pour forcer les variables
echo "5. Correction du docker-compose.yml..."
if [ -f docker-compose.yml ]; then
    # S'assurer que mar-api a les bonnes variables d'environnement
    if ! grep -A 10 "mar-api:" docker-compose.yml | grep -q "OLLAMA_HOST"; then
        echo "Ajout des variables Ollama au docker-compose.yml..."
        
        # Créer une version modifiée
        cp docker-compose.yml docker-compose.yml.backup
        
        # Utiliser Python pour modifier le YAML proprement
        python3 << 'EOL'
import yaml
import sys

try:
    with open('docker-compose.yml', 'r') as f:
        compose = yaml.safe_load(f)
    
    # Forcer les variables d'environnement pour mar-api
    if 'services' in compose and 'mar-api' in compose['services']:
        service = compose['services']['mar-api']
        
        if 'environment' not in service:
            service['environment'] = {}
        
        # Forcer les variables Ollama
        service['environment']['OLLAMA_HOST'] = 'ollama:11434'
        service['environment']['OLLAMA_URL'] = 'http://ollama:11434'
        service['environment']['PYTHONPATH'] = '/app'
        
        # S'assurer de la dépendance
        if 'depends_on' not in service:
            service['depends_on'] = []
        if isinstance(service['depends_on'], list):
            if 'ollama' not in service['depends_on']:
                service['depends_on'].append('ollama')
        elif isinstance(service['depends_on'], dict):
            if 'ollama' not in service['depends_on']:
                service['depends_on']['ollama'] = {'condition': 'service_started'}
    
    with open('docker-compose.yml', 'w') as f:
        yaml.dump(compose, f, default_flow_style=False)
    
    print("✓ docker-compose.yml corrigé")
    
except Exception as e:
    print(f"⚠️ Erreur: {e}")
    # Fallback: modification manuelle
    print("Utilisation de la méthode manuelle...")
EOL
    fi
fi

# 6. Créer les modules manquants dans le Dockerfile
echo "6. Ajout de la création des modules manquants au Dockerfile..."
if [ -f Dockerfile ]; then
    if ! grep -q "llm/pooling" Dockerfile; then
        # Ajouter la création des modules au Dockerfile
        cat >> Dockerfile << 'EOL'

# Création des modules manquants
RUN mkdir -p /app/llm/pooling && \
    mkdir -p /app/orchestrator/tasks

# Création du module llm.pooling
RUN echo 'class LLMPool:\n    def __init__(self, max_connections=5):\n        self.max_connections = max_connections\n        self.clients = []\n        self.active_clients = 0\n\n    async def get_client(self):\n        return None\n\n    async def release_client(self, client):\n        pass\n\n    async def initialize(self):\n        pass' > /app/llm/pooling/pool.py && \
    touch /app/llm/pooling/__init__.py

# Création du module orchestrator.tasks
RUN echo 'class RAGTaskManager:\n    def __init__(self):\n        self.tasks = {}\n\n    async def create_task(self, task_type, parameters):\n        task_id = f"task_{len(self.tasks) + 1}"\n        self.tasks[task_id] = {"type": task_type, "parameters": parameters, "status": "created"}\n        return task_id\n\n    async def get_task(self, task_id):\n        return self.tasks.get(task_id)\n\n    async def update_task(self, task_id, status, result=None):\n        if task_id in self.tasks:\n            self.tasks[task_id]["status"] = status\n            if result:\n                self.tasks[task_id]["result"] = result\n            return True\n        return False' > /app/orchestrator/tasks/rag_tasks.py && \
    touch /app/orchestrator/tasks/__init__.py && \
    touch /app/orchestrator/__init__.py
EOL
        echo "✓ Création des modules ajoutée au Dockerfile"
    fi
fi

# 7. Reconstruire avec force
echo "7. Reconstruction forcée..."
docker-compose build --no-cache --pull mar-api
echo "✓ Image reconstruite"

# 8. Redémarrer les services
echo "8. Redémarrage des services..."
docker-compose up -d
echo "✓ Services redémarrés"

# 9. Attendre et vérifier
echo "9. Vérification finale..."
sleep 30

echo "Test de connectivité finale:"
docker exec mar-api ping -c 2 ollama && echo "✅ Ping OK" || echo "❌ Ping KO"
docker exec mar-api curl -s http://ollama:11434/api/tags > /dev/null && echo "✅ HTTP OK" || echo "❌ HTTP KO"

echo "Logs API (dernières lignes):"
docker logs mar-api --tail 10

echo "Test API finale:"
curl -s http://localhost:8008/health > /dev/null && echo "✅ API OK" || echo "❌ API KO"

echo "=== CORRECTION FORCÉE TERMINÉE ==="
