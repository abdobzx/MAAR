#!/bin/bash

# ✅ VÉRIFICATION FINALE - SOLUTION BUILD 43MIN READY
# Valide que tous les fichiers et solutions sont prêts

set -e

echo "✅ VÉRIFICATION FINALE SOLUTION BUILD 43MIN"
echo "==========================================="

ERRORS=0

# Fonction de vérification
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        size=$(wc -l < "$file" 2>/dev/null || echo "0")
        echo "✅ $description : $file ($size lignes)"
    else
        echo "❌ MANQUANT : $file"
        ((ERRORS++))
    fi
}

check_executable() {
    local file=$1
    local description=$2
    
    if [ -x "$file" ]; then
        echo "✅ $description : $file (exécutable)"
    else
        echo "❌ NON EXÉCUTABLE : $file"
        ((ERRORS++))
    fi
}

echo ""
echo "📋 1. FICHIERS DE CONFIGURATION"
echo "------------------------------"
check_file "requirements.fast.txt" "Requirements optimisés"
check_file "Dockerfile.fast" "Dockerfile optimisé"
check_file "docker-compose.fast.yml" "Docker Compose rapide"

echo ""
echo "📋 2. SCRIPTS D'INTERVENTION"
echo "---------------------------"
check_executable "solution-43min-build.sh" "Solution automatique"
check_executable "urgence-rebuild.sh" "Rebuild d'urgence"
check_executable "transfert-urgence-ubuntu.sh" "Transfert serveur"

echo ""
echo "📋 3. SCRIPTS DE TEST"
echo "-------------------"
check_executable "test-build-comparison.sh" "Comparaison builds"

echo ""
echo "📋 4. DOCUMENTATION"
echo "------------------"
check_file "RAPPORT-SOLUTION-43MIN.md" "Rapport solution complète"
check_file "SOLUTION-URGENCE-BUILD.md" "Guide urgence"

echo ""
echo "📋 5. VALIDATION CONTENU requirements.fast.txt"
echo "----------------------------------------------"
if [ -f "requirements.fast.txt" ]; then
    deps_count=$(grep -v '^#' requirements.fast.txt | grep -v '^$' | wc -l)
    echo "📦 Nombre dépendances : $deps_count"
    
    # Vérification dépendances critiques
    critical_deps=("fastapi" "uvicorn" "pydantic" "langchain" "ollama")
    for dep in "${critical_deps[@]}"; do
        if grep -q "$dep" requirements.fast.txt; then
            echo "✅ Dépendance critique : $dep"
        else
            echo "❌ MANQUANT : $dep"
            ((ERRORS++))
        fi
    done
fi

echo ""
echo "📋 6. VALIDATION DOCKERFILE.FAST"
echo "-------------------------------"
if [ -f "Dockerfile.fast" ]; then
    if grep -q "requirements.fast.txt" Dockerfile.fast; then
        echo "✅ Dockerfile utilise requirements.fast.txt"
    else
        echo "❌ Dockerfile n'utilise pas requirements.fast.txt"
        ((ERRORS++))
    fi
    
    if grep -q "timeout" Dockerfile.fast; then
        echo "✅ Timeouts configurés"
    else
        echo "⚠️  Pas de timeout configuré"
    fi
fi

echo ""
echo "📊 RÉSUMÉ FINAL"
echo "==============="

if [ $ERRORS -eq 0 ]; then
    echo "🎉 TOUTES LES VÉRIFICATIONS PASSÉES"
    echo ""
    echo "🚀 PRÊT POUR DÉPLOIEMENT URGENCE :"
    echo "1. Sur serveur Ubuntu : docker-compose down --remove-orphans"
    echo "2. Transfert : ./transfert-urgence-ubuntu.sh user@server"
    echo "3. Exécution : ./solution-43min-build.sh"
    echo ""
    echo "⏱️  Temps attendu : 2-5 minutes (vs 43 minutes avant)"
    exit 0
else
    echo "❌ $ERRORS ERREURS DÉTECTÉES"
    echo ""
    echo "🔧 Actions requises :"
    echo "- Vérifier les fichiers manquants"
    echo "- Rendre les scripts exécutables : chmod +x *.sh"
    echo "- Relancer cette vérification"
    exit 1
fi
