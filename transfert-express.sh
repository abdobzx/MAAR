#!/bin/zsh

# 🚀 TRANSFERT EXPRESS - SOLUTION BUILD 43MIN
# Usage: ./transfert-express.sh user@server

set -e

if [[ $# -eq 0 ]]; then
    echo "❌ Usage: $0 user@server"
    echo "Exemple: $0 ubuntu@192.168.1.100"
    exit 1
fi

SERVER=$1
echo "🚀 TRANSFERT EXPRESS VERS $SERVER"
echo "================================="

# Fichiers essentiels
FILES=(
    "requirements.fast.txt"
    "Dockerfile.fast"
    "docker-compose.fast.yml"
    "solution-43min-build.sh"
)

echo "📦 Vérification fichiers locaux..."
for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file ($(wc -l < "$file") lignes)"
    else
        echo "❌ MANQUANT: $file"
        exit 1
    fi
done

echo ""
echo "📤 Transfert vers $SERVER..."
if scp "${FILES[@]}" "$SERVER:/tmp/"; then
    echo "✅ Transfert réussi"
else
    echo "❌ Échec transfert"
    exit 1
fi

echo ""
echo "🔧 Configuration à distance..."
ssh "$SERVER" << 'ENDSSH'
    echo "📍 Recherche répertoire projet..."
    
    # Recherche du répertoire projet
    for dir in "$HOME/rag-enterprise" "$HOME/MAR" "$HOME/rag" "$HOME/project" "$(pwd)"; do
        if [[ -f "$dir/requirements.txt" ]] || [[ -f "$dir/docker-compose.yml" ]]; then
            PROJECT_DIR="$dir"
            break
        fi
    done
    
    if [[ -z "$PROJECT_DIR" ]]; then
        echo "❌ Répertoire projet non trouvé"
        echo "📁 Fichiers disponibles dans /tmp/"
        ls -la /tmp/requirements.fast.txt /tmp/Dockerfile.fast /tmp/docker-compose.fast.yml /tmp/solution-43min-build.sh
        echo ""
        echo "🔧 Copier manuellement dans votre répertoire projet:"
        echo "   cp /tmp/requirements.fast.txt /tmp/Dockerfile.fast /tmp/docker-compose.fast.yml /tmp/solution-43min-build.sh /chemin/vers/projet/"
        exit 1
    fi
    
    echo "✅ Projet trouvé: $PROJECT_DIR"
    
    # Copie des fichiers
    cp /tmp/requirements.fast.txt "$PROJECT_DIR/"
    cp /tmp/Dockerfile.fast "$PROJECT_DIR/"
    cp /tmp/docker-compose.fast.yml "$PROJECT_DIR/"
    cp /tmp/solution-43min-build.sh "$PROJECT_DIR/"
    
    cd "$PROJECT_DIR"
    chmod +x solution-43min-build.sh
    
    echo "✅ Fichiers installés dans $PROJECT_DIR"
    echo ""
    echo "🚨 EXÉCUTER MAINTENANT:"
    echo "   cd $PROJECT_DIR"
    echo "   ./solution-43min-build.sh"
ENDSSH

echo ""
echo "🎯 PROCHAINES ÉTAPES:"
echo "1. ssh $SERVER"
echo "2. cd [répertoire-projet]"  
echo "3. ./solution-43min-build.sh"
echo ""
echo "⏱️  Temps attendu: 2-5 minutes (vs 43 minutes avant)"
