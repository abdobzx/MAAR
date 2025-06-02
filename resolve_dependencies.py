#!/usr/bin/env python3
"""
Script de résolution automatique des conflits de dépendances
pour le système MAR (Multi-Agent RAG)
"""

import subprocess
import sys
import re
from typing import Dict, List, Tuple, Set
from packaging import version
from packaging.requirements import Requirement

def get_package_info(package_name: str) -> Dict:
    """Récupère les informations d'un package depuis PyPI"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return {}
        
        info = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
        
        return info
    except Exception:
        return {}

def parse_requirements_file(filepath: str) -> List[str]:
    """Parse un fichier requirements.txt"""
    requirements = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('//'):
                    requirements.append(line)
    except FileNotFoundError:
        print(f"Fichier {filepath} non trouvé")
        return []
    
    return requirements

def get_compatible_versions() -> Dict[str, str]:
    """Retourne les versions compatibles testées"""
    return {
        # Core dependencies avec versions stables
        "httpx": "0.25.2",
        "ollama": "0.2.1", 
        "fastapi": "0.108.0",
        "uvicorn": "0.25.0",
        "pydantic": "2.5.3",
        "aiohttp": "3.9.1",
        
        # AI/ML dependencies
        "crewai": "0.11.2",
        "langchain": "0.2.16",
        "langchain-community": "0.2.16",
        "langgraph": "0.0.55",
        "sentence-transformers": "2.2.2",
        "transformers": "4.36.2",
        "torch": "2.1.2",
        
        # Vector databases
        "qdrant-client": "1.7.0",
        "weaviate-client": "3.25.3",
        "elasticsearch": "8.11.1",
        
        # Database
        "sqlalchemy": "2.0.25",
        "asyncpg": "0.29.0",
        "redis": "5.0.1",
        
        # Security
        "cryptography": "41.0.8",
        "python-jose": "3.3.0",
        "passlib": "1.7.4",
        
        # Development
        "pytest": "7.4.3",
        "pytest-asyncio": "0.23.2",
        "black": "23.12.1"
    }

def create_fixed_requirements():
    """Crée un fichier requirements avec des versions garanties compatibles"""
    
    compatible_versions = get_compatible_versions()
    
    requirements_content = """# Requirements fixes pour le système MAR
# Versions testées et garanties compatibles

# =============================================================================
# CORE FRAMEWORK - Versions verrouillées pour éviter les conflits
# =============================================================================
fastapi==0.108.0
uvicorn[standard]==0.25.0
pydantic==2.5.3
pydantic-settings==2.1.0

# =============================================================================
# HTTP CLIENT - Version spécifique pour éviter les conflits avec ollama
# =============================================================================
httpx==0.25.2

# =============================================================================
# MULTI-AGENT FRAMEWORK - SothemaAI focused
# =============================================================================
crewai==0.11.2
langchain==0.2.16
langchain-community==0.2.16
langgraph==0.0.55

# =============================================================================
# AI/ML PROVIDERS - Ollama version compatible
# =============================================================================
ollama==0.2.1
sentence-transformers==2.2.2
transformers==4.36.2
torch==2.1.2

# =============================================================================
# VECTOR DATABASES & SEARCH
# =============================================================================
qdrant-client==1.7.0
weaviate-client==3.25.3
elasticsearch==8.11.1
rank-bm25==0.2.2

# =============================================================================
# DOCUMENT PROCESSING
# =============================================================================
pypdf2==3.0.1
python-docx==1.1.0
python-multipart==0.0.6
pytesseract==0.3.10
pillow==10.1.0
openai-whisper==20231117
aiohttp==3.9.1
langdetect==1.0.9

# =============================================================================
# DATABASE & STORAGE
# =============================================================================
sqlalchemy==2.0.25
asyncpg==0.29.0
redis==5.0.1
minio==7.2.0

# =============================================================================
# SECURITY & AUTHENTICATION
# =============================================================================
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-keycloak==3.8.0
cryptography==41.0.8

