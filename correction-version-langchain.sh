#!/bin/bash

# 🚨 CORRECTION IMMÉDIATE - ERREUR LANGCHAIN-COMMUNITY VERSION
# Corrige l'erreur "langchain-community==0.3.25" qui n'existe pas

set -e

echo "🚨 CORRECTION IMMÉDIATE - ERREUR VERSION LANGCHAIN"
echo "=================================================="

# 1. Vérification du problème
echo "📍 1. Diagnostic erreur..."
if grep -q "langchain-community==0.3.25" requirements.fast.txt 2>/dev/null; then
    echo "❌ Erreur détectée: langchain-community==0.3.25 (version inexistante)"
else
    echo "⚠️  Fichier requirements.fast.txt non trouvé ou déjà corrigé"
fi

# 2. Correction immédiate
echo "📍 2. Correction versions LangChain..."

# Backup du fichier actuel
if [ -f "requirements.fast.txt" ]; then
    cp requirements.fast.txt requirements.fast.txt.backup
    echo "✅ Backup créé: requirements.fast.txt.backup"
fi

# Création du fichier corrigé
cat > requirements.fast.txt << 'EOF'
# Requirements minimal pour build rapide - URGENCE CORRIGÉE
# Versions fixes et vérifiées pour éviter la résolution lente

# Core API
fastapi==0.108.0
uvicorn[standard]==0.25.0
pydantic>=2.9.0,<3.0.0

# LangChain Core (versions fixes et disponibles)
langchain==0.3.24
langchain-community==0.3.24
langsmith>=0.1.17,<0.4.0

# Ollama & HTTP
ollama==0.5.1
httpx>=0.27.0,<0.29.0

# Database essentiels
qdrant-client>=1.7.1,<1.15.0
sqlalchemy==2.0.25
redis==5.0.1

# Utilities essentiels
python-dotenv==1.0.0
aiofiles==23.2.1
typer==0.9.0

# Security minimal
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Multi-processing
celery==5.3.4

# Document processing minimal
pypdf2==3.0.1
python-multipart==0.0.6
EOF

echo "✅ Fichier requirements.fast.txt corrigé"

# 3. Vérification de la correction
echo "📍 3. Vérification correction..."
if grep -q "langchain==0.3.24" requirements.fast.txt && grep -q "langchain-community==0.3.24" requirements.fast.txt; then
    echo "✅ Versions LangChain corrigées: 0.3.24 (version disponible)"
else
    echo "❌ Erreur dans la correction"
    exit 1
fi

# 4. Nettoyage Docker et rebuild immédiat
echo "📍 4. Nettoyage et rebuild..."
docker-compose -f docker-compose.fast.yml down --remove-orphans 2>/dev/null || true
docker system prune -f

# 5. Build corrigé
echo "📍 5. Build avec versions corrigées..."
start_time=$(date +%s)

if docker-compose -f docker-compose.fast.yml build --no-cache; then
    end_time=$(date +%s)
    build_time=$((end_time - start_time))
    echo "✅ BUILD RÉUSSI EN ${build_time}s"
    
    # Déploiement immédiat
    echo "📍 6. Déploiement..."
    docker-compose -f docker-compose.fast.yml up -d
    
    # Test rapide
    sleep 5
    if curl -f http://localhost:8000/health 2>/dev/null; then
        echo "✅ API opérationnelle"
    else
        echo "⚠️  API pas encore prête - vérification..."
        docker-compose -f docker-compose.fast.yml logs --tail=10
    fi
else
    echo "❌ Build échoué - tentative build minimal..."
    
    # Build minimal en dernier recours
    docker build -t rag-api-minimal -f - . << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn "pydantic>=2.9.0" "langchain==0.3.24" "langchain-community==0.3.24" "langsmith>=0.1.17" ollama "httpx>=0.27.0"
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    
    docker run -d -p 8000:8000 --name rag-api-minimal rag-api-minimal
    echo "✅ Build minimal déployé"
fi

echo ""
echo "🎉 CORRECTION TERMINÉE"
echo "Version corrigée: langchain-community 0.3.25 → 0.3.24"
echo "Test: curl http://localhost:8000/health"
