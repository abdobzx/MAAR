#!/bin/bash

# Script de déploiement d'urgence - Résolution des conflits de dépendances
# Utilise une approche d'installation par étapes pour éviter tous les conflits

set -euo pipefail

# Configuration
WORK_DIR="$(pwd)"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"

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

# Fonction de nettoyage complet
emergency_cleanup() {
    log_info "🧹 Nettoyage complet de l'environnement Docker..."
    
    # Arrêter tous les conteneurs du projet
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # Supprimer toutes les images liées au projet
    docker images | grep -E "(mar|rag|staging)" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    # Nettoyage complet du système Docker
    docker system prune -af --volumes
    
    log_success "Environnement Docker nettoyé"
}

# Test de construction avec Dockerfile minimal
test_minimal_build() {
    log_info "🔧 Test de construction avec Dockerfile minimal..."
    
    if docker build -f Dockerfile.minimal -t mar-minimal-test . 2>&1 | tee build.log; then
        log_success "✅ Construction réussie avec Dockerfile minimal!"
        return 0
    else
        log_error "❌ Échec de construction avec Dockerfile minimal"
        log_info "Dernières lignes du log de construction:"
        tail -20 build.log
        return 1
    fi
}

# Créer un docker-compose temporaire pour le test
create_temp_compose() {
    log_info "📝 Création d'un docker-compose temporaire..."
    
    cat > docker-compose.temp.yml << 'EOF'
version: '3.8'

services:
  # Base de données PostgreSQL
  postgres:
    image: postgres:15-alpine
    container_name: postgres-temp
    environment:
      POSTGRES_DB: mar_db
      POSTGRES_USER: mar_user
      POSTGRES_PASSWORD: mar_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mar_user -d mar_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis pour le cache
  redis:
    image: redis:7-alpine
    container_name: redis-temp
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant pour les vecteurs
  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: qdrant-temp
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Application principale
  mar_api:
    build:
      context: .
      dockerfile: Dockerfile.minimal
    container_name: mar-api-temp
    environment:
      - ENVIRONMENT=staging
      - DEBUG=false
      - DATABASE_URL=postgresql://mar_user:mar_password@postgres:5432/mar_db
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  qdrant_data:
EOF

    log_success "Docker-compose temporaire créé"
}

# Déploiement d'urgence
emergency_deploy() {
    log_info "🚀 Démarrage du déploiement d'urgence..."
    
    # Construire et démarrer avec le compose temporaire
    docker-compose -f docker-compose.temp.yml up -d --build
    
    log_info "⏳ Attente du démarrage des services (60 secondes)..."
    sleep 60
    
    # Test de santé
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "🔍 Test de santé - Tentative $attempt/$max_attempts..."
        
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "✅ API accessible et fonctionnelle!"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "❌ L'API n'est pas accessible après $max_attempts tentatives"
            log_info "📋 Affichage des logs pour diagnostic..."
            docker-compose -f docker-compose.temp.yml logs --tail=50 mar_api
            return 1
        fi
        
        sleep 10
        ((attempt++))
    done
}

# Validation finale
final_validation() {
    log_info "✅ Validation finale du déploiement..."
    
    # Vérifier les services
    log_info "📊 Statut des services:"
    docker-compose -f docker-compose.temp.yml ps
    
    # Tests de connectivité
    log_info "🌐 Tests de connectivité:"
    
    if curl -f http://localhost:8000/health 2>/dev/null; then
        log_success "✅ Health endpoint accessible"
    else
        log_error "❌ Health endpoint inaccessible"
    fi
    
    if curl -f http://localhost:8000/docs 2>/dev/null; then
        log_success "✅ Documentation accessible"
    else
        log_warning "⚠️ Documentation potentiellement inaccessible"
    fi
    
    # Afficher les URLs d'accès
    echo
    log_success "🎉 Déploiement d'urgence terminé avec succès!"
    log_info "📍 URLs d'accès:"
    log_info "   - API: http://localhost:8000"
    log_info "   - Health: http://localhost:8000/health"
    log_info "   - Documentation: http://localhost:8000/docs"
    log_info "   - PostgreSQL: localhost:5432"
    log_info "   - Redis: localhost:6379"
    log_info "   - Qdrant: http://localhost:6333"
}

# Fonction principale
main() {
    log_info "🚨 DÉPLOIEMENT D'URGENCE - Résolution des conflits de dépendances"
    echo
    
    # Sauvegarde
    if [ -d "docker-compose.yml" ]; then
        mkdir -p "$BACKUP_DIR"
        cp docker-compose*.yml "$BACKUP_DIR/" 2>/dev/null || true
        log_info "💾 Sauvegarde créée dans $BACKUP_DIR"
    fi
    
    emergency_cleanup
    echo
    
    if test_minimal_build; then
        echo
        create_temp_compose
        echo
        if emergency_deploy; then
            echo
            final_validation
        else
            log_error "🚫 Échec du déploiement d'urgence"
            exit 1
        fi
    else
        log_error "🚫 Impossible de construire l'image Docker"
        exit 1
    fi
}

# Gestion des signaux
trap 'log_error "Déploiement interrompu"; exit 1' INT TERM

# Exécuter si appelé directement
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