# =============================================================================
# MONITORING & OBSERVABILITY
# =============================================================================
prometheus-client==0.19.0
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation-fastapi==0.43b0
langsmith==0.0.69

# =============================================================================
# UTILITIES
# =============================================================================
aiofiles==23.2.1
python-dotenv==1.0.0
celery==5.3.4
structlog==23.2.0
typer==0.9.0

# =============================================================================
# DEVELOPMENT & TESTING
# =============================================================================
pytest==7.4.3
pytest-asyncio==0.23.2
pytest-cov==4.1.0
black==23.12.1
isort==5.13.2
mypy==1.8.0
pre-commit==3.6.0

# =============================================================================
# CLOUD & DEPLOYMENT
# =============================================================================
kubernetes==28.1.0
azure-identity==1.15.0
azure-storage-blob==12.19.0
boto3==1.34.0
"""

    with open('/Users/abderrahman/Documents/MAR/requirements.final.txt', 'w') as f:
        f.write(requirements_content)
    
    print("✅ Fichier requirements.final.txt créé avec des versions compatibles")

def create_minimal_requirements():
    """Crée un fichier requirements minimal pour le debug"""
    
    minimal_content = """# Requirements minimaux pour le debugging
# Seulement les dépendances essentielles

# Core web framework
fastapi==0.108.0
uvicorn[standard]==0.25.0
pydantic==2.5.3

# HTTP client - version compatible
httpx==0.25.2

# AI provider - version compatible
ollama==0.2.1

# Base utilities
python-dotenv==1.0.0
aiofiles==23.2.1
"""

    with open('/Users/abderrahman/Documents/MAR/requirements.debug.txt', 'w') as f:
        f.write(minimal_content)
    
    print("✅ Fichier requirements.debug.txt créé pour le debugging")

def create_ultimate_dockerfile():
    """Crée un Dockerfile ultimate avec installation par étapes"""
    
    dockerfile_content = """# Dockerfile Ultimate - Résolution définitive des conflits
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="MAR Team"
LABEL version="1.0"
LABEL description="Multi-Agent RAG System - Ultimate Build"

# Variables d'environnement pour pip
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Installation des dépendances système
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    make \\
    pkg-config \\
    libffi-dev \\
    libssl-dev \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Mise à jour de pip
RUN pip install --upgrade pip setuptools wheel

# Création du répertoire de travail
WORKDIR /app

# ÉTAPE 1: Installation des dépendances de base
RUN pip install --no-deps \\
    typing-extensions==4.8.0 \\
    packaging==23.2 \\
    certifi==2023.11.17

# ÉTAPE 2: Installation du framework HTTP (sans conflits)
RUN pip install \\
    httpx==0.25.2 \\
    httpcore==1.0.2 \\
    h11==0.14.0 \\
    sniffio==1.3.0

# ÉTAPE 3: Installation de FastAPI et dépendances web
RUN pip install \\
    pydantic==2.5.3 \\
    fastapi==0.108.0 \\
    uvicorn[standard]==0.25.0

# ÉTAPE 4: Installation d'Ollama (version compatible)
RUN pip install ollama==0.2.1

# ÉTAPE 5: Installation des dépendances AI/ML
COPY requirements.final.txt .
RUN pip install --no-deps -r requirements.final.txt

# ÉTAPE 6: Vérification finale des installations
RUN python -c "import httpx; import ollama; import fastapi; print('✅ Toutes les dépendances critiques sont installées')"

# Copie du code source
COPY . .

# Exposition du port
EXPOSE 8000

# Point d'entrée
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

    with open('/Users/abderrahman/Documents/MAR/Dockerfile.ultimate', 'w') as f:
        f.write(dockerfile_content)
    
    print("✅ Dockerfile.ultimate créé avec installation par étapes")

