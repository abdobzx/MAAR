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

# 3. Créer un patch spécifique pour les clients Ollama
echo "3. Application de patches spécifiques..."

# Patch pour le client Ollama principal
if [ -f "llm/ollama/client.py" ]; then
    echo "Patch du client Ollama principal..."
    cat > temp_patch.py << 'EOL'
import re
import sys

def patch_ollama_client(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Patch spécifique pour forcer l'utilisation d'ollama:11434
        patches = [
            # Forcer OLLAMA_HOST au début du fichier
            (r'^(import .*?)$', r'\1\nimport os\nos.environ["OLLAMA_HOST"] = "ollama:11434"'),
            # Corriger les initialisations d'URL
            (r'self\.base_url = .*', 'self.base_url = "http://ollama:11434"'),
            (r'base_url=.*localhost.*', 'base_url="http://ollama:11434"'),
            (r'url.*=.*localhost:11434', 'url = "http://ollama:11434"'),
        ]
        
        for pattern, replacement in patches:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"✓ Client Ollama patché: {filepath}")
        
    except Exception as e:
        print(f"⚠️ Erreur lors du patch de {filepath}: {e}")

if __name__ == "__main__":
    patch_ollama_client(sys.argv[1])
EOL

    python3 temp_patch.py "llm/ollama/client.py"
    rm temp_patch.py
fi

# 4. Forcer les variables d'environnement dans le Dockerfile
echo "4. Correction du Dockerfile..."
if [ -f Dockerfile ]; then
    # Ajouter les variables d'environnement Ollama au Dockerfile s'elles n'y sont pas
    if ! grep -q "OLLAMA_HOST" Dockerfile; then
        sed -i '/ENV PYTHONPATH/a ENV OLLAMA_HOST=ollama:11434\nENV OLLAMA_URL=http://ollama:11434' Dockerfile
        echo "✓ Variables Ollama ajoutées au Dockerfile"
    fi
fi

# 5. Correction du docker-compose.yml
echo "5. Correction du docker-compose.yml..."
python3 << 'EOL'
import yaml

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
        
        # S'assurer de la dépendance
        if 'depends_on' not in service:
            service['depends_on'] = []
        if 'ollama' not in service['depends_on']:
            service['depends_on'].append('ollama')
    
    with open('docker-compose.yml', 'w') as f:
        yaml.dump(compose, f, default_flow_style=False)
    
    print("✓ docker-compose.yml corrigé")
    
except Exception as e:
    print(f"⚠️ Erreur: {e}")
EOL

# 6. Reconstruire avec force
echo "6. Reconstruction forcée..."
docker-compose build --no-cache --pull mar-api
echo "✓ Image reconstruite"

# 7. Redémarrer les services
echo "7. Redémarrage des services..."
docker-compose up -d
echo "✓ Services redémarrés"

# 8. Attendre et vérifier
echo "8. Vérification finale..."
sleep 30

echo "Test de connectivité finale:"
docker exec mar-api ping -c 2 ollama && echo "✅ Ping OK" || echo "❌ Ping KO"
docker exec mar-api curl -s http://ollama:11434/api/tags > /dev/null && echo "✅ HTTP OK" || echo "❌ HTTP KO"

echo "Logs API (dernières lignes):"
docker logs mar-api --tail 10

echo "Test API finale:"
curl -s http://localhost:8008/health > /dev/null && echo "✅ API OK" || echo "❌ API KO"

echo "=== CORRECTION FORCÉE TERMINÉE ==="
