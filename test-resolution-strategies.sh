#!/bin/bash

# Script pour tester les différentes stratégies de résolution Docker

echo "🔧 Test des stratégies de résolution 'resolution-too-deep'"
echo "========================================================"

# Fonction pour tester un Dockerfile
test_dockerfile() {
    local dockerfile=$1
    local tag=$2
    
    echo ""
    echo "🧪 Test de $dockerfile -> $tag"
    echo "----------------------------------------"
    
    if docker build -f "$dockerfile" -t "$tag" . 2>&1 | tee "build-${tag}.log"; then
        echo "✅ $dockerfile: Build réussi"
        docker rmi "$tag" 2>/dev/null || true
        return 0
    else
        echo "❌ $dockerfile: Build échoué"
        echo "📋 Dernières lignes du log:"
        tail -10 "build-${tag}.log"
        return 1
    fi
}

# Fonction pour vérifier Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker n'est pas installé"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "❌ Docker daemon n'est pas en cours d'exécution"
        echo "   Démarrez Docker et relancez ce script"
        exit 1
    fi
    
    echo "✅ Docker est disponible"
}

# Vérifier que Docker fonctionne
check_docker

# Nettoyer les anciens logs
rm -f build-*.log

# Tester les différentes stratégies
echo ""
echo "🎯 Stratégies à tester:"
echo "1. Dockerfile.progressive - Installation progressive avec fallback"
echo "2. Dockerfile.phased - Installation en phases séparées"
echo "3. requirements.staging.txt simplifié"

success_count=0
total_count=0

# Test 1: Dockerfile progressif
if [ -f "Dockerfile.progressive" ]; then
    ((total_count++))
    if test_dockerfile "Dockerfile.progressive" "test-progressive"; then
        ((success_count++))
    fi
fi

# Test 2: Dockerfile par phases
if [ -f "Dockerfile.phased" ] && [ -f "requirements.core.txt" ] && [ -f "requirements.ai.txt" ]; then
    ((total_count++))
    if test_dockerfile "Dockerfile.phased" "test-phased"; then
        ((success_count++))
    fi
else
    echo "⚠️  Dockerfile.phased ou fichiers requirements manquants"
fi

# Résumé
echo ""
echo "========================================================"
echo "📊 RÉSULTATS:"
echo "Succès: $success_count/$total_count"

if [ $success_count -gt 0 ]; then
    echo "✅ Au moins une stratégie fonctionne!"
    echo ""
    echo "💡 RECOMMANDATIONS:"
    echo "1. Utilisez la stratégie qui a fonctionné"
    echo "2. Le problème 'resolution-too-deep' est résolu"
    echo "3. Votre build Docker devrait maintenant réussir"
else
    echo "❌ Toutes les stratégies ont échoué"
    echo ""
    echo "🔍 PROCHAINES ÉTAPES:"
    echo "1. Vérifiez les logs de build: build-*.log"
    echo "2. Simplifiez encore plus les requirements"
    echo "3. Considérez l'utilisation d'une image de base différente"
fi

# Nettoyer les images de test
docker rmi test-progressive test-phased 2>/dev/null || true

echo ""
echo "📁 Logs disponibles:"
ls -la build-*.log 2>/dev/null || echo "Aucun log généré"
