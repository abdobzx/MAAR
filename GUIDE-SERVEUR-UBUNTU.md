# 🚀 Guide de Déploiement Serveur Ubuntu - MAR System

## ✅ Pré-requis Serveur

### 1. Installation Docker & Docker Compose
```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Installation Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Installation Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Redémarrage requis
sudo reboot
```

### 2. Vérification Post-Installation
```bash
docker --version
docker-compose --version
docker run hello-world
```

## 📁 Transfert des Fichiers

### Option 1: Transfert Direct (recommandé)
```bash
# Sur votre machine locale
./transfer-to-server.sh
```

### Option 2: Transfert Manuel
```bash
# Depuis votre machine locale
scp -r requirements.final.txt requirements.debug.txt Dockerfile.ultimate docker-compose.ultimate.yml database/ monitoring/ scripts/ api/ core/ agents/ user@server:/home/user/MAR/
```

### Option 3: Git Clone
```bash
# Sur le serveur
git clone <your-repo> MAR
cd MAR
```

## 🚀 Déploiement sur Serveur

### 1. Connexion au Serveur
```bash
ssh user@your-server-ip
cd MAR
```

### 2. Vérification des Fichiers
```bash
ls -la requirements.final.txt
ls -la Dockerfile.ultimate
ls -la docker-compose.ultimate.yml
ls -la scripts/deploy-ultimate.sh
```

### 3. Exécution du Déploiement
```bash
# Rendre les scripts exécutables
chmod +x scripts/*.sh

# Lancer le déploiement ultimate
./scripts/deploy-ultimate.sh
```

### 4. Sélection du Menu
```
🎯 Script de déploiement ultimate MAR
=====================================
1) Déploiement complet
2) Nettoyage seulement
3) Construction seulement
4) Test image
5) Vérification santé
6) Afficher logs
7) Quitter

Choisissez une option: 1
```

## 🔍 Vérifications Post-Déploiement

### 1. Vérification des Services
```bash
# Status des conteneurs
docker-compose -f docker-compose.ultimate.yml ps

# Logs des services
docker-compose -f docker-compose.ultimate.yml logs -f
```

### 2. Tests de Connectivité
```bash
# API Health Check
curl -f http://localhost:8000/health

# Swagger UI
curl -f http://localhost:8000/docs

# Qdrant Health
curl -f http://localhost:6333/health

# PostgreSQL
docker-compose -f docker-compose.ultimate.yml exec postgres pg_isready -U mar_user

# Redis
docker-compose -f docker-compose.ultimate.yml exec redis redis-cli ping
```

### 3. Accès depuis l'Extérieur
```bash
# Ouvrir les ports (si firewall actif)
sudo ufw allow 8000/tcp
sudo ufw allow 9090/tcp
sudo ufw allow 6333/tcp

# Vérifier l'IP du serveur
ip addr show
```

## 🚨 Résolution de Problèmes

### Problème: Build Docker Échoue
```bash
# Nettoyer complètement Docker
sudo docker system prune -af
sudo docker volume prune -f

# Relancer avec le debug requirements
docker build -f Dockerfile.ultimate --build-arg REQUIREMENTS_FILE=requirements.debug.txt -t mar-ultimate:debug .
```

### Problème: Service ne Démarre Pas
```bash
# Vérifier les logs spécifiques
docker-compose -f docker-compose.ultimate.yml logs mar-api

# Redémarrer un service spécifique
docker-compose -f docker-compose.ultimate.yml restart mar-api
```

### Problème: Ports Occupés
```bash
# Vérifier les ports utilisés
sudo netstat -tulpn | grep :8000

# Arrêter les services conflictuels
sudo systemctl stop nginx  # ou autre service web
```

### Problème: Permissions
```bash
# Corriger les permissions
sudo chown -R $USER:$USER /home/$USER/MAR
chmod +x scripts/*.sh
```

## 📊 Monitoring & Maintenance

### 1. Accès aux Services
- **API MAR** : http://server-ip:8000
- **Swagger UI** : http://server-ip:8000/docs
- **Prometheus** : http://server-ip:9090
- **Qdrant UI** : http://server-ip:6333/dashboard

### 2. Commandes de Maintenance
```bash
# Redémarrer tous les services
docker-compose -f docker-compose.ultimate.yml restart

# Mise à jour de l'image
docker-compose -f docker-compose.ultimate.yml down
docker build -f Dockerfile.ultimate -t mar-ultimate:latest . --no-cache
docker-compose -f docker-compose.ultimate.yml up -d

# Backup des données
docker run --rm -v mar_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

### 3. Logs Centralisés
```bash
# Logs en temps réel
docker-compose -f docker-compose.ultimate.yml logs -f

# Logs d'un service spécifique
docker-compose -f docker-compose.ultimate.yml logs -f mar-api

# Logs avec filtre
docker-compose -f docker-compose.ultimate.yml logs | grep ERROR
```

## 🔄 Mise à Jour du Système

### 1. Mise à Jour du Code
```bash
# Pull des dernières modifications
git pull origin main

# Rebuild et redéploiement
docker-compose -f docker-compose.ultimate.yml down
./scripts/deploy-ultimate.sh
```

### 2. Mise à Jour des Dépendances
```bash
# Modifier requirements.final.txt si nécessaire
# Rebuild complet
docker build -f Dockerfile.ultimate -t mar-ultimate:latest . --no-cache
docker-compose -f docker-compose.ultimate.yml up -d
```

## 🎯 Checklist de Validation Finale

- [ ] ✅ Docker et Docker Compose installés
- [ ] ✅ Tous les fichiers transférés
- [ ] ✅ Scripts exécutables
- [ ] ✅ Build Docker réussi
- [ ] ✅ Tous les conteneurs démarrés
- [ ] ✅ API accessible (http://server-ip:8000/health)
- [ ] ✅ Swagger UI accessible (http://server-ip:8000/docs)
- [ ] ✅ Base de données connectée
- [ ] ✅ Qdrant opérationnel
- [ ] ✅ Redis opérationnel
- [ ] ✅ Logs sans erreurs critiques
- [ ] ✅ Monitoring accessible

## 📞 Support

En cas de problème, vérifiez :
1. Les logs : `docker-compose -f docker-compose.ultimate.yml logs`
2. L'état des services : `docker-compose -f docker-compose.ultimate.yml ps`
3. Les ressources système : `htop` ou `free -h`
4. L'espace disque : `df -h`

---

**🎉 Une fois tous les checks validés, votre système MAR est opérationnel en production !**
