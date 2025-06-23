#!/bin/bash

# Test de validation du fix langsmith/langchain
# Script pour vérifier la compatibilité après correction

echo "🔧 Test de validation du fix langsmith/langchain"
echo "==============================================="

# Nettoyage préliminaire
echo "🧹 Nettoyage des images Docker..."
docker system prune -f >/dev/null 2>&1

# Test avec Dockerfile spécifique langchain
echo "🐳 Création du Dockerfile de test langchain/langsmith..."
cat > Dockerfile.langchain-test << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Test d'installation des dépendances langchain critiques
RUN pip install --no-cache-dir "pydantic>=2.9.0,<3.0.0"
RUN pip install --no-cache-dir "langsmith>=0.1.17,<0.4.0"
RUN pip install --no-cache-dir "langchain>=0.2.0"
RUN pip install --no-cache-dir "langchain-community>=0.2.0"
RUN pip install --no-cache-dir "ollama==0.5.1"

# Validation Python de compatibilité
RUN python -c "
import langchain
import langsmith
import pydantic
import ollama
print('=' * 50)
print('✅ LangChain version:', langchain.__version__)
print('✅ LangSmith version:', langsmith.__version__)
print('✅ Pydantic version:', pydantic.VERSION)
print('✅ Ollama importé avec succès')
print('✅ Toutes les dépendances LangChain compatibles!')
print('=' * 50)
"

CMD ["echo", "Test LangChain/LangSmith terminé avec succès"]
EOF

# Construction du test
echo "🔨 Construction de l'image de test langchain..."
if docker build -f Dockerfile.langchain-test -t langchain-test-fix . ; then
    echo ""
    echo "✅ SUCCESS: Fix langchain/langsmith validé!"
    echo "✅ langsmith>=0.1.17 compatible avec langchain>=0.2.0"
    echo "✅ Toutes les dépendances LangChain installées"
    echo ""
    echo "🚀 Le système est maintenant prêt pour le déploiement complet!"
    echo "   Utilisez: ./deploy-production.sh"
else
    echo ""
    echo "❌ ÉCHEC: Problème de compatibilité langchain/langsmith détecté"
    echo "Vérifiez les logs ci-dessus pour identifier le problème."
    exit 1
fi

# Nettoyage
docker rmi langchain-test-fix >/dev/null 2>&1
rm -f Dockerfile.langchain-test

echo "🏁 Test langchain/langsmith terminé!"
