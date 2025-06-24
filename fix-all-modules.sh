#!/bin/bash
# Script pour corriger les modules manquants et la configuration Ollama

echo "=== Correction des modules manquants et de la configuration Ollama ==="

# 1. Création des structures de répertoires nécessaires localement
echo "1. Création des structures de modules manquants localement..."

# Créer les répertoires nécessaires
mkdir -p orchestrator/tasks
mkdir -p llm/pooling

# Créer le fichier pool.py pour llm.pooling
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

# Créer le fichier __init__.py pour llm.pooling
touch llm/pooling/__init__.py

# Créer le fichier rag_tasks.py pour orchestrator.tasks
cat > orchestrator/tasks/rag_tasks.py << 'EOL'
"""
Module pour gérer les tâches RAG de l'orchestrator.
"""

class RAGTaskManager:
    """
    Gestionnaire de tâches pour les opérations RAG.
    """
    def __init__(self):
        self.tasks = {}
    
    async def create_task(self, task_type, parameters):
        """
        Crée une nouvelle tâche.
        """
        task_id = f"task_{len(self.tasks) + 1}"
        self.tasks[task_id] = {
            "type": task_type,
            "parameters": parameters,
            "status": "created"
        }
        return task_id
    
    async def get_task(self, task_id):
        """
        Récupère une tâche par son ID.
        """
        return self.tasks.get(task_id)
    
    async def update_task(self, task_id, status, result=None):
        """
        Met à jour le statut d'une tâche.
        """
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
            if result:
                self.tasks[task_id]["result"] = result
            return True
        return False
EOL

# Créer le fichier __init__.py pour orchestrator.tasks
touch orchestrator/tasks/__init__.py
touch orchestrator/__init__.py

# Créer un fichier pour corriger l'URL d'Ollama
cat > fix_ollama_client.py << 'EOL'
#!/usr/bin/env python3
"""
Script pour remplacer l'URL codée en dur de localhost:11434 par la variable d'environnement OLLAMA_HOST
"""
import os

def fix_ollama_client():
    # Rechercher le fichier client.py d'Ollama
    for root, dirs, files in os.walk("/app"):
        for file in files:
            if file == "client.py" and ("ollama" in root or "llm" in root):
                client_path = os.path.join(root, file)
                print(f"Fichier client trouvé: {client_path}")
                
                # Lire le contenu du fichier
                with open(client_path, 'r') as f:
                    content = f.read()
                
                # Remplacer localhost:11434 par la variable d'environnement
                if 'localhost:11434' in content:
                    modified_content = content.replace(
                        "localhost:11434", 
                        "os.environ.get('OLLAMA_HOST', 'ollama:11434')"
                    )
                    
                    # Vérifier si os est déjà importé
                    if "import os" not in content:
                        modified_content = "import os\n" + modified_content
                    
                    # Écrire le contenu modifié
                    with open(client_path, 'w') as f:
                        f.write(modified_content)
                    
                    print(f"✓ URL Ollama corrigée dans {client_path}")
                    return True
                else:
                    print(f"! Pas de 'localhost:11434' trouvé dans {client_path}")
    
    print("! Aucun fichier client Ollama trouvé")
    return False

if __name__ == "__main__":
    fix_ollama_client()
EOL

echo "✓ Modules créés localement"

# 2. Arrêter les conteneurs
echo "2. Arrêt des conteneurs Docker..."
docker-compose down
echo "✓ Conteneurs arrêtés"

# 3. Reconstruire l'image mar-api
echo "3. Reconstruction de l'image mar-api..."
docker-compose build --no-cache mar-api
echo "✓ Image mar-api reconstruite"

# 4. Redémarrer tous les services
echo "4. Redémarrage des services Docker..."
docker-compose up -d
echo "✓ Services redémarrés"

# 5. Attendre que les services démarrent
echo "5. Attente du démarrage des services..."
sleep 20

# 6. Exécuter le script de correction d'URL Ollama à l'intérieur du conteneur
echo "6. Correction de l'URL Ollama dans le conteneur..."
docker cp fix_ollama_client.py mar-api:/app/fix_ollama_client.py
docker exec mar-api python /app/fix_ollama_client.py

# 7. Redémarrer l'API
echo "7. Redémarrage de l'API..."
docker restart mar-api
echo "✓ API redémarrée"

# 8. Attendre le démarrage de l'API
echo "8. Attente du démarrage de l'API..."
sleep 15

# 9. Vérifier les logs
echo "9. Vérification des logs de l'API..."
docker logs mar-api --tail 40

# 10. Tester l'API
echo "10. Test de la santé de l'API..."
curl -s http://localhost:8008/health || echo "⚠️ L'API n'est pas encore prête. Vérifiez les logs pour plus d'informations."

echo "=== Correction terminée ==="
echo "Si l'API ne répond toujours pas, vérifiez les logs avec: docker logs mar-api"
