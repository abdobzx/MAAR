#!/bin/bash

# Script de démarrage rapide pour le système RAG Enterprise
# Usage: ./quick-start.sh [environment]

set -euo pipefail

ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Couleurs
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

log_section() {
    echo ""
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===============================================${NC}"
}

check_requirements() {
    log_section "VÉRIFICATION DES PRÉREQUIS"
    
    local missing_tools=()
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    else
        log_info "Docker: ✓ $(docker --version | cut -d' ' -f3)"
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    else
        log_info "Docker Compose: ✓ $(docker-compose --version | cut -d' ' -f3)"
    fi
    
    # Vérifier Python
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    else
        python_version=$(python3 --version | cut -d' ' -f2)
        log_info "Python: ✓ $python_version"
        
        # Vérifier la version Python
        if [[ "$python_version" < "3.11" ]]; then
            log_warn "Python 3.11+ recommandé (version actuelle: $python_version)"
        fi
    fi
    
    # Vérifier pip
    if ! command -v pip3 &> /dev/null; then
        missing_tools+=("pip3")
    else
        log_info "Pip: ✓ $(pip3 --version | cut -d' ' -f2)"
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "Outils manquants: ${missing_tools[*]}"
        echo ""
        echo "Installation requise:"
        echo "  - Docker: https://docs.docker.com/get-docker/"
        echo "  - Docker Compose: https://docs.docker.com/compose/install/"
        echo "  - Python 3.11+: https://www.python.org/downloads/"
        exit 1
    fi
    
    log_info "Tous les prérequis sont installés ✓"
}

setup_environment() {
    log_section "CONFIGURATION DE L'ENVIRONNEMENT"
    
    cd "$PROJECT_ROOT"
    
    # Créer le fichier .env si nécessaire
    if [ ! -f ".env.$ENVIRONMENT" ]; then
        if [ -f ".env.example" ]; then
            log_info "Création du fichier .env.$ENVIRONMENT depuis .env.example"
            cp .env.example ".env.$ENVIRONMENT"
            
            # Génération de clés aléatoires pour le développement
            if [ "$ENVIRONMENT" = "development" ]; then
                log_info "Génération de clés de développement..."
                
                # Clé secrète
                SECRET_KEY=$(openssl rand -hex 32)
                sed -i.bak "s/your-super-secret-key-change-this-in-production/$SECRET_KEY/" ".env.$ENVIRONMENT"
                
                # Clé de chiffrement
                ENCRYPTION_KEY=$(openssl rand -hex 16)
                sed -i.bak "s/your-encryption-key-32-chars-long/$ENCRYPTION_KEY/" ".env.$ENVIRONMENT"
                
                # Mots de passe par défaut
                sed -i.bak "s/your-postgres-password/postgres_dev_password/" ".env.$ENVIRONMENT"
                sed -i.bak "s/your-redis-password/redis_dev_password/" ".env.$ENVIRONMENT"
                
                rm -f ".env.$ENVIRONMENT.bak"
                
                log_warn "⚠️  Clés générées automatiquement pour le développement"
                log_warn "⚠️  Ne pas utiliser en production !"
            fi
        else
            log_error "Fichier .env.example manquant"
            exit 1
        fi
    else
        log_info "Fichier .env.$ENVIRONMENT existe déjà"
    fi
    
    # Vérifier les clés API
    log_info "Vérification de la configuration..."
    
    if grep -q "sk-your-openai-api-key" ".env.$ENVIRONMENT"; then
        log_warn "⚠️  Clé OpenAI non configurée (optionnel pour le développement)"
    fi
    
    if grep -q "your-cohere-api-key" ".env.$ENVIRONMENT"; then
        log_warn "⚠️  Clé Cohere non configurée (optionnel pour le développement)"
    fi
}

start_services() {
    log_section "DÉMARRAGE DES SERVICES"
    
    cd "$PROJECT_ROOT"
    
    log_info "Arrêt des services existants..."
    docker-compose down -v 2>/dev/null || true
    
    # Sélection du fichier compose selon l'environnement
    local compose_files="-f docker-compose.yml"
    
    case "$ENVIRONMENT" in
        "development")
            compose_files="$compose_files -f docker-compose.dev.yml"
            ;;
        "staging")
            compose_files="$compose_files -f docker-compose.staging.yml"
            ;;
        "production")
            log_error "Utiliser les scripts de déploiement Kubernetes pour la production"
            exit 1
            ;;
    esac
    
    log_info "Démarrage des services ($ENVIRONMENT)..."
    
    # Pull des images
    log_info "Téléchargement des images Docker..."
    docker-compose $compose_files pull
    
    # Démarrage des services de base
    log_info "Démarrage des services de base..."
    docker-compose $compose_files up -d postgres redis qdrant minio
    
    # Attente que les services soient prêts
    log_info "Attente que les services soient prêts..."
    sleep 30
    
    # Vérification de la connectivité
    check_services_health
    
    # Démarrage de l'application
    log_info "Démarrage de l'application RAG..."
    docker-compose $compose_files up -d
    
    # Attente finale
    sleep 20
    
    log_info "Services démarrés avec succès ✓"
}

