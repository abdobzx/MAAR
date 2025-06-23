#!/bin/bash

# =============================================================================
# DÉPLOIEMENT MANUEL OPTIMISÉ - SYSTÈME MAR
# Version corrigée avec résolution des conflits de dépendances
# =============================================================================

set -e

echo "🚀 DÉPLOIEMENT MANUEL SYSTÈME MAR - VERSION CORRIGÉE"
echo "===================================================="
echo ""

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}[ÉTAPE] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[SUCCÈS] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[ATTENTION] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERREUR] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Vérification des prérequis
print_step "Vérification des prérequis..."

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker n'est pas installé"
    exit 1
fi

# Vérifier Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose n'est pas installé"
    exit 1
fi

print_success "Docker et Docker Compose sont disponibles"

# Vérification des fichiers requis
print_step "Vérification des fichiers requis..."

required_files=(
    "requirements.final.txt"
    "Dockerfile.ultimate"
    "docker-compose.ultimate.yml"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        print_success "Fichier trouvé: $file"
    else
        print_error "Fichier manquant: $file"
        print_info "Assurez-vous d'être dans le bon répertoire et d'avoir tous les fichiers"
        exit 1
    fi
done

echo ""

# Affichage des corrections appliquées
print_step "Résumé des corrections appliquées..."
echo ""
print_info "Corrections de dépendances:"
echo "  ✓ httpx==0.25.2 (maintenu - version stable)"
echo "  ✓ ollama (suppression contrainte version)"
echo "  ✓ langchain==0.1.20 (downgrade pour compatibilité CrewAI)"
echo "  ✓ langchain-community==0.0.38 (downgrade pour compatibilité)"
echo "  ✓ cryptography==42.0.8 (mise à jour vers version disponible)"
echo ""

# Demande de confirmation
read -p "Voulez-vous continuer avec le déploiement? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Déploiement annulé par l'utilisateur"
    exit 0
fi

echo ""

# Étape 1: Nettoyage
print_step "1/9 - Nettoyage de l'environnement Docker..."

# Arrêter les conteneurs existants
if docker-compose -f docker-compose.ultimate.yml ps -q | grep -q .; then
    print_info "Arrêt des conteneurs existants..."
    docker-compose -f docker-compose.ultimate.yml down
    print_success "Conteneurs arrêtés"
else
    print_info "Aucun conteneur en cours d'exécution"
fi

# Nettoyage des images orphelines (optionnel)
print_info "Nettoyage des ressources Docker inutilisées..."
docker system prune -f
print_success "Nettoyage terminé"

echo ""

# Étape 2: Validation de requirements.final.txt
print_step "2/9 - Validation des dépendances..."

if grep -q "httpx==0.25.2" requirements.final.txt && \
   grep -q "langchain==0.1.20" requirements.final.txt && \
   grep -q "cryptography==42.0.8" requirements.final.txt; then
    print_success "Toutes les corrections sont présentes dans requirements.final.txt"
else
    print_error "Les corrections ne sont pas appliquées dans requirements.final.txt"
    print_info "Vérifiez que le fichier contient les bonnes versions"
    exit 1
fi

echo ""

# Étape 3: Construction de l'image
print_step "3/9 - Construction de l'image Docker..."

print_info "Début de la construction (cela peut prendre plusieurs minutes)..."
print_info "Construction avec Dockerfile.ultimate..."

if docker build -f Dockerfile.ultimate -t mar-system:latest .; then
    print_success "Image construite avec succès!"
else
    print_error "Échec de la construction de l'image"
    print_info "Vérifiez les logs ci-dessus pour identifier le problème"
    exit 1
fi

echo ""

# Étape 4: Test rapide de l'image
print_step "4/9 - Test rapide de l'image construite..."

print_info "Test des imports critiques..."
if docker run --rm mar-system:latest python -c "
import fastapi
import crewai  
import langchain
import httpx
import ollama
import cryptography
print('✅ Tous les imports critiques réussis')
"; then
    print_success "Test des imports réussi!"
else
    print_error "Échec du test des imports"
    exit 1
fi

echo ""

# Étape 5: Création des volumes
print_step "5/9 - Création des volumes Docker..."

volumes=(
    "mar_postgres_data"
    "mar_redis_data" 
    "mar_qdrant_data"
    "mar_minio_data"
    "mar_prometheus_data"
)

for volume in "${volumes[@]}"; do
    if docker volume ls -q | grep -q "^${volume}$"; then
        print_info "Volume existant: $volume"
    else
        docker volume create $volume
        print_success "Volume créé: $volume"
    fi
done

echo ""

# Étape 6: Démarrage des services de base
print_step "6/9 - Démarrage des services de base..."

print_info "Démarrage de PostgreSQL, Redis, Qdrant..."
docker-compose -f docker-compose.ultimate.yml up -d postgres redis qdrant

print_info "Attente de l'initialisation des services de base (30 secondes)..."
sleep 30

# Vérification des services de base
if docker-compose -f docker-compose.ultimate.yml ps postgres | grep -q "Up"; then
    print_success "PostgreSQL démarré"
else
    print_error "Problème avec PostgreSQL"
    docker-compose -f docker-compose.ultimate.yml logs postgres
    exit 1
fi

echo ""

# Étape 7: Démarrage des services de monitoring
print_step "7/9 - Démarrage des services de monitoring..."

print_info "Démarrage de Prometheus et MinIO..."
docker-compose -f docker-compose.ultimate.yml up -d prometheus minio

print_info "Attente de l'initialisation (15 secondes)..."
sleep 15

echo ""

# Étape 8: Démarrage de l'API principale
print_step "8/9 - Démarrage de l'API MAR..."

print_info "Démarrage du service principal MAR..."
docker-compose -f docker-compose.ultimate.yml up -d mar-api

print_info "Attente du démarrage de l'API (45 secondes)..."
sleep 45

echo ""

# Étape 9: Vérification finale
print_step "9/9 - Vérification finale du déploiement..."

print_info "État des services:"
docker-compose -f docker-compose.ultimate.yml ps

echo ""

# Test de santé de l'API
print_info "Test de l'endpoint de santé..."
if curl -s http://localhost:8000/health | grep -q "status"; then
    print_success "API MAR opérationnelle!"
else
    print_warning "L'API ne répond pas encore ou il y a un problème"
    print_info "Vérification des logs de l'API..."
    docker-compose -f docker-compose.ultimate.yml logs --tail=20 mar-api
fi

echo ""

# Résumé final
print_step "RÉSUMÉ DU DÉPLOIEMENT"
echo ""
print_success "🎉 Déploiement terminé!"
echo ""
print_info "Services disponibles:"
echo "  • API MAR:        http://localhost:8000"
echo "  • Documentation:  http://localhost:8000/docs"
echo "  • Santé:         http://localhost:8000/health"
echo "  • Prometheus:    http://localhost:9090"
echo "  • MinIO:         http://localhost:9001"
echo ""
print_info "Commandes utiles:"
echo "  • État:          docker-compose -f docker-compose.ultimate.yml ps"
echo "  • Logs:          docker-compose -f docker-compose.ultimate.yml logs [service]"
echo "  • Arrêt:         docker-compose -f docker-compose.ultimate.yml down"
echo "  • Redémarrage:   docker-compose -f docker-compose.ultimate.yml restart [service]"
echo ""

# Vérification finale optionnelle
print_warning "Voulez-vous afficher les logs récents de l'API pour vérifier? (y/N)"
read -p "> " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    print_info "Derniers logs de l'API MAR:"
    echo "=========================="
    docker-compose -f docker-compose.ultimate.yml logs --tail=30 mar-api
fi

echo ""
print_success "Déploiement manuel terminé avec succès!"
print_info "Le système MAR est maintenant opérationnel avec les corrections de dépendances appliquées."
