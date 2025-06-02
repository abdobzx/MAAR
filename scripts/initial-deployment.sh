#!/bin/bash

# Script de déploiement initial pour le système RAG Enterprise
# Usage: ./initial-deployment.sh [environment]

set -euo pipefail

ENVIRONMENT=${1:-staging}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

validate_prerequisites() {
    log_step "Validation des prérequis..."
    
    # Vérifier les outils requis
    local required_tools=("docker" "kubectl" "helm")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Outil requis manquant: $tool"
            echo "Veuillez installer $tool avant de continuer"
            exit 1
        fi
    done
    
    # Vérifier Docker
    if ! docker info &> /dev/null; then
        log_error "Docker n'est pas en cours d'exécution"
        exit 1
    fi
    
    # Vérifier Kubernetes (si pas en mode local)
    if [ "$ENVIRONMENT" != "local" ]; then
        if ! kubectl cluster-info &> /dev/null; then
            log_error "Impossible de se connecter au cluster Kubernetes"
            exit 1
        fi
    fi
    
    log_info "Prérequis validés"
}

setup_local_development() {
    log_step "Configuration de l'environnement de développement local..."
    
    cd "$PROJECT_ROOT"
    
    # Créer le fichier .env.development s'il n'existe pas
    if [ ! -f ".env.development" ]; then
        log_info "Création du fichier .env.development..."
        cp .env.example .env.development 2>/dev/null || {
            log_warn "Fichier .env.example non trouvé, création manuelle..."
            cat > .env.development << EOF
# Environnement de développement
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://rag_user:rag_password@localhost:5432/rag_database
REDIS_URL=redis://:redis_password@localhost:6379/0
QDRANT_URL=http://localhost:6333
SOTHEMAAI_API_KEY=your-api-key-here
SECRET_KEY=dev-secret-key-change-in-production
LOG_LEVEL=DEBUG
EOF
        }
    fi
    
    # Arrêter les services existants
    log_info "Arrêt des services existants..."
    docker-compose down -v 2>/dev/null || true
    
    # Construire et démarrer les services
    log_info "Construction et démarrage des services..."
    docker-compose up -d --build
    
    # Attendre que les services soient prêts
    log_info "Attente de la disponibilité des services..."
    sleep 30
    
    # Vérifier la santé des services
    check_service_health "http://localhost:8000/health" "API RAG"
    check_service_health "http://localhost:5432" "PostgreSQL" "nc"
    check_service_health "http://localhost:6379" "Redis" "nc"
    check_service_health "http://localhost:6333/health" "Qdrant"
    
    log_info "Environnement de développement configuré!"
    echo
    echo "🚀 Services disponibles:"
    echo "  - API RAG: http://localhost:8000"
    echo "  - Documentation: http://localhost:8000/docs"
    echo "  - Grafana: http://localhost:3000 (admin/grafana_password)"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - MinIO: http://localhost:9001 (minio_user/minio_password)"
}

check_service_health() {
    local url=$1
    local service_name=$2
    local method=${3:-curl}
    local max_attempts=30
    local attempt=1
    
    log_info "Vérification de $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if [ "$method" = "curl" ]; then
            if curl -f -s "$url" > /dev/null 2>&1; then
                log_info "$service_name est prêt"
                return 0
            fi
        elif [ "$method" = "nc" ]; then
            local host=$(echo "$url" | sed 's/http:\/\///' | cut -d':' -f1)
            local port=$(echo "$url" | sed 's/http:\/\///' | cut -d':' -f2)
            if nc -z "$host" "$port" 2>/dev/null; then
                log_info "$service_name est prêt"
                return 0
            fi
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "$service_name n'est pas disponible après $max_attempts tentatives"
            return 1
        fi
        
        sleep 2
        ((attempt++))
    done
}

