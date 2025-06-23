#!/bin/bash

# Script de résolution ultime des conflits de dépendances
# À exécuter sur le serveur de staging

set -euo pipefail

# Configuration
WORK_DIR="~/AI_Deplyment_First_step/MAAR"
BACKUP_DIR="~/backup_$(date +%Y%m%d_%H%M%S)"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Sauvegarde des fichiers actuels
backup_current_state() {
    log_info "Sauvegarde de l'état actuel..."
    
    mkdir -p "$BACKUP_DIR"
    cp -r "$WORK_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
    
    log_success "Sauvegarde créée dans $BACKUP_DIR"
}

# Nettoyage complet Docker
complete_docker_cleanup() {
    log_info "Nettoyage complet de l'environnement Docker..."
    
    # Arrêter tous les conteneurs
    docker stop $(docker ps -aq) 2>/dev/null || true
    
    # Supprimer tous les conteneurs
    docker rm $(docker ps -aq) 2>/dev/null || true
    
    # Supprimer toutes les images
    docker rmi $(docker images -q) -f 2>/dev/null || true
    
    # Nettoyage complet du système Docker
    docker system prune -af --volumes
    
    log_success "Environnement Docker complètement nettoyé"
}

# Correction forcée des fichiers requirements
fix_requirements_files() {
    log_info "Correction forcée des fichiers requirements..."
    
    cd "$WORK_DIR"
    
    # Créer requirements.staging.txt optimisé
    cat > requirements.staging.txt << 'EOF'
# Core Framework
fastapi>=0.108.0
uvicorn[standard]>=0.25.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Multi-Agent Framework (SothemaAI focused)
crewai>=0.11.2
langchain>=0.2.0
langchain-community>=0.2.0
langgraph>=0.0.55

# Vector Database & Search
qdrant-client>=1.7.0
weaviate-client>=3.25.0
elasticsearch>=8.11.0
rank-bm25>=0.2.2

# HTTP Client - Version compatible
httpx>=0.25.0,<0.26.0
aiohttp>=3.9.0

# Embeddings & LLMs (SothemaAI focused)
sentence-transformers>=2.2.0
transformers>=4.36.0
torch>=2.1.0
ollama>=0.2.0

# Document Processing
pypdf2>=3.0.0
python-docx>=1.1.0
python-multipart>=0.0.6
pytesseract>=0.3.10
pillow>=10.1.0

# Database
asyncpg>=0.29.0
redis>=5.0.0
sqlalchemy>=2.0.25

# Security
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
cryptography>=41.0.0

# Utilities
aiofiles>=23.2.0
python-dotenv>=1.0.0
structlog>=23.2.0
celery>=5.3.0

# Monitoring
prometheus-client>=0.19.0
opentelemetry-api>=1.22.0
opentelemetry-sdk>=1.22.0
EOF

    # Vérifier que requirements.txt est aussi correct
    sed -i 's/httpx==0.26.0/httpx>=0.25.0,<0.26.0/g' requirements.txt 2>/dev/null || true
    sed -i 's/ollama==0.1.7/ollama>=0.2.0/g' requirements.txt 2>/dev/null || true
    
    # Corriger requirements-minimal.txt
    sed -i 's/httpx==0.26.0/httpx>=0.25.0,<0.26.0/g' requirements-minimal.txt 2>/dev/null || true
    sed -i 's/ollama==0.1.7/ollama>=0.2.0/g' requirements-minimal.txt 2>/dev/null || true
    
    log_success "Fichiers requirements corrigés"
}

# Créer un Dockerfile ultra-optimisé
create_optimized_dockerfile() {
    log_info "Création d'un Dockerfile optimisé pour staging..."
    
    cat > Dockerfile.staging.fixed << 'EOF'
FROM python:3.11-slim as builder

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer l'environnement virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copier et installer les dépendances
COPY requirements.staging.txt /tmp/requirements.txt

# Installation des dépendances avec résolution de conflits
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    "httpx>=0.25.0,<0.26.0" \
    "ollama>=0.2.0" \
    "fastapi>=0.108.0" \
    "uvicorn[standard]>=0.25.0" \
    "pydantic>=2.5.0" \
    "qdrant-client>=1.7.0" \
    "redis>=5.0.0" \
    "asyncpg>=0.29.0" \
    "sqlalchemy>=2.0.25" \
    "sentence-transformers>=2.2.0" \
    "transformers>=4.36.0" \
    "torch>=2.1.0" \
    "langchain>=0.2.0" \
    "crewai>=0.11.2" \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Stage de production
FROM python:3.11-slim as production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Installer les dépendances runtime
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Créer l'utilisateur
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copier l'environnement virtuel
COPY --from=builder /opt/venv /opt/venv

# Créer les répertoires
RUN mkdir -p /app/logs /app/data /app/uploads && \
    chown -R appuser:appuser /app

# Copier le code application
WORKDIR /app
COPY --chown=appuser:appuser . .

# Configurer l'utilisateur
USER appuser

# Créer le script d'entrée
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'set -e' >> /app/entrypoint.sh && \
    echo 'echo "Starting MAR API..."' >> /app/entrypoint.sh && \
    echo 'exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
EOF

    log_success "Dockerfile optimisé créé"
}

# Modifier docker-compose pour utiliser le Dockerfile fixé
update_docker_compose() {
    log_info "Mise à jour du docker-compose..."
    
    # Backup du fichier original
    cp docker-compose.staging.yml docker-compose.staging.yml.backup
    
    # Modifier pour utiliser le nouveau Dockerfile
    sed -i 's/dockerfile: Dockerfile.staging/dockerfile: Dockerfile.staging.fixed/g' docker-compose.staging.yml
    
    log_success "Docker-compose mis à jour"
}

# Test de construction
test_build() {
    log_info "Test de construction de l'image..."
    
    docker build -f Dockerfile.staging.fixed -t mar-staging-test .
    
    if [ $? -eq 0 ]; then
        log_success "Construction réussie!"
        return 0
    else
        log_error "Échec de la construction"
        return 1
    fi
}

# Déploiement final
deploy_staging() {
    log_info "Déploiement final en staging..."
    
    # Démarrer avec le nouveau setup
    docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d --build
    
    # Attendre le démarrage
    sleep 30
    
    # Test de santé
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        log_success "Déploiement réussi! API accessible"
        return 0
    else
        log_error "L'API n'est pas accessible"
        docker-compose -f docker-compose.yml -f docker-compose.staging.yml logs --tail=50
        return 1
    fi
}

# Fonction principale
main() {
    log_info "Début de la résolution ultime des conflits de dépendances"
    
    backup_current_state
    complete_docker_cleanup
    fix_requirements_files
    create_optimized_dockerfile
    update_docker_compose
    
    if test_build; then
        deploy_staging
        log_success "🎉 Déploiement staging complété avec succès!"
    else
        log_error "Échec du déploiement. Consultez les logs ci-dessus."
        exit 1
    fi
}

# Exécuter si appelé directement
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
EOF
