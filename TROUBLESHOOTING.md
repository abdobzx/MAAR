# 🔧 Guide de Dépannage Rapide - Plateforme MAR

## Problèmes Courants et Solutions

### 1. ❌ Erreur "No rule to make target 'docker-up'"

**Problème**: La commande `make docker-up` ne fonctionne pas.

**Solutions**:
```bash
# Solution 1: Utiliser la commande corrigée
make setup          # Configuration initiale
make docker-up       # ou make up

# Solution 2: Utiliser Docker Compose directement
docker-compose up -d

# Solution 3: Utiliser le script de démarrage rapide
./quickstart.sh
```

### 2. ❌ Erreur "cp: .env.example: No such file or directory"

**Problème**: Le fichier `.env.example` n'existe pas.

**Solutions**:
```bash
# Vérifier la présence du fichier
ls -la .env.example

# Si absent, le recréer
cat > .env.example << 'EOF'
# Configuration MAR
DEV_MODE=true
LOG_LEVEL=INFO
API_PORT=8000
VECTOR_STORE_TYPE=faiss
OLLAMA_BASE_URL=http://localhost:11434
EOF

# Puis copier
cp .env.example .env
```

### 3. 🐳 Docker ne démarre pas

**Problème**: Docker Compose ne peut pas démarrer les services.

**Solutions**:
```bash
# Vérifier que Docker est démarré
docker info

# Si Docker n'est pas démarré
sudo systemctl start docker  # Linux
# ou démarrer Docker Desktop    # macOS/Windows

# Nettoyer et redémarrer
docker-compose down
docker system prune -f
docker-compose up -d
```

### 4. 🔌 Ports déjà utilisés

**Problème**: Erreur "Port already in use".

**Solutions**:
```bash
# Voir quels processus utilisent les ports
lsof -i :8000  # API
lsof -i :8501  # Streamlit
lsof -i :3000  # Grafana

# Arrêter les processus si nécessaire
kill -9 <PID>

# Ou changer les ports dans docker-compose.yml
```

### 5. 🧠 Ollama non accessible

**Problème**: La plateforme ne peut pas se connecter à Ollama.

**Solutions**:
```bash
# Vérifier Ollama
curl http://localhost:11434/api/tags

# Si pas installé
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve

# Télécharger un modèle
ollama pull llama2

# Mode simulation si Ollama indisponible
# La plateforme fonctionne avec des réponses simulées
```

## 🚀 Commandes de Démarrage Rapide

### Option 1: Script Automatique (Recommandé)
```bash
./quickstart.sh
```

### Option 2: Configuration Manuelle
```bash
# 1. Configuration
make setup

# 2. Démarrage
make docker-up

# 3. Vérification
curl http://localhost:8000/health
```

### Option 3: Docker Compose Direct
```bash
# Configuration
cp .env.example .env
mkdir -p data/{vector_store,uploads,backups} logs

# Démarrage
docker-compose up -d

# Logs
docker-compose logs -f
```

## 📊 Vérification des Services

### Health Checks
```bash
# API
curl http://localhost:8000/health

# Interface (peut prendre 1-2 min)
curl http://localhost:8501/healthz

# Monitoring
curl http://localhost:3000/api/health

# Prometheus
curl http://localhost:9090/-/healthy
```

### Status des Conteneurs
```bash
# Voir tous les conteneurs
docker-compose ps

# Logs d'un service spécifique
docker-compose logs -f mar-api
docker-compose logs -f mar-ui
```

## 🔍 Diagnostic Détaillé

### 1. Vérification de l'Environnement
```bash
# Versions
docker --version
docker-compose --version
python3 --version

# Espace disque
df -h

# RAM disponible
free -h  # Linux
vm_stat  # macOS
```

### 2. Test des Dépendances
```bash
# Test Python
python3 -c "import fastapi, streamlit; print('Dependencies OK')"

# Test de connectivité
ping google.com
```

### 3. Nettoyage Complet
```bash
# Arrêter tout
docker-compose down

# Nettoyer Docker
docker system prune -af
docker volume prune -f

# Supprimer les données (ATTENTION!)
rm -rf data/ logs/

# Reconfigurer
make setup
make docker-up
```

## 🆘 Support d'Urgence

### Si rien ne fonctionne

1. **Redémarrage complet**:
```bash
# Arrêter tout
docker-compose down
docker system prune -af

# Redémarrer Docker
sudo systemctl restart docker  # Linux
# ou redémarrer Docker Desktop

# Reconfigurer complètement
rm -rf data/ logs/ .env
make setup
make docker-up
```

2. **Mode minimal**:
```bash
# Lancer seulement l'API
docker-compose up -d mar-api

# Tester
curl http://localhost:8000/docs
```

3. **Mode développement Python**:
```bash
# Sans Docker
pip install -r requirements.txt
export DEV_MODE=true
python -m uvicorn api.main:app --reload --port 8000
```

## 📞 Obtenir de l'Aide

### Informations à fournir

```bash
# Collecter les informations de debug
echo "=== System Info ===" > debug.txt
uname -a >> debug.txt
docker --version >> debug.txt
docker-compose --version >> debug.txt

echo "=== Container Status ===" >> debug.txt
docker-compose ps >> debug.txt

echo "=== Logs ===" >> debug.txt
docker-compose logs --tail=50 >> debug.txt

echo "=== Disk Space ===" >> debug.txt
df -h >> debug.txt

# Envoyer debug.txt pour analyse
```

### Liens Utiles

- 📚 Documentation complète: [DEPLOYMENT.md](DEPLOYMENT.md)
- 🐛 Signaler un bug: GitHub Issues
- 💬 Communauté: GitHub Discussions
- 📧 Support: Voir README.md

---

**🎯 Objectif**: Avoir la plateforme fonctionnelle en moins de 10 minutes !**
