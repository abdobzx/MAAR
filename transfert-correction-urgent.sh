#!/bin/zsh

# 🚨 TRANSFERT CORRECTION LANGCHAIN VERSION - URGENT
# Corrige l'erreur langchain-community==0.3.25 qui n'existe pas

set -e

if [[ $# -eq 0 ]]; then
    echo "❌ Usage: $0 user@server"
    echo "Exemple: $0 root@Ubuntu-2204-jammy-amd64-base"
    exit 1
fi

SERVER=$1
echo "🚨 TRANSFERT CORRECTION LANGCHAIN VERS $SERVER"
echo "=============================================="

# Vérifier que la correction locale est appliquée
if grep -q "langchain-community==0.3.25" requirements.fast.txt; then
    echo "❌ Erreur encore présente localement - correction automatique..."
    
    # Correction locale immédiate
    sed -i.bak 's/langchain==0.3.25/langchain==0.3.24/g' requirements.fast.txt
    sed -i.bak 's/langchain-community==0.3.25/langchain-community==0.3.24/g' requirements.fast.txt
    
    echo "✅ Correction locale appliquée"
fi

echo "📤 Transfert fichiers corrigés..."
scp requirements.fast.txt correction-version-langchain.sh "$SERVER:/tmp/"

echo "🔧 Exécution correction sur serveur..."
ssh "$SERVER" << 'ENDSSH'
    echo "📍 Localisation du projet..."
    
    # Recherche du répertoire de projet
    for dir in "$HOME/AI_Deplyment_First_step/MAAR" "$HOME/MAAR" "$HOME/rag-enterprise" "$HOME/rag" "$(pwd)"; do
        if [[ -f "$dir/docker-compose.yml" ]] || [[ -f "$dir/requirements.txt" ]]; then
            PROJECT_DIR="$dir"
            echo "✅ Projet trouvé: $PROJECT_DIR"
            break
        fi
    done
    
    if [[ -z "$PROJECT_DIR" ]]; then
        echo "❌ Répertoire projet non trouvé"
        echo "Exécuter manuellement:"
        echo "cp /tmp/requirements.fast.txt /tmp/correction-version-langchain.sh /chemin/vers/projet/"
        echo "cd /chemin/vers/projet/ && chmod +x correction-version-langchain.sh && ./correction-version-langchain.sh"
        exit 1
    fi
    
    # Copie et exécution
    cp /tmp/requirements.fast.txt "$PROJECT_DIR/"
    cp /tmp/correction-version-langchain.sh "$PROJECT_DIR/"
    
    cd "$PROJECT_DIR"
    chmod +x correction-version-langchain.sh
    
    echo "🚀 Exécution correction immédiate..."
    ./correction-version-langchain.sh
ENDSSH

echo ""
echo "🎯 CORRECTION APPLIQUÉE"
echo "Erreur: langchain-community==0.3.25 → langchain-community==0.3.24"
echo "Build devrait maintenant réussir en 2-5 minutes"
