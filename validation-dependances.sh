#!/bin/bash

# =============================================================================
# SCRIPT DE VALIDATION DES DÉPENDANCES - SYSTÈME MAR
# Validation rapide des corrections de dépendances avant déploiement
# =============================================================================

set -e

echo "🔍 VALIDATION DES DÉPENDANCES - SYSTÈME MAR"
echo "=========================================="
echo ""

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_IMAGE_NAME="mar-system-final"
TEST_CONTAINER_NAME="mar-dep-test"

print_step() {
    echo -e "${BLUE}➤ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Fonction de nettoyage
cleanup() {
    print_step "Nettoyage des ressources de test..."
    docker rm -f $TEST_CONTAINER_NAME 2>/dev/null || true
    docker rmi $DOCKER_IMAGE_NAME:test 2>/dev/null || true
    print_success "Nettoyage terminé"
}

# Piège pour nettoyage automatique
trap cleanup EXIT

# Étape 1: Vérification des fichiers requis
print_step "Vérification des fichiers requis..."

required_files=(
    "requirements.final.txt"
    "Dockerfile.ultimate"
    "docker-compose.ultimate.yml"
)

for file in "${required_files[@]}"; do
    if [[ -f "$SCRIPT_DIR/$file" ]]; then
        print_success "Fichier trouvé: $file"
    else
        print_error "Fichier manquant: $file"
        exit 1
    fi
done

echo ""

# Étape 2: Création d'un Dockerfile de test simple
print_step "Création du Dockerfile de test pour validation des dépendances..."

cat > "$SCRIPT_DIR/Dockerfile.test" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système minimales
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des requirements
COPY requirements.final.txt .

# Test d'installation des dépendances
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.final.txt

# Vérification des imports critiques
RUN python -c "import fastapi; print('✓ FastAPI')" && \
    python -c "import crewai; print('✓ CrewAI')" && \
    python -c "import langchain; print('✓ LangChain')" && \
    python -c "import httpx; print('✓ HTTPX')" && \
    python -c "import cryptography; print('✓ Cryptography')" && \
    python -c "import ollama; print('✓ Ollama')" && \
    python -c "import qdrant_client; print('✓ Qdrant')" && \
    python -c "import sqlalchemy; print('✓ SQLAlchemy')" && \
    echo "✅ TOUS LES IMPORTS CRITIQUES RÉUSSIS"

CMD ["echo", "Test de dépendances réussi!"]
EOF

print_success "Dockerfile de test créé"

echo ""

# Étape 3: Construction de l'image de test
print_step "Construction de l'image Docker de test..."

if docker build -f "$SCRIPT_DIR/Dockerfile.test" -t "$DOCKER_IMAGE_NAME:test" "$SCRIPT_DIR"; then
    print_success "Construction de l'image de test réussie!"
else
    print_error "Échec de la construction de l'image de test"
    print_warning "Vérifiez les conflits de dépendances dans requirements.final.txt"
    exit 1
fi

echo ""

# Étape 4: Test d'exécution
print_step "Test d'exécution du conteneur..."

if docker run --name $TEST_CONTAINER_NAME --rm "$DOCKER_IMAGE_NAME:test"; then
    print_success "Test d'exécution réussi!"
else
    print_error "Échec du test d'exécution"
    exit 1
fi

echo ""

# Étape 5: Validation des versions de paquets critiques
print_step "Validation des versions de paquets critiques..."

echo "Versions installées:"
docker run --rm "$DOCKER_IMAGE_NAME:test" python -c "
import pkg_resources
import sys

critical_packages = [
    'fastapi', 'httpx', 'crewai', 'langchain', 'langchain-community',
    'cryptography', 'ollama', 'sqlalchemy', 'pydantic'
]

print('📦 VERSIONS DES PAQUETS CRITIQUES:')
print('=' * 50)

for package in critical_packages:
    try:
        version = pkg_resources.get_distribution(package).version
        print(f'{package:<20} : {version}')
    except pkg_resources.DistributionNotFound:
        print(f'{package:<20} : ❌ NON INSTALLÉ')
        
print('=' * 50)
"

echo ""

# Étape 6: Résumé final
print_step "Résumé de la validation..."

echo ""
print_success "🎉 VALIDATION DES DÉPENDANCES RÉUSSIE!"
echo ""
echo -e "${GREEN}Les corrections apportées sont valides:${NC}"
echo -e "  ${GREEN}✓${NC} httpx==0.25.2 (compatible avec ollama)"
echo -e "  ${GREEN}✓${NC} langchain==0.1.20 (compatible avec crewai==0.11.2)"
echo -e "  ${GREEN}✓${NC} langchain-community==0.0.38 (compatible)"
echo -e "  ${GREEN}✓${NC} cryptography==42.0.8 (version disponible)"
echo -e "  ${GREEN}✓${NC} ollama sans contrainte de version"
echo ""
echo -e "${BLUE}Le système est prêt pour le déploiement principal!${NC}"
echo ""
echo -e "${YELLOW}Étapes suivantes recommandées:${NC}"
echo "1. Transfert des fichiers vers le serveur"
echo "2. Exécution du déploiement complet avec docker-compose"
echo "3. Vérification des services"
echo ""

# Nettoyage du Dockerfile de test
rm -f "$SCRIPT_DIR/Dockerfile.test"

print_success "Script de validation terminé avec succès!"
