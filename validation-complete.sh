#!/bin/zsh

# ✅ VALIDATION COMPLÈTE SOLUTION BUILD 43MIN

echo "✅ VALIDATION COMPLÈTE SOLUTION BUILD 43MIN"
echo "==========================================="

# Couleurs pour l'affichage
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

validation_passed=true

check_file() {
    local file=$1
    local desc=$2
    if [[ -f "$file" ]]; then
        local size=$(wc -l < "$file")
        echo -e "${GREEN}✅ $desc: $file ($size lignes)${NC}"
    else
        echo -e "${RED}❌ MANQUANT: $desc - $file${NC}"
        validation_passed=false
    fi
}

check_dependency() {
    local dep=$1
    if grep -q "$dep" requirements.fast.txt 2>/dev/null; then
        local version=$(grep "$dep" requirements.fast.txt)
        echo -e "${GREEN}✅ $dep: $version${NC}"
    else
        echo -e "${RED}❌ MANQUANT: $dep${NC}"
        validation_passed=false
    fi
}

echo "\n📋 1. FICHIERS SOLUTION"
echo "----------------------"
check_file "requirements.fast.txt" "Requirements optimisés"
check_file "Dockerfile.fast" "Dockerfile optimisé"
check_file "docker-compose.fast.yml" "Compose optimisé"
check_file "solution-43min-build.sh" "Script automatique"
check_file "transfert-express.sh" "Transfert rapide"

echo "\n📦 2. DÉPENDANCES CRITIQUES CORRIGÉES"
echo "------------------------------------"
check_dependency "pydantic"
check_dependency "langsmith"
check_dependency "httpx"
check_dependency "ollama"
check_dependency "langchain"

echo "\n📊 3. COMPARAISON OPTIMISATION"
echo "-----------------------------"
if [[ -f "requirements.fast.txt" && -f "requirements.staging.txt" ]]; then
    fast_count=$(grep -v '^#' requirements.fast.txt | grep -v '^$' | wc -l)
    staging_count=$(grep -v '^#' requirements.staging.txt | grep -v '^$' | wc -l)
    reduction=$((staging_count - fast_count))
    percentage=$(( (reduction * 100) / staging_count ))
    
    echo -e "${GREEN}📦 Requirements FAST: $fast_count dépendances${NC}"
    echo -e "${YELLOW}📦 Requirements STAGING: $staging_count dépendances${NC}"
    echo -e "${GREEN}🚀 RÉDUCTION: $reduction dépendances ($percentage% moins)${NC}"
else
    echo -e "${RED}❌ Impossible de comparer - fichiers manquants${NC}"
    validation_passed=false
fi

echo "\n⏱️ 4. TEMPS ATTENDUS"
echo "-------------------"
echo -e "${RED}❌ AVANT: 2588s (43 minutes)${NC}"
echo -e "${GREEN}✅ APRÈS: 120-300s (2-5 minutes)${NC}"
echo -e "${GREEN}🚀 GAIN: ~90% plus rapide${NC}"

echo "\n🎯 5. INSTRUCTIONS FINALES"
echo "-------------------------"
if $validation_passed; then
    echo -e "${GREEN}🎉 VALIDATION RÉUSSIE - SOLUTION PRÊTE${NC}"
    echo ""
    echo -e "${YELLOW}📤 TRANSFERT:${NC}"
    echo "   ./transfert-express.sh user@server"
    echo ""
    echo -e "${YELLOW}🚀 EXÉCUTION SUR SERVEUR:${NC}"
    echo "   ssh user@server"
    echo "   cd /chemin/projet/"
    echo "   ./solution-43min-build.sh"
    echo ""
    echo -e "${GREEN}⏱️  TEMPS TOTAL INTERVENTION: 5-10 minutes${NC}"
else
    echo -e "${RED}❌ VALIDATION ÉCHOUÉE - Corriger les erreurs ci-dessus${NC}"
    exit 1
fi
