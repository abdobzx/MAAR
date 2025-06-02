#!/bin/bash

# Script de validation finale avant déploiement
# Vérifie la cohérence des fichiers et configurations

set -euo pipefail

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

VALIDATION_PASSED=true

# Fonction pour marquer un échec
mark_failure() {
    VALIDATION_PASSED=false
    log_error "$1"
}

# Validation des fichiers requirements
validate_requirements() {
    log_info "Validation des fichiers requirements..."
    
    local files=("requirements.txt" "requirements.staging.txt" "requirements-minimal.txt")
    
    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            mark_failure "Fichier $file manquant"
            continue
        fi
        
        log_info "Validation de $file..."
        
        # Vérifier les versions problématiques
        if grep -q "httpx==0.26.0" "$file"; then
            mark_failure "Version incompatible httpx==0.26.0 trouvée dans $file"
        fi
        
        if grep -q "ollama==0.1.7" "$file"; then
            mark_failure "Version incompatible ollama==0.1.7 trouvée dans $file"
        fi
        
        # Vérifier les versions correctes
        if grep -q "httpx>=0.25.2,<0.26.0\|httpx>=0.25.0" "$file"; then
            log_success "Version httpx compatible trouvée dans $file"
        else
            log_warning "Version httpx non trouvée ou non standard dans $file"
        fi
        
        if grep -q "ollama>=0.2.0" "$file"; then
            log_success "Version ollama compatible trouvée dans $file"
        else
            log_warning "Version ollama non trouvée ou non standard dans $file"
        fi
    done
}

# Validation des Dockerfiles
validate_dockerfiles() {
    log_info "Validation des Dockerfiles..."
    
    if [ ! -f "Dockerfile" ]; then
        mark_failure "Dockerfile principal manquant"
    else
        if grep -q "requirements.txt" Dockerfile; then
            log_success "Dockerfile utilise requirements.txt"
        else
            log_warning "Dockerfile ne semble pas utiliser requirements.txt"
        fi
    fi
    
    if [ ! -f "Dockerfile.staging" ]; then
        mark_failure "Dockerfile.staging manquant"
    else
        if grep -q "requirements.staging.txt" Dockerfile.staging; then
            log_success "Dockerfile.staging utilise requirements.staging.txt"
        else
            log_warning "Dockerfile.staging ne semble pas utiliser requirements.staging.txt"
        fi
    fi
}

# Validation des fichiers Docker Compose
validate_docker_compose() {
    log_info "Validation des fichiers Docker Compose..."
    
    if [ ! -f "docker-compose.yml" ]; then
        mark_failure "docker-compose.yml manquant"
    else
        # Vérifier les valeurs booléennes corrigées
        if grep -q 'KC_HOSTNAME_STRICT: "false"' docker-compose.yml; then
            log_success "Valeurs booléennes Keycloak correctement formatées"
        else
            log_warning "Valeurs booléennes Keycloak potentiellement incorrectes"
        fi
    fi
    
    if [ ! -f "docker-compose.staging.yml" ]; then
        mark_failure "docker-compose.staging.yml manquant"
    else
        if grep -q "Dockerfile.staging" docker-compose.staging.yml; then
            log_success "docker-compose.staging.yml utilise Dockerfile.staging"
        else
            mark_failure "docker-compose.staging.yml n'utilise pas Dockerfile.staging"
        fi
    fi
}

# Validation du fichier d'environnement
validate_env_files() {
    log_info "Validation des fichiers d'environnement..."
    
    if [ ! -f ".env.staging" ]; then
        mark_failure "Fichier .env.staging manquant"
    else
        log_success "Fichier .env.staging présent"
        
        # Vérifier les variables critiques
        local required_vars=("POSTGRES_DB" "REDIS_URL" "SOTHEMAAI_API_KEY" "QDRANT_URL")
        
        for var in "${required_vars[@]}"; do
            if grep -q "^$var=" .env.staging; then
                log_success "Variable $var définie dans .env.staging"
            else
                log_warning "Variable $var non trouvée dans .env.staging"
            fi
        done
    fi
}

# Validation de la structure des répertoires
validate_directory_structure() {
    log_info "Validation de la structure des répertoires..."
    
    local required_dirs=("agents" "api" "core" "scripts" "tests")
    
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_success "Répertoire $dir présent"
        else
            mark_failure "Répertoire $dir manquant"
        fi
    done
}

# Validation des scripts de déploiement
validate_deployment_scripts() {
    log_info "Validation des scripts de déploiement..."
    
    if [ -f "scripts/staging-deploy.sh" ]; then
        log_success "Script staging-deploy.sh présent"
        if [ -x "scripts/staging-deploy.sh" ]; then
            log_success "Script staging-deploy.sh exécutable"
        else
            log_warning "Script staging-deploy.sh non exécutable"
            chmod +x scripts/staging-deploy.sh
            log_success "Permissions d'exécution ajoutées"
        fi
    else
        log_warning "Script staging-deploy.sh manquant"
    fi
}

# Vérification des dépendances système
check_system_dependencies() {
    log_info "Vérification des dépendances système..."
    
    local deps=("docker" "docker-compose" "curl")
    
    for dep in "${deps[@]}"; do
        if command -v "$dep" &> /dev/null; then
            log_success "$dep installé"
        else
            mark_failure "$dep non installé ou non dans le PATH"
        fi
    done
}

# Résumé de validation
validation_summary() {
    echo
    log_info "=== RÉSUMÉ DE VALIDATION ==="
    
    if [ "$VALIDATION_PASSED" = true ]; then
        log_success "✅ TOUTES LES VALIDATIONS PASSÉES"
        log_info "Le système est prêt pour le déploiement staging"
        echo
        log_info "Pour déployer en staging, exécutez:"
        log_info "  cd /votre/serveur/MAR"
        log_info "  ./scripts/staging-deploy.sh"
    else
        log_error "❌ CERTAINES VALIDATIONS ONT ÉCHOUÉ"
        log_error "Veuillez corriger les erreurs avant le déploiement"
        exit 1
    fi
}

# Fonction principale
main() {
    log_info "Début de la validation finale du système MAR"
    echo
    
    validate_requirements
    echo
    validate_dockerfiles
    echo
    validate_docker_compose
    echo
    validate_env_files
    echo
    validate_directory_structure
    echo
    validate_deployment_scripts
    echo
    check_system_dependencies
    echo
    validation_summary
}

# Exécuter si appelé directement
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
