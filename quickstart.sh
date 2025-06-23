#!/bin/bash

# Script de démarrage rapide pour la plateforme MAR
# Usage: ./quickstart.sh

set -e  # Arrêter le script en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé. Veuillez installer Docker Desktop."
        exit 1
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose n'est pas installé."
        exit 1
    fi
    
    # Vérifier que Docker est démarré
    if ! docker info &> /dev/null; then
        log_error "Docker n'est pas démarré. Veuillez démarrer Docker Desktop."
        exit 1
    fi
    
    log_success "Prérequis vérifiés"
}

# Configuration initiale
setup_environment() {
    log_info "Configuration de l'environnement..."
    
    # Créer le fichier .env s'il n'existe pas
    if [ ! -f .env ]; then
        log_info "Création du fichier .env..."
        cp .env.example .env
        log_success "Fichier .env créé"
    else
        log_warning "Le fichier .env existe déjà"
    fi
    
    # Créer les répertoires nécessaires
    log_info "Création des répertoires..."
    mkdir -p data/{vector_store,uploads,backups}
    mkdir -p logs
    log_success "Répertoires créés"
}

# Vérifier si Ollama est disponible
check_ollama() {
    log_info "Vérification d'Ollama..."
    
    # Tenter de se connecter à Ollama
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_success "Ollama est accessible sur http://localhost:11434"
        
        # Vérifier si des modèles sont installés
        models=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | wc -l)
        if [ "$models" -gt 0 ]; then
            log_success "Modèles Ollama disponibles"
        else
            log_warning "Aucun modèle Ollama installé"
            log_info "Pour installer un modèle: ollama pull llama2"
        fi
    else
        log_warning "Ollama n'est pas accessible sur http://localhost:11434"
        log_info "La plateforme fonctionnera en mode simulation"
        log_info "Pour installer Ollama: curl -fsSL https://ollama.ai/install.sh | sh"
    fi
}

# Démarrage des services
start_services() {
    log_info "Démarrage des services Docker..."
    
    # Arrêter les services existants si ils tournent
    docker-compose down 2>/dev/null || true
    
    # Démarrer les services
    if docker-compose up -d; then
        log_success "Services démarrés avec succès"
    else
        log_error "Erreur lors du démarrage des services"
        exit 1
    fi
}

# Attendre que les services soient prêts
wait_for_services() {
    log_info "Attente que les services soient prêts..."
    
    # Attendre l'API
    log_info "Vérification de l'API..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            log_success "API prête sur http://localhost:8000"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "L'API n'a pas démarré dans les temps"
            exit 1
        fi
        
        sleep 2
    done
    
    # Attendre l'interface
    log_info "Vérification de l'interface Streamlit..."
    for i in {1..30}; do
        if curl -s http://localhost:8501/healthz >/dev/null 2>&1; then
            log_success "Interface prête sur http://localhost:8501"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_warning "L'interface Streamlit met du temps à démarrer"
            break
        fi
        
        sleep 2
    done
}

# Test rapide de la plateforme
test_platform() {
    log_info "Test rapide de la plateforme..."
    
    # Test de l'endpoint health
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        log_success "Endpoint health fonctionnel"
    else
        log_warning "Endpoint health ne répond pas correctement"
    fi
    
    # Test de la documentation API
    if curl -s http://localhost:8000/docs >/dev/null 2>&1; then
        log_success "Documentation API accessible"
    else
        log_warning "Documentation API non accessible"
    fi
}

# Affichage des informations finales
show_final_info() {
    echo ""
    echo -e "${GREEN}🎉 Plateforme MAR démarrée avec succès !${NC}"
    echo ""
    echo -e "${BLUE}📱 Accès aux services:${NC}"
    echo -e "  • Interface utilisateur: ${YELLOW}http://localhost:8501${NC}"
    echo -e "  • API Documentation:     ${YELLOW}http://localhost:8000/docs${NC}"
    echo -e "  • API Health Check:      ${YELLOW}http://localhost:8000/health${NC}"
    echo -e "  • Monitoring Grafana:    ${YELLOW}http://localhost:3000${NC} (admin/admin)"
    echo -e "  • Prometheus:            ${YELLOW}http://localhost:9090${NC}"
    echo ""
    echo -e "${BLUE}🛠️  Commandes utiles:${NC}"
    echo -e "  • Voir les logs:         ${YELLOW}make logs${NC}"
    echo -e "  • Arrêter la plateforme: ${YELLOW}make down${NC}"
    echo -e "  • Redémarrer:            ${YELLOW}make restart${NC}"
    echo -e "  • Tests end-to-end:      ${YELLOW}python scripts/test_end_to_end.py${NC}"
    echo ""
    echo -e "${BLUE}📚 Premiers pas:${NC}"
    echo -e "  1. Ouvrez l'interface: http://localhost:8501"
    echo -e "  2. Créez un compte utilisateur"
    echo -e "  3. Ingérez vos premiers documents"
    echo -e "  4. Testez le chat RAG"
    echo ""
    echo -e "${GREEN}Bonne utilisation de la plateforme MAR ! 🚀${NC}"
}

# Gestion des erreurs
cleanup_on_error() {
    log_error "Une erreur s'est produite. Nettoyage..."
    docker-compose down 2>/dev/null || true
    exit 1
}

# Main function
main() {
    echo -e "${BLUE}🚀 Démarrage rapide de la plateforme MAR${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
    
    # Piège pour nettoyer en cas d'erreur
    trap cleanup_on_error ERR
    
    # Étapes de configuration
    check_prerequisites
    setup_environment
    check_ollama
    start_services
    wait_for_services
    test_platform
    show_final_info
}

# Vérifier si le script est exécuté directement
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
