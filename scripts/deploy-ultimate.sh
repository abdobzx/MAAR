#!/bin/bash

# Script de déploiement ultimate pour MAR
# Résolution définitive des conflits de dépendances

set -euo pipefail

echo "🚀 Démarrage du déploiement ultimate MAR..."

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
    echo "====================================="
    
    PS3="Choisissez une option: "
    options=("Déploiement complet" "Nettoyage seulement" "Construction seulement" "Test image" "Vérification santé" "Afficher logs" "Quitter")
    
    select opt in "${options[@]}"; do
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
