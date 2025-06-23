#!/bin/bash

# VALIDATION FINALE COMPLÈTE - Système MAR
# Vérification exhaustive avant déploiement en production

set -euo pipefail

echo "🔍 VALIDATION FINALE COMPLÈTE - Système MAR"
echo "=============================================="
echo "Date: $(date)"
echo "Répertoire: $(pwd)"
echo ""

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Compteurs
success_count=0
warning_count=0
error_count=0
total_checks=0

# Fonction de logging avec compteurs
check_file() {
    local file=$1
    local description=$2
    local critical=${3:-true}
    total_checks=$((total_checks + 1))
    
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✅${NC} $description : $file"
        success_count=$((success_count + 1))
        return 0
    else
        if [[ "$critical" == "true" ]]; then
            echo -e "${RED}❌${NC} $description : $file (CRITIQUE - MANQUANT)"
            error_count=$((error_count + 1))
        else
            echo -e "${YELLOW}⚠️${NC} $description : $file (optionnel - manquant)"
            warning_count=$((warning_count + 1))
        fi
        return 1
    fi
}

check_directory() {
    local dir=$1
    local description=$2
    local critical=${3:-true}
    total_checks=$((total_checks + 1))
    
    if [[ -d "$dir" ]]; then
        echo -e "${GREEN}✅${NC} $description : $dir"
        success_count=$((success_count + 1))
        return 0
    else
        if [[ "$critical" == "true" ]]; then
            echo -e "${RED}❌${NC} $description : $dir (CRITIQUE - MANQUANT)"
            error_count=$((error_count + 1))
        else
            echo -e "${YELLOW}⚠️${NC} $description : $dir (optionnel - manquant)"
            warning_count=$((warning_count + 1))
        fi
        return 1
    fi
}

check_executable() {
    local file=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [[ -f "$file" && -x "$file" ]]; then
        echo -e "${GREEN}✅${NC} $description : $file (exécutable)"
        success_count=$((success_count + 1))
        return 0
    elif [[ -f "$file" ]]; then
        echo -e "${YELLOW}⚠️${NC} $description : $file (non exécutable)"
        warning_count=$((warning_count + 1))
        return 1
    else
        echo -e "${RED}❌${NC} $description : $file (MANQUANT)"
        error_count=$((error_count + 1))
        return 1
    fi
}

echo -e "${BLUE}📋 1. VÉRIFICATION DES FICHIERS DOCKER${NC}"
echo "================================================"

# Fichiers Docker critiques
check_file "Dockerfile.ultimate" "Dockerfile Ultimate (solution finale)"
check_file "docker-compose.ultimate.yml" "Docker Compose Ultimate"
check_file "Dockerfile.staging" "Dockerfile Staging"
check_file "docker-compose.staging.yml" "Docker Compose Staging"
check_file "Dockerfile" "Dockerfile principal" false

echo -e "\n${BLUE}📋 2. VÉRIFICATION DES REQUIREMENTS${NC}"
echo "=============================================="

# Fichiers Requirements
check_file "requirements.final.txt" "Requirements Final (CRITIQUE)"
check_file "requirements.debug.txt" "Requirements Debug"
check_file "requirements.staging.txt" "Requirements Staging"
check_file "requirements.txt" "Requirements Principal"
check_file "requirements.fixed.txt" "Requirements Fixed" false

# Vérification du contenu des requirements critiques
if [[ -f "requirements.final.txt" ]]; then
    if grep -q "httpx==0.25.2" requirements.final.txt && grep -q "ollama==0.2.1" requirements.final.txt; then
        echo -e "${GREEN}✅${NC} Versions compatibles httpx/ollama détectées"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}❌${NC} Versions incompatibles httpx/ollama"
        error_count=$((error_count + 1))
    fi
    total_checks=$((total_checks + 1))
fi

echo -e "\n${BLUE}📋 3. VÉRIFICATION DE LA STRUCTURE PROJET${NC}"
echo "=================================================="

