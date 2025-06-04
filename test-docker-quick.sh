#!/bin/bash
# Test rapide des dépendances Docker
# Version simplifiée pour validation rapide

echo "🔍 TEST RAPIDE DOCKER - RAG ENTERPRISE"
echo "======================================"

# Test 1: Build simple avec requirements
echo "1️⃣ Test build avec requirements.python313.txt..."

cat > Dockerfile.quick << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.python313.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import ollama, httpx, fastapi; print('✅ Dependencies OK')"
EOF

if docker build -f Dockerfile.quick -t rag-quick-test .; then
    echo "✅ Build réussi avec requirements.python313.txt"
    docker rmi rag-quick-test
else
    echo "❌ Échec build - problème de dépendances"
fi

rm -f Dockerfile.quick

# Test 2: Validation httpx/ollama spécifique
echo ""
echo "2️⃣ Test compatibilité httpx/ollama..."

docker run --rm python:3.11-slim sh -c "
pip install 'ollama==0.5.1' 'httpx>=0.27.0,<0.29.0' --quiet &&
python -c 'import ollama, httpx; print(f\"✅ ollama: {getattr(ollama, \"__version__\", \"OK\")}\"); print(f\"✅ httpx: {httpx.__version__}\"); print(\"✅ Compatibilité confirmée\")' || echo '❌ Incompatibilité détectée'
"

echo ""
echo "🎯 Test rapide terminé!"
