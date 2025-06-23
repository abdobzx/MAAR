#!/bin/bash

# 🚀 DÉMARRAGE IMMÉDIAT - Système MAR Production
echo "🚀 DÉMARRAGE IMMÉDIAT - Système MAR Production"
echo "=============================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📋 CHECKLIST FINALE${NC}"
echo "==================="

# Vérification des fichiers critiques
files_ok=true
critical_files=(
    "requirements.final.txt:Dépendances Python résolues"
    "Dockerfile.ultimate:Build Docker optimisé"
    "docker-compose.ultimate.yml:Stack infrastructure"
    "transfer-to-server.sh:Script de transfert"
    "scripts/deploy-ultimate.sh:Déploiement automatisé"
)

for item in "${critical_files[@]}"; do
    file="${item%:*}"
    desc="${item#*:}"
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✅${NC} $desc"
    else
        echo -e "${RED}❌${NC} $desc - MANQUANT: $file"
        files_ok=false
    fi
done

echo ""
echo -e "${BLUE}🔧 VÉRIFICATION CONFIGURATION${NC}"
echo "================================"

# Vérification configuration transfert
if grep -q "YOUR_SERVER_IP" transfer-to-server.sh; then
    echo -e "${YELLOW}⚠️${NC}  Configuration requise dans transfer-to-server.sh"
    echo "     Modifiez SERVER_IP et SERVER_USER"
    config_needed=true
else
    echo -e "${GREEN}✅${NC} Configuration transfert OK"
    config_needed=false
fi

# Vérification versions critiques
if grep -q "httpx==0.25.2" requirements.final.txt && grep -q "ollama==0.2.1" requirements.final.txt; then
    echo -e "${GREEN}✅${NC} Versions critiques httpx/ollama compatibles"
else
    echo -e "${RED}❌${NC} Problème versions httpx/ollama"
    files_ok=false
fi

echo ""
echo -e "${BLUE}📋 ACTIONS IMMÉDIATES${NC}"
echo "======================"

if [[ "$files_ok" == "true" ]]; then
    if [[ "$config_needed" == "true" ]]; then
        echo -e "${YELLOW}🔧 ÉTAPE 1 : CONFIGURATION REQUISE${NC}"
        echo "   Modifiez transfer-to-server.sh :"
        echo ""
        echo "   SERVER_IP=\"votre.ip.serveur\""
        echo "   SERVER_USER=\"votre-utilisateur\""
        echo ""
        echo -e "${GREEN}🚀 ÉTAPE 2 : TRANSFERT${NC}"
        echo "   ./transfer-to-server.sh"
        echo ""
        echo -e "${GREEN}🎯 ÉTAPE 3 : DÉPLOIEMENT${NC}"
        echo "   ssh votre-utilisateur@votre-serveur"
        echo "   cd MAR"
        echo "   ./scripts/deploy-ultimate.sh"
        echo "   → Choisir 'Déploiement complet'"
    else
        echo -e "${GREEN}🚀 SYSTÈME ENTIÈREMENT PRÊT !${NC}"
        echo ""
        echo "Exécutez immédiatement :"
        echo "./transfer-to-server.sh"
    fi
    
    echo ""
    echo -e "${BLUE}📈 RÉSULTATS ATTENDUS${NC}"
    echo "====================="
    echo "• API MAR : http://serveur:8000"
    echo "• Documentation : http://serveur:8000/docs"
    echo "• Health Check : http://serveur:8000/health"
    echo "• Monitoring : http://serveur:9090"
    
else
    echo -e "${RED}❌ PROBLÈMES DÉTECTÉS${NC}"
    echo "Consultez RESOLUTION-FINALE.md pour plus de détails"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 SYSTÈME MAR PRÊT POUR PRODUCTION !${NC}"
echo ""
echo "📚 Documentation disponible :"
echo "• INSTRUCTIONS-TRANSFERT.md - Guide de transfert"
echo "• GUIDE-SERVEUR-UBUNTU.md - Instructions serveur"
echo "• STATUT-FINAL-PRODUCTION.md - État détaillé"
echo ""
echo "⏱️  Temps estimé de déploiement : 15 minutes"
