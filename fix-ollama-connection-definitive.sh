#!/bin/bash
# Script pour corriger définitivement la connexion Ollama

echo "=== Correction définitive de la connexion Ollama ==="

# 1. Arrêter tous les services
echo "1. Arrêt de tous les services..."
docker-compose down
echo "✓ Services arrêtés"

# 2. Rechercher et corriger tous les fichiers qui utilisent localhost:11434
echo "2. Correction de tous les fichiers Python..."

# Créer un script de correction temporaire
cat > fix_ollama_urls.py << 'EOL'
#!/usr/bin/env python3
import os
import re

def fix_ollama_urls_in_file(filepath):
    """Corrige les URLs Ollama dans un fichier"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacements multiples pour couvrir tous les cas
        patterns = [
            (r'localhost:11434', 'ollama:11434'),
            (r'127\.0\.0\.1:11434', 'ollama:11434'),
            (r'"http://localhost:11434"', '"http://ollama:11434"'),
            (r"'http://localhost:11434'", "'http://ollama:11434'"),
            (r'http://localhost:11434', 'http://ollama:11434'),
            (r'OLLAMA_HOST.*=.*localhost:11434', 'OLLAMA_HOST = "ollama:11434"'),
            (r'OLLAMA_HOST.*=.*"localhost:11434"', 'OLLAMA_HOST = "ollama:11434"'),
            (r"OLLAMA_HOST.*=.*'localhost:11434'", "OLLAMA_HOST = 'ollama:11434'"),
        ]
        
        modified = False
        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                modified = True
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Corrigé: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"⚠️ Erreur lors de la correction de {filepath}: {e}")
        return False

def scan_and_fix_directory(directory):
    """Scan et corrige tous les fichiers Python dans un répertoire"""
    fixed_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_ollama_urls_in_file(filepath):
                    fixed_files.append(filepath)
    
    return fixed_files

if __name__ == "__main__":
    print("Recherche et correction des URLs Ollama...")
    fixed = scan_and_fix_directory('.')
    print(f"Fichiers corrigés: {len(fixed)}")
    for f in fixed:
        print(f"  - {f}")
EOL

python3 fix_ollama_urls.py
rm fix_ollama_urls.py
echo "✓ URLs Ollama corrigées"

# 3. Créer/Corriger le fichier .env pour forcer l'utilisation d'Ollama Docker
echo "3. Configuration des variables d'environnement..."
cat > .env << 'EOL'
# Configuration Ollama pour Docker
OLLAMA_HOST=ollama:11434
OLLAMA_URL=http://ollama:11434

# Configuration API
API_PORT=8008
API_HOST=0.0.0.0

# Configuration base de données
REDIS_URL=redis://redis:6379
ELASTICSEARCH_URL=http://elasticsearch:9200

# Configuration monitoring
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
EOL
echo "✓ Fichier .env créé"

# 4. Corriger le docker-compose.yml pour s'assurer que l'environnement est bien transmis
echo "4. Vérification du docker-compose.yml..."

# Créer une version corrigée du docker-compose
if [ -f docker-compose.yml ]; then
    cp docker-compose.yml docker-compose.yml.backup
    
    # Ajouter les variables d'environnement si elles ne sont pas présentes
    python3 << 'EOL'
import yaml
import sys

try:
    with open('docker-compose.yml', 'r') as f:
        compose = yaml.safe_load(f)
    
    # S'assurer que le service mar-api a les bonnes variables d'environnement
    if 'services' in compose and 'mar-api' in compose['services']:
        if 'environment' not in compose['services']['mar-api']:
            compose['services']['mar-api']['environment'] = {}
        
        # Ajouter/forcer les variables Ollama
        env = compose['services']['mar-api']['environment']
        env['OLLAMA_HOST'] = 'ollama:11434'
        env['OLLAMA_URL'] = 'http://ollama:11434'
        env['PYTHONPATH'] = '/app'
        
        # S'assurer que mar-api dépend d'ollama
        if 'depends_on' not in compose['services']['mar-api']:
            compose['services']['mar-api']['depends_on'] = []
        if 'ollama' not in compose['services']['mar-api']['depends_on']:
            compose['services']['mar-api']['depends_on'].append('ollama')
    
    with open('docker-compose.yml', 'w') as f:
        yaml.dump(compose, f, default_flow_style=False)
    
    print("✓ docker-compose.yml mis à jour")
except Exception as e:
    print(f"⚠️ Erreur lors de la mise à jour du docker-compose.yml: {e}")
    sys.exit(1)
EOL
fi

# 5. Reconstruire et redémarrer
echo "5. Reconstruction de l'image mar-api..."
docker-compose build --no-cache mar-api
echo "✓ Image reconstruite"

echo "6. Démarrage des services..."
docker-compose up -d
echo "✓ Services démarrés"

# 7. Attendre le démarrage
echo "7. Attente du démarrage complet..."
sleep 30

# 8. Vérifier la connexion Ollama
echo "8. Vérification de la connexion Ollama..."
echo "État du conteneur Ollama:"
docker ps | grep ollama

echo "Logs Ollama (10 dernières lignes):"
docker logs mar-ollama --tail 10

echo "Test de connectivité depuis mar-api vers ollama:"
docker exec mar-api ping -c 2 ollama || echo "⚠️ Ping vers ollama échoué"

echo "Test de connexion HTTP vers Ollama:"
docker exec mar-api curl -s http://ollama:11434/api/tags || echo "⚠️ Connexion HTTP vers ollama échouée"

# 9. Vérifier les logs de l'API
echo "9. Vérification des logs de l'API..."
docker logs mar-api --tail 20

# 10. Test final de l'API
echo "10. Test final de l'API..."
curl -s http://localhost:8008/health && echo "✅ API en ligne !" || echo "⚠️ API non disponible"

echo "=== Correction définitive terminée ==="
echo ""
echo "Commandes utiles pour le diagnostic:"
echo "  - Logs API: docker logs mar-api"
echo "  - Logs Ollama: docker logs mar-ollama"
echo "  - Test santé: curl http://localhost:8008/health"
echo "  - Test Ollama: docker exec mar-api curl http://ollama:11434/api/tags"
