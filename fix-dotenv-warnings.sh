#!/bin/bash
# Script pour corriger les warnings python-dotenv

echo "=== Correction des warnings python-dotenv ==="

# 1. Identifier et corriger le fichier .env problématique
echo "1. Recherche du fichier .env problématique..."

# Chercher tous les fichiers .env
find . -name ".env*" -type f | while read envfile; do
    echo "Analyse de: $envfile"
    
    # Vérifier si le fichier a des problèmes de format
    if grep -n "^[[:space:]]*$\|^[[:space:]]*#" "$envfile" | head -5; then
        echo "Lignes vides ou commentaires détectés dans $envfile"
        
        # Créer une version nettoyée
        echo "Nettoyage de $envfile..."
        cp "$envfile" "$envfile.backup"
        
        # Nettoyer le fichier: enlever les lignes vides au début et à la fin
        # et s'assurer que chaque ligne est au bon format
        python3 << EOL
import re

def clean_env_file(filepath):
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Ignorer les lignes vides
            if not line:
                continue
                
            # Garder les commentaires mais s'assurer qu'ils commencent par #
            if line.startswith('#'):
                cleaned_lines.append(line + '\n')
                continue
            
            # Pour les variables d'environnement, s'assurer du format KEY=VALUE
            if '=' in line:
                # Nettoyer les espaces autour du =
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # S'assurer que la clé est valide (lettres, chiffres, underscore)
                if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                    cleaned_lines.append(f'{key}={value}\n')
                else:
                    print(f"Ligne {i} ignorée (clé invalide): {line}")
            else:
                print(f"Ligne {i} ignorée (format invalide): {line}")
        
        # Écrire le fichier nettoyé
        with open(filepath, 'w') as f:
            f.writelines(cleaned_lines)
        
        print(f"✓ Fichier {filepath} nettoyé")
        return True
        
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage de {filepath}: {e}")
        return False

clean_env_file('$envfile')
EOL
    fi
done

# 2. Créer un fichier .env propre si aucun n'existe ou s'ils sont tous corrompus
echo "2. S'assurer qu'un fichier .env propre existe..."
cat > .env.clean << 'EOL'
# Configuration Ollama pour Docker
OLLAMA_HOST=ollama:11434
OLLAMA_URL=http://ollama:11434

# Configuration API
API_PORT=8008
API_HOST=0.0.0.0

# Configuration Redis
REDIS_URL=redis://redis:6379

# Configuration Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# Configuration Prometheus
PROMETHEUS_URL=http://prometheus:9090

# Configuration Grafana
GRAFANA_URL=http://grafana:3000

# Configuration Python
PYTHONPATH=/app
PYTHONUNBUFFERED=1
EOL

# Remplacer le .env existant s'il est problématique
if [ -f .env ]; then
    # Tester si le .env actuel cause des problèmes
    python3 -c "
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('error')
try:
    load_dotenv('.env')
    print('✓ Fichier .env actuel valide')
except:
    print('⚠️ Fichier .env actuel problématique, remplacement...')
    import shutil
    shutil.move('.env', '.env.corrupted')
    shutil.copy('.env.clean', '.env')
"
else
    cp .env.clean .env
    echo "✓ Nouveau fichier .env créé"
fi

# 3. Nettoyer les fichiers de configuration Docker
echo "3. Nettoyage des fichiers de configuration Docker..."

# S'assurer que docker-compose.yml n'a pas de problèmes avec les variables d'environnement
if [ -f docker-compose.yml ]; then
    echo "Vérification du docker-compose.yml..."
    
    # Tester la validité du YAML
    python3 -c "
import yaml
try:
    with open('docker-compose.yml', 'r') as f:
        yaml.safe_load(f)
    print('✓ docker-compose.yml valide')
except Exception as e:
    print(f'⚠️ Problème avec docker-compose.yml: {e}')
"
fi

# 4. Redémarrer les services pour appliquer les corrections
echo "4. Application des corrections..."
docker-compose down
sleep 5
docker-compose up -d

echo "5. Attente du démarrage..."
sleep 20

echo "6. Vérification des logs sans warnings..."
docker logs mar-api --tail 30 | grep -v "python-dotenv could not parse" || true

echo "=== Correction des warnings dotenv terminée ==="

# Nettoyage
rm -f .env.clean
