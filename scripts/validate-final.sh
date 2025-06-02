#!/bin/bash

# Script de validation finale avant transfert vers le serveur
# Vérifie tous les fichiers et configurations nécessaires

set -euo pipefail

echo "🔍 Validation finale du système MAR avant transfert"
echo "=================================================="

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success_count=0
total_checks=0

# Fonction de vérification
check_file() {
    local file=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✅${NC} $description : $file"
        success_count=$((success_count + 1))
        return 0
    else
        echo -e "${RED}❌${NC} $description : $file (MANQUANT)"
        return 1
    fi
}

check_directory() {
    local dir=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [[ -d "$dir" ]]; then
        echo -e "${GREEN}✅${NC} $description : $dir"
        success_count=$((success_count + 1))
        return 0
    else
        echo -e "${RED}❌${NC} $description : $dir (MANQUANT)"
        return 1
    fi
}

echo "🔍 Vérification des fichiers de configuration Docker..."

# Fichiers Docker
check_file "Dockerfile.ultimate" "Dockerfile Ultimate"
check_file "docker-compose.ultimate.yml" "Docker Compose Ultimate"
check_file "Dockerfile.staging" "Dockerfile Staging"
check_file "docker-compose.staging.yml" "Docker Compose Staging"

echo -e "\n🔍 Vérification des fichiers de requirements..."

# Fichiers Requirements
check_file "requirements.final.txt" "Requirements Final (versions compatibles)"
check_file "requirements.debug.txt" "Requirements Debug (minimal)"
check_file "requirements.staging.txt" "Requirements Staging"
check_file "requirements.txt" "Requirements Principal"

echo -e "\n🔍 Vérification de la structure du projet..."

# Structure du projet
check_directory "api" "Répertoire API"
check_directory "core" "Répertoire Core"
check_directory "agents" "Répertoire Agents"
check_directory "database" "Répertoire Database"
check_directory "scripts" "Répertoire Scripts"
check_directory "monitoring" "Répertoire Monitoring"

echo -e "\n🔍 Vérification des scripts de déploiement..."

# Scripts
check_file "scripts/deploy-ultimate.sh" "Script de déploiement ultimate"
check_file "scripts/staging-deploy.sh" "Script de déploiement staging"
check_file "scripts/emergency-deploy.sh" "Script de déploiement d'urgence"

echo -e "\n🔍 Vérification des fichiers de configuration..."

# Configuration
check_file "database/init.sql" "Script d'initialisation DB"
check_file "monitoring/prometheus.yml" "Configuration Prometheus"

echo -e "\n🔍 Vérification de la documentation..."

# Documentation
check_file "RESOLUTION-FINALE.md" "Guide de résolution finale"
check_file "DEPLOYMENT-FINAL.md" "Guide de déploiement final"
check_file "INSTRUCTIONS-FINALES.md" "Instructions finales"

echo -e "\n🔍 Vérification des permissions des scripts..."

# Permissions
if [[ -x "scripts/deploy-ultimate.sh" ]]; then
    echo -e "${GREEN}✅${NC} Script deploy-ultimate.sh exécutable"
    success_count=$((success_count + 1))
else
    echo -e "${RED}❌${NC} Script deploy-ultimate.sh non exécutable"
fi
total_checks=$((total_checks + 1))

echo -e "\n🔍 Analyse des conflits de dépendances..."

# Vérification des versions dans requirements.final.txt
if grep -q "httpx==0.25.2" requirements.final.txt && grep -q "ollama==0.2.1" requirements.final.txt; then
    echo -e "${GREEN}✅${NC} Versions compatibles httpx et ollama détectées"
    success_count=$((success_count + 1))
else
    echo -e "${RED}❌${NC} Versions incompatibles ou manquantes"
fi
total_checks=$((total_checks + 1))

echo -e "\n🔍 Vérification de la syntaxe des fichiers YAML..."

# Validation YAML (si yamllint est disponible)
if command -v python3 &> /dev/null; then
    python3 -c "
import yaml
import sys

files_to_check = [
    'docker-compose.ultimate.yml',
    'docker-compose.staging.yml',
    'monitoring/prometheus.yml'
]

for file in files_to_check:
    try:
        with open(file, 'r') as f:
            yaml.safe_load(f)
        print(f'✅ {file} : YAML valide')
    except Exception as e:
        print(f'❌ {file} : YAML invalide - {e}')
        sys.exit(1)
"
    success_count=$((success_count + 1))
else
    echo -e "${YELLOW}⚠️${NC} Python3 non disponible, impossible de valider les YAML"
fi
total_checks=$((total_checks + 1))

echo -e "\n🔍 Création d'un fichier de transfert..."

# Création d'un script de transfert
cat > transfer-to-server.sh << 'EOF'
#!/bin/bash

# Script de transfert vers le serveur Ubuntu
# Remplacez les variables par vos valeurs

SERVER_IP="YOUR_SERVER_IP"
SERVER_USER="YOUR_SERVER_USER"
REMOTE_PATH="/home/$SERVER_USER/MAR"

echo "🚀 Transfert des fichiers vers le serveur..."

# Création du répertoire distant
ssh $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_PATH"

# Transfert des fichiers essentiels
rsync -avz --progress \
    requirements.final.txt \
    requirements.debug.txt \
    Dockerfile.ultimate \
    docker-compose.ultimate.yml \
    database/ \
    monitoring/ \
    scripts/ \
    api/ \
    core/ \
    agents/ \
    RESOLUTION-FINALE.md \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/

echo "✅ Transfert terminé"
echo "Prochaine étape : ssh $SERVER_USER@$SERVER_IP 'cd $REMOTE_PATH && ./scripts/deploy-ultimate.sh'"
EOF

chmod +x transfer-to-server.sh
echo -e "${GREEN}✅${NC} Script de transfert créé : transfer-to-server.sh"

echo -e "\n📊 Résumé de la validation..."
echo "=============================="
echo -e "Total des vérifications : $total_checks"
echo -e "Réussies : ${GREEN}$success_count${NC}"
echo -e "Échouées : ${RED}$((total_checks - success_count))${NC}"

if [[ $success_count -eq $total_checks ]]; then
    echo -e "\n${GREEN}🎉 VALIDATION RÉUSSIE !${NC}"
    echo -e "Le système est prêt pour le transfert vers le serveur."
    echo -e "\nÉtapes suivantes :"
    echo -e "1. Modifier transfer-to-server.sh avec vos informations de serveur"
    echo -e "2. Exécuter : ./transfer-to-server.sh"
    echo -e "3. Se connecter au serveur et exécuter : ./scripts/deploy-ultimate.sh"
else
    echo -e "\n${RED}❌ VALIDATION ÉCHOUÉE${NC}"
    echo -e "Veuillez corriger les problèmes avant le transfert."
    exit 1
fi
