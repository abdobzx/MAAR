#!/bin/bash
# Script pour corriger l'erreur de connexion à Ollama

echo "=== Correction de l'erreur de connexion à Ollama ==="

# 1. Vérifier si le service Ollama est bien démarré
echo "1. Vérification de l'état du service Ollama..."
docker ps | grep ollama
OLLAMA_STATUS=$?

if [ $OLLAMA_STATUS -ne 0 ]; then
    echo "⚠️ Le service Ollama ne semble pas être en cours d'exécution."
    echo "Redémarrage du service Ollama..."
    docker-compose restart mar-ollama
    sleep 5
fi

# 2. Vérifier la variable d'environnement OLLAMA_HOST dans le conteneur
echo "2. Vérification de la variable d'environnement OLLAMA_HOST dans le conteneur..."
OLLAMA_HOST_ENV=$(docker exec mar-api env | grep OLLAMA_HOST)
echo "Variable OLLAMA_HOST: $OLLAMA_HOST_ENV"

# 3. Créer un script pour corriger l'URL Ollama
echo "3. Création d'un script pour corriger l'URL Ollama..."
cat > fix_ollama_url.py << 'EOL'
#!/usr/bin/env python3
"""
Script pour corriger l'URL du client Ollama dans le code
"""
import os
import re

def fix_ollama_client_file():
    # Chemins possibles du fichier client.py
    possible_paths = [
        "/app/llm/ollama/client.py",
        "/app/api/llm/ollama/client.py",
        "/app/llm/client.py"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Fichier trouvé: {path}")
            with open(path, 'r') as f:
                content = f.read()
            
            # Rechercher et remplacer localhost:11434 par la variable d'environnement
            if 'localhost:11434' in content:
                print("Remplacement de 'localhost:11434' par la variable d'environnement")
                modified_content = content.replace(
                    'localhost:11434', 
                    'os.environ.get("OLLAMA_HOST", "localhost:11434")'
                )
                
                # S'assurer que os est importé
                if 'import os' not in content:
                    modified_content = 'import os\n' + modified_content
                
                with open(path, 'w') as f:
                    f.write(modified_content)
                print(f"✓ Fichier {path} corrigé")
                return True
            else:
                print(f"Pas de 'localhost:11434' trouvé dans {path}")
    
    print("⚠️ Aucun fichier client Ollama trouvé ou nécessitant des modifications")
    return False

if __name__ == "__main__":
    if fix_ollama_client_file():
        print("✓ Correction appliquée avec succès")
    else:
        print("⚠️ Correction non appliquée")
EOL

# 4. Copier le script dans le conteneur
echo "4. Copie du script dans le conteneur..."
docker cp fix_ollama_url.py mar-api:/app/fix_ollama_url.py

# 5. Exécuter le script dans le conteneur
echo "5. Exécution du script dans le conteneur..."
docker exec mar-api python /app/fix_ollama_url.py

# 6. Rechercher tous les fichiers contenant "localhost:11434"
echo "6. Recherche de tous les fichiers contenant 'localhost:11434'..."
docker exec mar-api grep -r "localhost:11434" /app --include="*.py"

# 7. Redémarrer l'API
echo "7. Redémarrage de l'API..."
docker restart mar-api
echo "✓ API redémarrée"

# 8. Attendre que l'API démarre
echo "8. Attente du démarrage de l'API..."
sleep 15

# 9. Vérifier les logs
echo "9. Vérification des logs de l'API..."
docker logs mar-api --tail 50

echo "=== Correction terminée ==="
echo "Vérifiez l'état de l'API avec: curl http://localhost:8008/health"