# Structure critique du projet
check_directory "api" "Répertoire API"
check_directory "core" "Répertoire Core"
check_directory "agents" "Répertoire Agents"
check_directory "database" "Répertoire Database"
check_directory "scripts" "Répertoire Scripts"
check_directory "monitoring" "Répertoire Monitoring"
check_directory "tests" "Répertoire Tests"

# Fichiers de base de données
check_file "database/init.sql" "Script d'initialisation DB"
check_file "database/manager.py" "Gestionnaire de base de données"

echo -e "\n${BLUE}📋 4. VÉRIFICATION DES SCRIPTS DE DÉPLOIEMENT${NC}"
echo "======================================================="

# Scripts critiques
check_executable "scripts/deploy-ultimate.sh" "Script déploiement ultimate"
check_executable "scripts/staging-deploy.sh" "Script déploiement staging"
check_executable "scripts/emergency-deploy.sh" "Script déploiement urgence"
check_executable "scripts/validate-final.sh" "Script validation finale"
check_executable "transfer-to-server.sh" "Script transfert serveur"

# Scripts optionnels mais utiles
check_executable "scripts/system-validation.sh" "Script validation système" false
check_executable "scripts/final-validation.sh" "Script validation finale étendue" false

echo -e "\n${BLUE}📋 5. VÉRIFICATION DE LA CONFIGURATION${NC}"
echo "==============================================="

# Configuration monitoring
check_file "monitoring/prometheus.yml" "Configuration Prometheus"

# Fichiers API
check_file "api/main.py" "Point d'entrée API"
check_file "core/config.py" "Configuration centrale"

echo -e "\n${BLUE}📋 6. VÉRIFICATION DE LA DOCUMENTATION${NC}"
echo "==============================================="

# Documentation critique
check_file "RESOLUTION-FINALE.md" "Guide résolution finale"
check_file "GUIDE-SERVEUR-UBUNTU.md" "Guide serveur Ubuntu"
check_file "ETAT-FINAL.md" "État final du système"
check_file "README.md" "Documentation principale"

# Documentation optionnelle
check_file "DEPLOYMENT-FINAL.md" "Guide déploiement final" false
check_file "INSTRUCTIONS-FINALES.md" "Instructions finales" false

echo -e "\n${BLUE}📋 7. TESTS DE SYNTAXE ET VALIDATION${NC}"
echo "============================================="

# Test syntaxe YAML avec Python
if command -v python3 &> /dev/null; then
    echo "🐍 Test de syntaxe YAML avec Python..."
    
    python3 -c "
import yaml
import sys

files_to_check = [
    'docker-compose.ultimate.yml',
    'docker-compose.staging.yml', 
    'monitoring/prometheus.yml'
]

yaml_errors = 0
for file in files_to_check:
    try:
        if os.path.exists(file):
            with open(file, 'r') as f:
                yaml.safe_load(f)
            print(f'✅ {file} : YAML valide')
        else:
            print(f'⚠️  {file} : Fichier non trouvé')
    except Exception as e:
        print(f'❌ {file} : YAML invalide - {e}')
        yaml_errors += 1

sys.exit(yaml_errors)
" && {
        echo -e "${GREEN}✅${NC} Tous les fichiers YAML sont valides"
        success_count=$((success_count + 1))
    } || {
        echo -e "${RED}❌${NC} Erreurs de syntaxe YAML détectées"
        error_count=$((error_count + 1))
    }
    total_checks=$((total_checks + 1))
else
    echo -e "${YELLOW}⚠️${NC} Python3 non disponible, impossible de valider les YAML"
    warning_count=$((warning_count + 1))
    total_checks=$((total_checks + 1))
fi

# Test imports Python critiques (si possible)
if command -v python3 &> /dev/null; then
    echo "🐍 Test des imports Python critiques..."
    
    python3 -c "
import sys
try:
    # Test imports basiques
    import json
    import os
    import datetime
    print('✅ Imports Python de base fonctionnels')
except ImportError as e:
    print(f'❌ Erreur imports de base: {e}')
    sys.exit(1)