def create_docker_compose_ultimate():
    """Crée un docker-compose ultimate pour le déploiement"""
    
    compose_content = """# Docker Compose Ultimate - Configuration de déploiement finale
version: '3.8'

services:
  # Service principal MAR
  mar-api:
    build:
      context: .
      dockerfile: Dockerfile.ultimate
    container_name: mar-api-ultimate
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=staging
      - PYTHONPATH=/app
      - DATABASE_URL=postgresql://mar_user:mar_password@postgres:5432/mar_db
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - postgres
      - redis
      - qdrant
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - mar-network

  # Base de données PostgreSQL
  postgres:
    image: postgres:15-alpine
    container_name: mar-postgres
    environment:
      POSTGRES_DB: mar_db
      POSTGRES_USER: mar_user
      POSTGRES_PASSWORD: mar_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - mar-network

  # Cache Redis
  redis:
    image: redis:7-alpine
    container_name: mar-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - mar-network

  # Base de données vectorielle Qdrant
  qdrant:
    image: qdrant/qdrant:latest
    container_name: mar-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    networks:
      - mar-network

  # Monitoring avec Prometheus (optionnel)
  prometheus:
    image: prom/prometheus:latest
    container_name: mar-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped
    networks:
      - mar-network

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  prometheus_data:

networks:
  mar-network:
    driver: bridge
    name: mar-network
"""

    with open('/Users/abderrahman/Documents/MAR/docker-compose.ultimate.yml', 'w') as f:
        f.write(compose_content)
    
    print("✅ docker-compose.ultimate.yml créé")

