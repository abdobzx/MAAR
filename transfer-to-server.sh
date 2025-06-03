#!/bin/bash

# Script de transfert vers le serveur Ubuntu
# Remplacez les variables par vos valeurs

SERVER_IP="YOUR_SERVER_IP"
SERVER_USER="YOUR_SERVER_USER"
REMOTE_PATH="/home/$SERVER_USER/MAR"

echo "🚀 Transfert des fichiers vers le serveur..."

# Vérification des variables
if [[ "$SERVER_IP" == "YOUR_SERVER_IP" || "$SERVER_USER" == "YOUR_SERVER_USER" ]]; then
    echo "❌ Veuillez modifier les variables SERVER_IP et SERVER_USER dans ce script"
    echo "   SERVER_IP=your.server.ip.address"
    echo "   SERVER_USER=your-username"
    exit 1
fi

# Vérification de la connectivité
if ! ssh -o ConnectTimeout=5 $SERVER_USER@$SERVER_IP "echo 'Connexion OK'"; then
    echo "❌ Impossible de se connecter au serveur $SERVER_IP"
    exit 1
fi

# Création du répertoire distant
echo "📁 Création du répertoire distant..."
ssh $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_PATH"

# Transfert des fichiers essentiels
echo "📦 Transfert des fichiers..."
rsync -avz --progress \
    requirements.final.txt \
    requirements.debug.txt \
    Dockerfile.ultimate \
    docker-compose.ultimate.yml \
    database/ \
    monitoring/ \
    scripts/ \
    api/ \
    core/ \
    agents/ \
    RESOLUTION-FINALE.md \
    GUIDE-SERVEUR-UBUNTU.md \
    ETAT-FINAL.md \
    $SERVER_USER@$SERVER_IP:$REMOTE_PATH/

echo "🔧 Configuration des permissions sur le serveur..."
ssh $SERVER_USER@$SERVER_IP "chmod +x $REMOTE_PATH/scripts/*.sh"

echo "✅ Transfert terminé avec succès!"
echo ""
echo "🎯 Prochaines étapes:"
echo "1. Se connecter au serveur:"
echo "   ssh $SERVER_USER@$SERVER_IP"
echo ""
echo "2. Naviguer vers le répertoire:"
echo "   cd $REMOTE_PATH"
echo ""
echo "3. Lancer le déploiement:"
echo "   chmod +x $REMOTE_PATH/scripts/*.sh"
echo ""
echo "4. Choisir 'Déploiement complet' dans le menu"
