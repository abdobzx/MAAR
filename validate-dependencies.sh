#!/bin/bash
# Script de validation des dépendances corrigées

echo "🔍 Validation des dépendances corrigées - RAG Multi-Agent System"
echo "=================================================================="

# Test 1: Validation des requirements principaux
echo "📦 Test 1: Validation des requirements principaux..."
pip install --dry-run -r requirements.txt > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Requirements principaux: Compatible"
else
    echo "❌ Requirements principaux: Conflit détecté"
    exit 1
fi

# Test 2: Validation des requirements staging
echo "📦 Test 2: Validation des requirements staging..."
pip install --dry-run -r requirements.staging.txt > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Requirements staging: Compatible"
else
    echo "❌ Requirements staging: Conflit détecté"
    exit 1
fi

# Test 3: Test de compatibilité ollama + httpx
echo "📦 Test 3: Test de compatibilité ollama + httpx..."
pip install --dry-run 'ollama==0.5.1' 'httpx>=0.27.0,<0.29.0' > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Ollama + httpx: Compatible"
else
    echo "❌ Ollama + httpx: Conflit détecté"
    exit 1
fi

# Test 4: Test de compatibilité qdrant-client + httpx
echo "📦 Test 4: Test de compatibilité qdrant-client + httpx..."
pip install --dry-run 'qdrant-client==1.7.0' 'httpx>=0.27.0,<0.29.0' > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Qdrant-client + httpx: Compatible"
else
    echo "❌ Qdrant-client + httpx: Conflit détecté"
    exit 1
fi

# Test 5: Test des packages FastAPI
echo "📦 Test 5: Test des packages FastAPI..."
pip install --dry-run 'fastapi==0.108.0' 'uvicorn[standard]==0.25.0' > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ FastAPI + Uvicorn: Compatible"
else
    echo "❌ FastAPI + Uvicorn: Conflit détecté"
    exit 1
fi

echo ""
echo "🎉 Toutes les validations des dépendances ont réussi!"
echo "Le système est prêt pour le déploiement Docker."
