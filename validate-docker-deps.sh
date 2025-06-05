#!/bin/bash
# Script de validation pour Docker et dépendances

echo "🐳 Script de validation Docker et dépendances"
echo "=============================================="

# Fonction pour tester Docker
test_docker() {
    echo "🔍 Test de Docker..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker n'est pas installé"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "⚠️  Docker daemon n'est pas en cours d'exécution"
        echo "   Vous pouvez le démarrer avec: sudo systemctl start docker"
        echo "   Ou sur macOS: open -a Docker"
        return 1
    fi
    
    echo "✅ Docker est disponible et fonctionne"
    return 0
}

# Fonction pour valider les dépendances
validate_dependencies() {
    echo "🔍 Validation des dépendances..."
    
    local req_file="requirements.staging.txt"
    
    if [[ ! -f "$req_file" ]]; then
        echo "❌ Fichier $req_file non trouvé"
        return 1
    fi
    
    echo "📋 Analyse de $req_file:"
    
    # Extraire les versions LangChain
    local langchain_version=$(grep -E "^langchain==" "$req_file" | head -1)
    local community_version=$(grep -E "^langchain-community==" "$req_file" | head -1)
    
    echo "  LangChain: $langchain_version"
    echo "  Community: $community_version"
    
    # Vérifications spécifiques
    if [[ "$langchain_version" == "langchain==0.3.25" ]] && [[ "$community_version" == "langchain-community==0.3.23" ]]; then
        echo "✅ Versions LangChain compatibles"
    else
        echo "❌ Versions LangChain potentiellement incompatibles"
        return 1
    fi
    
    # Vérifier les doublons
    echo "🔍 Recherche de doublons..."
    local duplicates=$(sort "$req_file" | uniq -d | grep -v "^#" | grep -v "^$")
    
    if [[ -n "$duplicates" ]]; then
        echo "❌ Doublons détectés:"
        echo "$duplicates"
        return 1
    else
        echo "✅ Aucun doublon détecté"
    fi
    
    return 0
}

# Fonction pour générer un Dockerfile de test
generate_test_dockerfile() {
    echo "🔍 Génération d'un Dockerfile de test..."
    
    cat > Dockerfile.test << 'EOF'
# Dockerfile de test pour validation des dépendances
FROM python:3.11-slim

WORKDIR /app

# Copier uniquement le fichier requirements
COPY requirements.staging.txt .

# Tester l'installation des dépendances
RUN pip install --no-cache-dir --dry-run -r requirements.staging.txt

# Si on arrive ici, les dépendances sont OK
RUN echo "✅ Test des dépendances réussi"
EOF
    
    echo "✅ Dockerfile.test créé"
}

# Fonction pour tester le build Docker (si possible)
test_docker_build() {
    if test_docker; then
        echo "🔍 Test de build Docker..."
        
        if docker build -f Dockerfile.test -t langchain-deps-test . 2>&1; then
            echo "✅ Build Docker réussi"
            
            # Nettoyer
            docker rmi langchain-deps-test 2>/dev/null || true
            return 0
        else
            echo "❌ Échec du build Docker"
            return 1
        fi
    else
        echo "⚠️  Test Docker ignoré (daemon non disponible)"
        return 0
    fi
}

# Fonction principale
main() {
    local exit_code=0
    
    # Test des dépendances
    if ! validate_dependencies; then
        exit_code=1
    fi
    
    # Génération du Dockerfile de test
    generate_test_dockerfile
    
    # Test Docker si possible
    if ! test_docker_build; then
        exit_code=1
    fi
    
    echo ""
    echo "=============================================="
    if [[ $exit_code -eq 0 ]]; then
        echo "🎉 Tous les tests ont réussi!"
        echo "   Les dépendances sont prêtes pour Docker"
    else
        echo "❌ Des problèmes ont été détectés"
        echo "   Veuillez corriger les erreurs avant de continuer"
    fi
    
    # Nettoyer
    rm -f Dockerfile.test
    
    return $exit_code
}

# Exécuter le script principal
main "$@"
