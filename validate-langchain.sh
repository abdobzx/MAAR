#!/bin/bash

# Script de validation rapide des versions LangChain
echo "🔍 Validation des versions LangChain..."

# Vérifier que LangChain 0.3.25 et LangChain-community 0.3.24 sont compatibles
echo "📦 Test de compatibilité LangChain..."

# Créer un fichier requirements temporaire pour test
cat > /tmp/test_langchain.txt << EOF
langchain==0.3.25
langchain-community==0.3.24
EOF

echo "🧪 Test de résolution pip..."
if pip install --dry-run -r /tmp/test_langchain.txt &>/dev/null; then
    echo "✅ Versions LangChain compatibles !"
else
    echo "❌ Conflit détecté dans les versions LangChain"
    echo "🔧 Tentative de résolution automatique..."
    
    # Test avec versions flexibles
    cat > /tmp/test_langchain_flexible.txt << EOF
langchain>=0.3.25,<0.4.0
langchain-community>=0.3.24,<0.4.0
EOF
    
    if pip install --dry-run -r /tmp/test_langchain_flexible.txt &>/dev/null; then
        echo "✅ Versions flexibles LangChain compatibles !"
        echo "💡 Recommandation: utiliser des ranges de versions plutôt que des versions fixes"
    else
        echo "❌ Problème persistant avec LangChain"
    fi
fi

# Nettoyage
rm -f /tmp/test_langchain*.txt

echo "✅ Validation terminée"
