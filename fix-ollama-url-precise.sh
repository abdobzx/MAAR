#!/bin/bash
# Script pour corriger l'URL Ollama dans le client.py

echo "=== Correction précise de l'URL Ollama dans client.py ==="

# 1. Recherche du fichier client.py
echo "1. Recherche et modification du fichier client.py dans le conteneur..."

# Créer un script Python pour un remplacement plus précis
cat > fix_ollama_url_precise.py << 'EOL'
#!/usr/bin/env python3
"""
Script pour corriger l'URL Ollama dans le client.py d'une manière plus précise
"""
import os
import re

def fix_ollama_url():
    # Chemin du fichier client.py
    client_path = "/app/llm/ollama/client.py"
    
    # Vérifier que le fichier existe
    if not os.path.exists(client_path):
        print(f"! Fichier {client_path} introuvable")
        return False
    
    # Lire le contenu du fichier
    with open(client_path, 'r') as f:
        content = f.read()
    
    # Ajouter l'import os s'il n'est pas déjà présent
    if 'import os' not in content:
        content = 'import os\n' + content
    
    # Patterns à chercher et remplacer pour l'initialisation du client
    patterns = [
        (r'BASE_URL\s*=\s*"[^"]*://localhost:11434"', 
         'BASE_URL = "http://" + os.environ.get("OLLAMA_HOST", "ollama:11434")'),
        (r'BASE_URL\s*=\s*\'[^\']*://localhost:11434\'', 
         'BASE_URL = "http://" + os.environ.get("OLLAMA_HOST", "ollama:11434")'),
        (r'base_url\s*=\s*"[^"]*://localhost:11434"', 
         'base_url = "http://" + os.environ.get("OLLAMA_HOST", "ollama:11434")'),
        (r'base_url\s*=\s*\'[^\']*://localhost:11434\'', 
         'base_url = "http://" + os.environ.get("OLLAMA_HOST", "ollama:11434")'),
        (r'"http://localhost:11434"', 
         '"http://" + os.environ.get("OLLAMA_HOST", "ollama:11434")'),
        (r"'http://localhost:11434'", 
         '"http://" + os.environ.get("OLLAMA_HOST", "ollama:11434")'),
    ]
    
    # Appliquer les remplacements
    modified = False
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
            print(f"✓ Remplacement effectué avec pattern: {pattern}")
    
    # Si aucun des patterns ne correspond, essayer un remplacement plus direct
    if not modified and "localhost:11434" in content:
        modified_content = content.replace(
            "localhost:11434", 
            '" + os.environ.get("OLLAMA_HOST", "ollama:11434") + "'
        )
        if modified_content != content:
            content = modified_content
            modified = True
            print("✓ Remplacement direct effectué")
    
    # Écrire le contenu modifié uniquement si des changements ont été faits
    if modified:
        with open(client_path, 'w') as f:
            f.write(content)
        print(f"✓ Fichier {client_path} mis à jour")
        return True
    else:
        print(f"! Aucun remplacement nécessaire dans {client_path}")
        return False

if __name__ == "__main__":
    fix_ollama_url()
EOL

# Copier et exécuter le script dans le conteneur
docker cp fix_ollama_url_precise.py mar-api:/app/fix_ollama_url_precise.py
docker exec mar-api python /app/fix_ollama_url_precise.py

# 2. Modifier manuellement le fichier de configuration pour Ollama
echo "2. Création d'un script pour modifier directement la variable OLLAMA_HOST dans la configuration..."

cat > fix_ollama_env.py << 'EOL'
#!/usr/bin/env python3
"""
Script pour forcer la valeur de la variable d'environnement OLLAMA_HOST dans la configuration
"""
import os

def fix_ollama_env():
    platform_path = "/app/api/platform.py"
    
    if os.path.exists(platform_path):
        # Lire le contenu du fichier
        with open(platform_path, 'r') as f:
            content = f.read()
        
        # Ajouter du code pour forcer la valeur de OLLAMA_HOST
        if "import os" not in content:
            modified_content = "import os\n" + content
        else:
            modified_content = content
            
        # Ajouter la ligne pour forcer OLLAMA_HOST près du début du fichier
        force_env = "\n# Forcer la valeur de OLLAMA_HOST pour l'environnement Docker\nos.environ['OLLAMA_HOST'] = 'ollama:11434'\n"
        
        # Trouver une position appropriée pour insérer le code
        import_pos = modified_content.find("import ")
        if import_pos != -1:
            # Trouver la fin du bloc d'imports
            lines = modified_content.split('\n')
            i = 0
            while i < len(lines) and (lines[i].startswith('import ') or lines[i].startswith('from ')):
                i += 1
            
            # Insérer après les imports
            modified_content = '\n'.join(lines[:i]) + force_env + '\n'.join(lines[i:])
        else:
            # Si pas d'imports, ajouter au début du fichier
            modified_content = force_env + modified_content
        
        # Écrire le contenu modifié
        with open(platform_path, 'w') as f:
            f.write(modified_content)
        
        print(f"✓ Variable OLLAMA_HOST forcée dans {platform_path}")
        return True
    else:
        print(f"! Fichier {platform_path} introuvable")
        return False

if __name__ == "__main__":
    fix_ollama_env()
EOL

# Copier et exécuter le script dans le conteneur
docker cp fix_ollama_env.py mar-api:/app/fix_ollama_env.py
docker exec mar-api python /app/fix_ollama_env.py

# 3. Redémarrer l'API
echo "3. Redémarrage de l'API..."
docker restart mar-api
echo "✓ API redémarrée"

# 4. Attendre le démarrage de l'API
echo "4. Attente du démarrage de l'API..."
sleep 15

# 5. Vérifier les logs
echo "5. Vérification des logs de l'API..."
docker logs mar-api --tail 40

# 6. Tester l'API
echo "6. Test de la santé de l'API..."
curl -s http://localhost:8008/health || echo "⚠️ L'API n'est pas encore prête. Vérifiez les logs pour plus d'informations."

echo "=== Correction terminée ==="
echo "Si l'API ne répond toujours pas, vérifiez les logs avec: docker logs mar-api"
