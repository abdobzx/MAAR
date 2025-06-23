#!/bin/bash

# VALIDATION RAPIDE PRÉ-TRANSFERT
echo "🔍 VALIDATION RAPIDE PRÉ-TRANSFERT"
echo "=================================="

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

validation_passed=true

echo -e "\n📁 Vérification des fichiers critiques..."

# Fichiers essentiels
critical_files=(
    "requirements.final.txt"
    "Dockerfile.ultimate"
    "docker-compose.ultimate.yml"
    "transfer-to-server.sh"
    "scripts/deploy-ultimate.sh"
)

for file in "${critical_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file (MANQUANT)"
        validation_passed=false
    fi
done

echo -e "\n📋 Vérification des répertoires..."

# Répertoires essentiels
critical_dirs=(
    "scripts"
    "database"
    "monitoring"
)

for dir in "${critical_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        echo -e "${GREEN}✅${NC} $dir/"
    else
        echo -e "${RED}❌${NC} $dir/ (MANQUANT)"
        validation_passed=false
    fi
done

echo -e "\n🔍 Vérification des dépendances critiques..."

# Vérification des versions critiques
if grep -q "httpx==0.25.2" requirements.final.txt && grep -q "ollama==0.2.1" requirements.final.txt; then
    echo -e "${GREEN}✅${NC} Versions httpx et ollama compatibles"
else
    echo -e "${RED}❌${NC} Versions httpx ou ollama problématiques"
    validation_passed=false
fi

echo -e "\n🔧 Vérification des permissions..."

# Scripts exécutables
if [[ -x "transfer-to-server.sh" ]]; then
    echo -e "${GREEN}✅${NC} transfer-to-server.sh exécutable"
else
    echo -e "${YELLOW}⚠️${NC} Correction des permissions..."
    chmod +x transfer-to-server.sh
    echo -e "${GREEN}✅${NC} Permissions corrigées"
fi

if [[ -x "scripts/deploy-ultimate.sh" ]]; then
    echo -e "${GREEN}✅${NC} deploy-ultimate.sh exécutable"
else
    echo -e "${YELLOW}⚠️${NC} Correction des permissions..."
    chmod +x scripts/deploy-ultimate.sh
    echo -e "${GREEN}✅${NC} Permissions corrigées"
fi

echo -e "\n🔧 Vérification de la configuration de transfert..."

# Vérification du script de transfert
if grep -q "YOUR_SERVER_IP" transfer-to-server.sh; then
    echo -e "${YELLOW}⚠️${NC} Configuration requise dans transfer-to-server.sh"
    echo "   Modifiez SERVER_IP et SERVER_USER avant le transfert"
else
    echo -e "${GREEN}✅${NC} Script de transfert configuré"
fi

echo -e "\n" && echo "=================================="

if [[ "$validation_passed" == "true" ]]; then
    echo -e "${GREEN}🎉 VALIDATION RÉUSSIE !${NC}"
    echo -e "Le système est prêt pour le transfert."
    echo -e "\n📋 Prochaines étapes :"
    echo -e "1. Modifiez transfer-to-server.sh avec vos informations serveur"
    echo -e "2. Exécutez : ./transfer-to-server.sh"
    echo -e "3. Sur le serveur : ./scripts/deploy-ultimate.sh"
    echo -e "4. Choisir 'Déploiement complet' dans le menu"
else
    echo -e "${RED}❌ VALIDATION ÉCHOUÉE${NC}"
    echo -e "Corrigez les problèmes avant le transfert."
    exit 1
fi

echo -e "\n🚀 Système MAR prêt pour la production !"