setup_staging_environment() {
    log_step "Configuration de l'environnement de staging..."
    
    local namespace="rag-staging"
    
    # Créer le namespace
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
    kubectl label namespace "$namespace" environment=staging --overwrite
    
    # Appliquer les secrets
    log_info "Configuration des secrets..."
    if [ -f "$PROJECT_ROOT/.env.staging" ]; then
        kubectl create secret generic rag-secrets \
            --from-env-file="$PROJECT_ROOT/.env.staging" \
            --namespace="$namespace" \
            --dry-run=client -o yaml | kubectl apply -f -
    else
        log_warn "Fichier .env.staging non trouvé, utilisation des valeurs par défaut"
        kubectl create secret generic rag-secrets \
            --from-literal=DATABASE_URL="postgresql+asyncpg://rag_user:rag_password@postgres:5432/rag_database" \
            --from-literal=REDIS_URL="redis://:redis_password@redis:6379/0" \
            --from-literal=SECRET_KEY="staging-secret-key" \
            --namespace="$namespace" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # Déployer avec Helm
    log_info "Déploiement avec Helm..."
    helm upgrade --install rag-system "$PROJECT_ROOT/infrastructure/helm" \
        --namespace="$namespace" \
        --set environment=staging \
        --set image.tag=latest \
        --wait \
        --timeout=10m
    
    # Vérifier le déploiement
    kubectl get pods -n "$namespace"
    kubectl get services -n "$namespace"
    
    log_info "Environnement de staging configuré!"
}

setup_production_environment() {
    log_step "Configuration de l'environnement de production..."
    
    log_warn "⚠️  ATTENTION: Déploiement en production!"
    read -p "Êtes-vous sûr de vouloir continuer? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Déploiement annulé"
        exit 0
    fi
    
    local namespace="rag-production"
    
    # Vérifications de sécurité
    if [ ! -f "$PROJECT_ROOT/.env.production" ]; then
        log_error "Fichier .env.production requis pour la production"
        exit 1
    fi
    
    # Créer le namespace avec labels de sécurité
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
    kubectl label namespace "$namespace" environment=production --overwrite
    kubectl label namespace "$namespace" security-level=high --overwrite
    
    # Appliquer les politiques de sécurité
    log_info "Application des politiques de sécurité..."
    if [ -d "$PROJECT_ROOT/infrastructure/security" ]; then
        kubectl apply -f "$PROJECT_ROOT/infrastructure/security/" -n "$namespace"
    fi
    
    # Configuration des secrets sécurisés
    log_info "Configuration des secrets de production..."
    kubectl create secret generic rag-secrets \
        --from-env-file="$PROJECT_ROOT/.env.production" \
        --namespace="$namespace" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Déploiement de production
    log_info "Déploiement de production avec Helm..."
    helm upgrade --install rag-system "$PROJECT_ROOT/infrastructure/helm" \
        --namespace="$namespace" \
        --values="$PROJECT_ROOT/infrastructure/helm/values-production.yaml" \
        --set environment=production \
        --set image.tag=v1.0.0 \
        --wait \
        --timeout=15m \
        --atomic
    
    # Vérifications post-déploiement
    log_info "Vérifications post-déploiement..."
    kubectl get pods -n "$namespace"
    kubectl get services -n "$namespace"
    kubectl get ingress -n "$namespace"
    
    log_info "Environnement de production configuré!"
    log_warn "N'oubliez pas de configurer:"
    echo "  - Certificats SSL/TLS"
    echo "  - DNS pour votre domaine"
    echo "  - Monitoring et alertes"
    echo "  - Sauvegardes automatiques"
}

show_next_steps() {
    echo
    echo "🎯 Prochaines étapes recommandées:"
    echo
    echo "1. **Sécurité:**"
    echo "   - Configurer les certificats SSL/TLS"
    echo "   - Mettre en place RBAC Kubernetes"
    echo "   - Configurer les Network Policies"
    echo
    echo "2. **Monitoring:**"
    echo "   - Déployer Prometheus/Grafana"
    echo "   - Configurer les alertes"
    echo "   - Mettre en place ELK Stack"
    echo
    echo "3. **CI/CD:**"
    echo "   - Configurer les pipelines GitHub Actions"
    echo "   - Mettre en place les tests automatisés"
    echo "   - Configurer les déploiements automatiques"
    echo
    echo "4. **Backup & Recovery:**"
    echo "   - Configurer les sauvegardes de base de données"
    echo "   - Tester les procédures de récupération"
    echo "   - Documenter les runbooks"
    echo
}

main() {
    echo "🚀 Configuration initiale du système RAG Enterprise"
    echo "=================================================="
    echo "Environnement: $ENVIRONMENT"
    echo
    
    validate_prerequisites
    
    case "$ENVIRONMENT" in
        "local"|"development")
            setup_local_development
            ;;
        "staging")
            setup_staging_environment
            ;;
        "production")
            setup_production_environment
            ;;
        *)
            log_error "Environnement non supporté: $ENVIRONMENT"
            echo "Environnements supportés: local, staging, production"
            exit 1
            ;;
    esac
    
    show_next_steps
}

# Exécution du script
main "$@"
