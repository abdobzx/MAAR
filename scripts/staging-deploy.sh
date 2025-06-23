#!/bin/bash

# Script de déploiement staging avec résolution des conflits de dépendances
# Usage: ./scripts/staging-deploy.sh

set -euo pipefail

# Configuration
COMPOSE_PROJECT_NAME="mar-staging"
ENV_FILE=".env.staging"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.staging.yml"

# Couleurs pour l'output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé ou n'est pas dans le PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose n'est pas installé ou n'est pas dans le PATH"
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Fichier d'environnement $ENV_FILE introuvable"
        exit 1
    fi
    
    if [ ! -f "requirements.staging.txt" ]; then
        log_error "Fichier requirements.staging.txt introuvable"
        exit 1
    fi
    
    log_success "Tous les prérequis sont satisfaits"
}

# Nettoyer l'environnement Docker
clean_docker_environment() {
    log_info "Nettoyage de l'environnement Docker..."
    
    # Arrêter et supprimer les conteneurs existants
    docker-compose $COMPOSE_FILES --env-file $ENV_FILE down --remove-orphans || true
    
    # Supprimer les images liées au projet
    log_info "Suppression des images Docker existantes..."
    docker images | grep "$COMPOSE_PROJECT_NAME" | awk '{print $3}' | xargs -r docker rmi -f || true
    
    # Nettoyer le cache de build Docker
    log_info "Nettoyage du cache Docker..."
    docker builder prune -f || true
    
    # Nettoyer les volumes orphelins
    log_info "Nettoyage des volumes orphelins..."
    docker volume prune -f || true
    
    log_success "Environnement Docker nettoyé"
}

# Valider les fichiers de requirements
validate_requirements() {
    log_info "Validation des fichiers de requirements..."
    
    # Vérifier que httpx et ollama ont les bonnes versions
    if grep -q "httpx==0.26.0" requirements*.txt; then
        log_error "Version incompatible de httpx trouvée dans les fichiers requirements"
        exit 1
    fi
    
    if grep -q "ollama==0.1.7" requirements*.txt; then
        log_error "Version incompatible d'ollama trouvée dans les fichiers requirements"
        exit 1
    fi
    
    log_success "Fichiers de requirements validés"
}

# Construire les images Docker
build_images() {
    log_info "Construction des images Docker..."
    
    # Utiliser le Dockerfile.staging pour éviter tout conflit
    export DOCKERFILE_PATH="Dockerfile.staging"
    
    docker-compose $COMPOSE_FILES --env-file $ENV_FILE build --no-cache --pull
    
    log_success "Images Docker construites avec succès"
}

# Démarrer les services
start_services() {
    log_info "Démarrage des services..."
    
    # Démarrer les services de base d'abord
    log_info "Démarrage des services d'infrastructure..."
    docker-compose $COMPOSE_FILES --env-file $ENV_FILE up -d postgres-staging redis-staging
    
    # Attendre que les services de base soient prêts
    log_info "Attente de la disponibilité des services de base..."
    sleep 10
    
    # Démarrer les services applicatifs
    log_info "Démarrage des services applicatifs..."
    docker-compose $COMPOSE_FILES --env-file $ENV_FILE up -d
    
    log_success "Tous les services ont été démarrés"
}

# Vérifier la santé des services
health_check() {
    log_info "Vérification de la santé des services..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Tentative $attempt/$max_attempts..."
        
        # Vérifier l'API principale
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "API principale accessible"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "L'API principale n'est pas accessible après $max_attempts tentatives"
            log_info "Affichage des logs pour diagnostic..."
            docker-compose $COMPOSE_FILES --env-file $ENV_FILE logs --tail=50 mar-api-staging
            exit 1
        fi
        
        sleep 10
        ((attempt++))
    done
}

# Afficher le statut final
show_status() {
    log_info "Statut final des services:"
    docker-compose $COMPOSE_FILES --env-file $ENV_FILE ps
    
    log_success "Déploiement staging terminé avec succès!"
    log_info "URLs d'accès:"
    log_info "  - API: http://localhost:8000"
    log_info "  - Documentation: http://localhost:8000/docs"
    log_info "  - Grafana: http://localhost:3000 (admin/admin)"
    log_info "  - Jaeger: http://localhost:16686"
}

# Fonction principale
main() {
    log_info "Début du déploiement staging pour le système MAR"
    
    check_prerequisites
    validate_requirements
    clean_docker_environment
    build_images
    start_services
    health_check
    show_status
    
    log_success "Déploiement staging complété avec succès!"
}

# Gestion des signaux pour un arrêt propre
trap 'log_error "Déploiement interrompu"; exit 1' INT TERM

# Exécuter le script principal si appelé directement
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