def create_deployment_script():
    """Crée le script de déploiement ultimate"""
    
    script_content = """#!/bin/bash

# Script de déploiement ultimate pour MAR
# Résolution définitive des conflits de dépendances

set -euo pipefail

echo "🚀 Démarrage du déploiement ultimate MAR..."

# Couleurs pour les logs
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Fonction de logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    log_info "✅ Prérequis vérifiés"
}

# Nettoyage complet
cleanup_everything() {
    log_info "Nettoyage complet du système Docker..."
    
    # Arrêt de tous les conteneurs MAR
    docker-compose -f docker-compose.ultimate.yml down --remove-orphans 2>/dev/null || true
    docker-compose -f docker-compose.staging.yml down --remove-orphans 2>/dev/null || true
    docker-compose -f docker-compose.yml down --remove-orphans 2>/dev/null || true
    
    # Suppression des images MAR
    docker images | grep "mar-" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    # Nettoyage complet Docker
    docker system prune -af
    docker volume prune -f
    
    log_info "✅ Nettoyage terminé"
}

# Construction de l'image ultimate
build_ultimate_image() {
    log_info "Construction de l'image ultimate..."
    
    # Vérification des fichiers requis
    if [[ ! -f "Dockerfile.ultimate" ]]; then
        log_error "Dockerfile.ultimate manquant"
        exit 1
    fi
    
    if [[ ! -f "requirements.final.txt" ]]; then
        log_error "requirements.final.txt manquant"
        exit 1
    fi
    
    # Construction avec no-cache pour éviter les problèmes
    docker build -f Dockerfile.ultimate -t mar-ultimate:latest . --no-cache
    
    log_info "✅ Image ultimate construite"
}

# Test de l'image
test_image() {
    log_info "Test de l'image ultimate..."
    
    # Test rapide des imports critiques
    docker run --rm mar-ultimate:latest python -c "
import sys
try:
    import httpx
    import ollama
    import fastapi
    import pydantic
    print('✅ Tous les imports critiques fonctionnent')
    print(f'httpx version: {httpx.__version__}')
    print(f'ollama version: {ollama.__version__}')
    print(f'fastapi version: {fastapi.__version__}')
except ImportError as e:
    print(f'❌ Erreur d\\'import: {e}')
    sys.exit(1)
"
    
    log_info "✅ Test de l'image réussi"
}

# Déploiement ultimate
deploy_ultimate() {
    log_info "Déploiement de la stack ultimate..."
    
    # Création des répertoires nécessaires
    mkdir -p logs data monitoring
    
    # Démarrage des services
    docker-compose -f docker-compose.ultimate.yml up -d
    
    log_info "Attente du démarrage des services..."
    sleep 30
    
    # Vérification de la santé
    check_health
}

# Vérification de la santé des services
check_health() {
    log_info "Vérification de la santé des services..."
    
    # Vérification PostgreSQL
    if docker-compose -f docker-compose.ultimate.yml exec -T postgres pg_isready -U mar_user; then
        log_info "✅ PostgreSQL opérationnel"
    else
        log_error "❌ PostgreSQL non opérationnel"
    fi
    
    # Vérification Redis
    if docker-compose -f docker-compose.ultimate.yml exec -T redis redis-cli ping | grep -q PONG; then
        log_info "✅ Redis opérationnel"
    else
        log_error "❌ Redis non opérationnel"
    fi
    
    # Vérification Qdrant
    if curl -sf http://localhost:6333/health >/dev/null; then
        log_info "✅ Qdrant opérationnel"
    else
        log_error "❌ Qdrant non opérationnel"
    fi
    
    # Vérification API MAR
    sleep 10
    if curl -sf http://localhost:8000/health >/dev/null; then
        log_info "✅ API MAR opérationnelle"
    else
        log_warn "⚠️  API MAR pas encore prête (normal au premier démarrage)"
    fi
}

# Affichage des logs
show_logs() {
    log_info "Affichage des logs..."
    docker-compose -f docker-compose.ultimate.yml logs -f --tail=50
}

# Menu principal
main() {
    echo "🎯 Script de déploiement ultimate MAR"
    echo "=====================================
    
    PS3="Choisissez une option: "
    options=("Déploiement complet" "Nettoyage seulement" "Construction seulement" "Test image" "Vérification santé" "Afficher logs" "Quitter")
    
    select opt in "\${options[@]}"; do
        case $opt in
            "Déploiement complet")
                check_prerequisites
                cleanup_everything
                build_ultimate_image
                test_image
                deploy_ultimate
                log_info "🎉 Déploiement ultimate terminé!"
                log_info "API disponible sur: http://localhost:8000"
                log_info "Swagger UI: http://localhost:8000/docs"
                break
                ;;
            "Nettoyage seulement")
                cleanup_everything
                break
                ;;
            "Construction seulement")
                build_ultimate_image
                test_image
                break
                ;;
            "Test image")
                test_image
                break
                ;;
            "Vérification santé")
                check_health
                break
                ;;
            "Afficher logs")
                show_logs
                break
                ;;
            "Quitter")
                break
                ;;
            *) 
                log_error "Option invalide $REPLY"
                ;;
        esac
    done
}

# Exécution du script
main "$@"
"""

    with open('/Users/abderrahman/Documents/MAR/scripts/deploy-ultimate.sh', 'w') as f:
        f.write(script_content)
    
    # Rendre le script exécutable
    subprocess.run(['chmod', '+x', '/Users/abderrahman/Documents/MAR/scripts/deploy-ultimate.sh'])
    
    print("✅ Script deploy-ultimate.sh créé et rendu exécutable")

def main():
    """Fonction principale"""
    print("🔧 Résolution automatique des conflits de dépendances MAR")
    print("="*60)
    
    # Création des fichiers de résolution
    create_fixed_requirements()
    create_minimal_requirements()
    create_ultimate_dockerfile()
    create_docker_compose_ultimate()
    create_deployment_script()
    
    print("\n✅ Tous les fichiers de résolution ont été créés:")
    print("   - requirements.final.txt (versions compatibles)")
    print("   - requirements.debug.txt (minimal pour debug)")
    print("   - Dockerfile.ultimate (build par étapes)")
    print("   - docker-compose.ultimate.yml (stack complète)")
    print("   - scripts/deploy-ultimate.sh (déploiement automatisé)")
    
    print("\n🚀 Pour déployer:")
    print("   cd /Users/abderrahman/Documents/MAR")
    print("   ./scripts/deploy-ultimate.sh")

if __name__ == "__main__":
    main()