check_services_health() {
    log_info "Vérification de l'état des services..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local all_healthy=true
        
        # PostgreSQL
        if ! docker-compose exec -T postgres pg_isready -U postgres &>/dev/null; then
            all_healthy=false
        fi
        
        # Redis
        if ! docker-compose exec -T redis redis-cli ping &>/dev/null; then
            all_healthy=false
        fi
        
        # Qdrant
        if ! curl -s http://localhost:6333/health &>/dev/null; then
            all_healthy=false
        fi
        
        # MinIO
        if ! curl -s http://localhost:9000/minio/health/live &>/dev/null; then
            all_healthy=false
        fi
        
        if [ "$all_healthy" = true ]; then
            log_info "Tous les services sont opérationnels ✓"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    log_error "Timeout: certains services ne répondent pas"
    docker-compose ps
    return 1
}

verify_installation() {
    log_section "VÉRIFICATION DE L'INSTALLATION"
    
    log_info "Test de l'API principale..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health &>/dev/null; then
            log_info "API principale: ✓ Opérationnelle"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "API principale: ✗ Non accessible"
            log_error "Logs de l'API:"
            docker-compose logs --tail=20 rag-api
            return 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    # Test de l'endpoint de santé
    log_info "Test des endpoints critiques..."
    
    local health_response=$(curl -s http://localhost:8000/health)
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        log_info "Endpoint /health: ✓"
    else
        log_warn "Endpoint /health: ⚠️ Réponse inattendue"
    fi
    
    log_info "Installation vérifiée avec succès ✓"
}

show_summary() {
    log_section "SYSTÈME RAG ENTERPRISE - PRÊT"
    
    echo ""
    log_info "🎉 Le système RAG Enterprise est opérationnel !"
    echo ""
    echo "📍 URLs d'accès:"
    echo "   • API Documentation: http://localhost:8000/docs"
    echo "   • Interface Swagger: http://localhost:8000/redoc"
    echo "   • Health Check: http://localhost:8000/health"
    echo ""
    echo "🗄️  Interfaces d'administration:"
    echo "   • MinIO Console: http://localhost:9001 (admin/password)"
    echo "   • Qdrant Dashboard: http://localhost:6333/dashboard"
    echo ""
    echo "🔧 Commandes utiles:"
    echo "   • Logs en temps réel: docker-compose logs -f"
    echo "   • Statut des services: docker-compose ps"
    echo "   • Arrêter le système: docker-compose down"
    echo ""
    echo "📚 Documentation:"
    echo "   • Guide utilisateur: docs/user-guide.md"
    echo "   • Documentation API: docs/api.md"
    echo "   • Guide de déploiement: docs/deployment-guide.md"
    echo ""
    
    if [ "$ENVIRONMENT" = "development" ]; then
        log_warn "⚠️  Environnement de développement"
        log_warn "⚠️  Ne pas utiliser en production"
        echo ""
        echo "🚀 Pour la production:"
        echo "   • Voir docs/production-deployment-guide.md"
        echo "   • Utiliser Kubernetes avec ./scripts/deployment/deploy.sh"
    fi
    
    echo ""
    log_info "💡 Pour commencer, visitez: http://localhost:8000/docs"
}

# Fonction d'aide
show_help() {
    echo "Usage: $0 [environment]"
    echo ""
    echo "Démarrage rapide du système RAG Enterprise"
    echo ""
    echo "Environnements:"
    echo "  development    Développement local (défaut)"
    echo "  staging        Environnement de test"
    echo ""
    echo "Options:"
    echo "  -h, --help     Affiche cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0                    # Démarrage en développement"
    echo "  $0 development        # Démarrage en développement"
    echo "  $0 staging            # Démarrage en staging"
}

# Gestion des arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    development|staging|"")
        ENVIRONMENT=${1:-development}
        ;;
    *)
        log_error "Environnement inconnu: $1"
        show_help
        exit 1
        ;;
esac

# Fonction de nettoyage en cas d'interruption
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Démarrage interrompu"
        log_info "Nettoyage en cours..."
        docker-compose down -v 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Exécution principale
main() {
    echo -e "${BLUE}"
    echo "███████╗ █████╗  ██████╗     ███████╗███╗   ██╗████████╗███████╗██████╗ ██████╗ ██████╗ ██╗███████╗███████╗"
    echo "██╔══██╗██╔══██╗██╔════╝     ██╔════╝████╗  ██║╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██║██╔════╝██╔════╝"
    echo "██████╔╝███████║██║  ███╗    █████╗  ██╔██╗ ██║   ██║   █████╗  ██████╔╝██████╔╝██████╔╝██║███████╗█████╗  "
    echo "██╔══██╗██╔══██║██║   ██║    ██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗██╔═══╝ ██╔══██╗██║╚════██║██╔══╝  "
    echo "██║  ██║██║  ██║╚██████╔╝    ███████╗██║ ╚████║   ██║   ███████╗██║  ██║██║     ██║  ██║██║███████║███████╗"
    echo "╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚══════╝"
    echo -e "${NC}"
    echo ""
    log_info "Environnement: $ENVIRONMENT"
    echo ""
    
    check_requirements
    setup_environment
    start_services
    verify_installation
    show_summary
    
    log_info "🎯 Démarrage terminé avec succès !"
}

# Exécution
main "$@"