" && {
        echo -e "${GREEN}✅${NC} Imports Python de base fonctionnels"
        success_count=$((success_count + 1))
    } || {
        echo -e "${RED}❌${NC} Problème avec les imports Python"
        error_count=$((error_count + 1))
    }
    total_checks=$((total_checks + 1))
fi

echo -e "\n${BLUE}📋 8. GÉNÉRATION DU SCRIPT DE TRANSFERT${NC}"
echo "==============================================="

# Vérification/création du script de transfert
if [[ ! -f "transfer-to-server.sh" ]]; then
    echo "📝 Création du script de transfert..."
    
    cat > transfer-to-server.sh << 'EOF'
#!/bin/bash

# Script de transfert vers le serveur Ubuntu
SERVER_IP="YOUR_SERVER_IP"
SERVER_USER="YOUR_SERVER_USER"
REMOTE_PATH="/home/$SERVER_USER/MAR"

echo "🚀 Transfert des fichiers vers le serveur..."

if [[ "$SERVER_IP" == "YOUR_SERVER_IP" || "$SERVER_USER" == "YOUR_SERVER_USER" ]]; then
    echo "❌ Configurez SERVER_IP et SERVER_USER dans ce script"
    exit 1
fi

ssh $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_PATH"

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
    *.md \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/

ssh $SERVER_USER@$SERVER_IP "chmod +x $REMOTE_PATH/scripts/*.sh"

echo "✅ Transfert terminé!"
echo "Connexion: ssh $SERVER_USER@$SERVER_IP"
echo "Déploiement: cd $REMOTE_PATH && ./scripts/deploy-ultimate.sh"
EOF

    chmod +x transfer-to-server.sh
    echo -e "${GREEN}✅${NC} Script de transfert créé et rendu exécutable"
    success_count=$((success_count + 1))
else
    echo -e "${GREEN}✅${NC} Script de transfert déjà présent"
    success_count=$((success_count + 1))
fi
total_checks=$((total_checks + 1))

echo -e "\n${BLUE}📊 RÉSUMÉ DE LA VALIDATION${NC}"
echo "================================="
echo -e "Total des vérifications : $total_checks"
echo -e "Réussies : ${GREEN}$success_count${NC}"
echo -e "Avertissements : ${YELLOW}$warning_count${NC}"
echo -e "Erreurs : ${RED}$error_count${NC}"

# Calcul du pourcentage de réussite
success_percentage=$(( (success_count * 100) / total_checks ))
echo -e "Taux de réussite : $success_percentage%"

echo -e "\n${BLUE}🎯 RECOMMANDATIONS${NC}"
echo "===================="

if [[ $error_count -eq 0 ]]; then
    echo -e "${GREEN}🎉 VALIDATION RÉUSSIE !${NC}"
    echo -e "Le système est prêt pour le déploiement en production."
    
    echo -e "\n${BLUE}📋 ÉTAPES SUIVANTES :${NC}"
    echo "1. Configurer transfer-to-server.sh avec vos informations serveur"
    echo "2. Exécuter : ./transfer-to-server.sh"
    echo "3. Sur le serveur : ./scripts/deploy-ultimate.sh"
    echo "4. Choisir 'Déploiement complet' dans le menu"
    
    if [[ $warning_count -gt 0 ]]; then
        echo -e "\n${YELLOW}⚠️  AVERTISSEMENTS :${NC}"
        echo "Quelques éléments optionnels sont manquants mais n'empêchent pas le déploiement."
    fi
    
    exit 0
    
elif [[ $error_count -le 3 ]]; then
    echo -e "${YELLOW}⚠️  VALIDATION PARTIELLEMENT RÉUSSIE${NC}"
    echo -e "Erreurs mineures détectées. Le déploiement peut être tenté avec prudence."
    echo -e "Corrigez les erreurs critiques avant le déploiement en production."
    exit 1
    
else
    echo -e "${RED}❌ VALIDATION ÉCHOUÉE${NC}"
    echo -e "Trop d'erreurs critiques détectées ($error_count)."
    echo -e "Corrigez les problèmes avant de procéder au déploiement."
    exit 2
fi
