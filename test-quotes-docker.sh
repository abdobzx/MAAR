#!/bin/bash

# Test ultra-rapide de la correction quotes Docker
echo "🔧 Test correction quotes Docker pour pydantic"
echo "=============================================="

echo "🐳 Création du Dockerfile de test quotes..."
cat > Dockerfile.quotes-test << 'EOF'
FROM python:3.11-slim

# Test avec quotes correctes
RUN pip install --no-cache-dir "pydantic>=2.9.0,<3.0.0"
RUN python -c "import pydantic; print('✅ Pydantic installé:', pydantic.VERSION)"

CMD ["echo", "Test quotes réussi"]
EOF

echo "🔨 Test de build avec quotes..."
if docker build -f Dockerfile.quotes-test -t quotes-test . >/dev/null 2>&1; then
    echo "✅ SUCCESS: Quotes Docker corrigées"
    docker rmi quotes-test >/dev/null 2>&1
else
    echo "❌ Problème avec les quotes"
fi

rm -f Dockerfile.quotes-test
echo "🚀 Script test-pydantic-fix.sh prêt avec quotes corrigées"
