#!/bin/bash

# 📡 TRANSFERT ULTRA-RAPIDE VERS SERVEUR UBUNTU
# Transfère uniquement les fichiers essentiels pour résoudre le build 43min
# Utilisation : ./transfert-urgence-ubuntu.sh [user@server]

set -e

SERVER=${1:-"ubuntu@your-server"}
if [ "$SERVER" == "ubuntu@your-server" ]; then
    echo "❌ Usage : $0 user@server-ip"
    echo "Exemple : $0 ubuntu@192.168.1.100"
    exit 1
fi

echo "📡 TRANSFERT D'URGENCE VERS $SERVER"
echo "==================================="

# Fichiers critiques à transférer
FICHIERS_URGENCE=(
    "requirements.fast.txt"
    "Dockerfile.fast" 
    "docker-compose.fast.yml"
    "solution-43min-build.sh"
    "urgence-rebuild.sh"
)

echo "📦 Préparation du package d'urgence..."

# Création d'un tar avec les fichiers essentiels
tar -czf urgence-build-fix.tar.gz \
    requirements.fast.txt \
    Dockerfile.fast \
    docker-compose.fast.yml \
    solution-43min-build.sh \
    urgence-rebuild.sh \
    2>/dev/null || echo "⚠️ Certains fichiers peuvent être manquants"

echo "📤 Transfert vers $SERVER..."
if scp urgence-build-fix.tar.gz "$SERVER:/tmp/"; then
    echo "✅ Transfert réussi"
else
    echo "❌ Échec transfert - vérifiez connexion SSH"
    exit 1
fi

echo "🚀 Exécution à distance sur $SERVER..."
ssh "$SERVER" << 'ENDSSH'
    cd /tmp
    echo "📦 Extraction package urgence..."
    tar -xzf urgence-build-fix.tar.gz
    
    echo "📍 Copie vers répertoire projet..."
    # Adapter le chemin selon votre projet
    PROJECT_DIR="$HOME/rag-enterprise" # ou autre répertoire
    
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Répertoire projet $PROJECT_DIR non trouvé"
        echo "Fichiers extraits dans /tmp/ - copier manuellement"
        ls -la /tmp/*.txt /tmp/*.yml /tmp/*.sh 2>/dev/null || true
    else
        cp requirements.fast.txt "$PROJECT_DIR/"
        cp Dockerfile.fast "$PROJECT_DIR/"
        cp docker-compose.fast.yml "$PROJECT_DIR/"
        cp solution-43min-build.sh "$PROJECT_DIR/"
        cp urgence-rebuild.sh "$PROJECT_DIR/"
        
        cd "$PROJECT_DIR"
        chmod +x *.sh
        
        echo "✅ Fichiers copiés dans $PROJECT_DIR"
        echo "🚨 MAINTENANT EXÉCUTER :"
        echo "   cd $PROJECT_DIR"
        echo "   ./solution-43min-build.sh"
    fi
ENDSSH

# Nettoyage local
rm -f urgence-build-fix.tar.gz

echo ""
echo "🎯 PROCHAINES ÉTAPES SUR SERVEUR :"
echo "1. ssh $SERVER"
echo "2. cd [répertoire-projet]"
echo "3. ./solution-43min-build.sh"
echo ""
echo "⏱️  Temps attendu : 2-5 minutes (vs 43 minutes avant)"
