# 🚀 Guide de Démarrage Rapide - Plateforme MAR

Ce guide vous aide à démarrer rapidement avec la plateforme MAR et résoudre les problèmes courants.

## ⚡ Démarrage en Une Commande

```bash
# Configuration complète automatique
make setup && make docker-up
```

## 🔧 Configuration Manuelle

Si vous préférez faire la configuration étape par étape :

### 1. Configuration initiale
```bash
# Copie du fichier de configuration
cp .env.example .env

# Création des répertoires nécessaires
mkdir -p data/{vector_store,uploads,backups} logs
```

### 2. Démarrage des services
```bash
# Démarrage de la stack complète
make docker-up
# ou directement avec docker-compose
docker-compose up -d
```

## 🎯 URLs d'Accès

Une fois les services démarrés :

- **Interface Utilisateur**: http://localhost:8501
- **API REST**: http://localhost:8000
- **Documentation API**: http://localhost:8000/docs
- **Grafana (Monitoring)**: http://localhost:3000
- **Prometheus (Métriques)**: http://localhost:9090

## 🛠️ Commandes Utiles

### Commandes de Base
```bash
make help              # Affiche toutes les commandes disponibles
make setup              # Configuration initiale complète
make docker-up          # Démarre la stack Docker
make docker-down        # Arrête la stack Docker
make logs               # Affiche les logs des services
make health             # Vérifie la santé des services
```

### Développement
```bash
make dev                # Lance l'environnement de développement
make dev-api            # Lance uniquement l'API
make dev-ui             # Lance uniquement l'interface Streamlit
make test               # Exécute les tests
make lint               # Vérifie la qualité du code
```

### Gestion Docker
```bash
make build              # Construit les images Docker
make clean-docker       # Nettoie les images Docker
make restart            # Redémarre la stack
```

## ❌ Problèmes Courants et Solutions

### Problème : `No such file or directory: .env.example`
**Solution** : Le fichier existe, utilisez la commande setup :
```bash
make setup
```

### Problème : `No rule to make target 'docker-up'`
**Solution** : La commande existe ! Essayez :
```bash
make docker-up
# ou directement
make up
```

### Problème : Port déjà utilisé
**Solution** : Arrêtez les services existants :
```bash
make docker-down
# Puis redémarrez
make docker-up
```

### Problème : Images Docker manquantes
**Solution** : Reconstruisez les images :
```bash
make build
make docker-up
```

### Problème : Permissions Docker
**Solution** : Ajoutez votre utilisateur au groupe Docker (macOS/Linux) :
```bash
sudo usermod -aG docker $USER
# Redémarrez votre session
```

### Problème : Services lents à démarrer
**Solution** : Les services peuvent prendre quelques minutes au premier démarrage. Vérifiez les logs :
```bash
make logs
```

## 🔍 Débogage

### Vérifier l'état des services
```bash
docker-compose ps              # État des conteneurs
make health                    # Santé des services
make logs                      # Logs de tous les services
make logs-api                  # Logs de l'API uniquement
make logs-ui                   # Logs de l'interface uniquement
```

### Redémarrage propre
```bash
make docker-down               # Arrêt
docker system prune -f         # Nettoyage (optionnel)
make docker-up                 # Redémarrage
```

### Reconstruction complète
```bash
make docker-down
make clean-docker
make build
make docker-up
```

## 📋 Prérequis

- **Docker** : Version 20.10+
- **Docker Compose** : Version 2.0+
- **Make** : Pour les commandes Makefile
- **Git** : Pour le clonage du projet

### Vérification des prérequis
```bash
docker --version
docker-compose --version
make --version
```

## 🚨 Support et Aide

1. **Vérifiez d'abord** : `make help` pour voir toutes les commandes
2. **Logs** : `make logs` pour voir les erreurs
3. **État** : `make health` pour vérifier les services
4. **Redémarrage** : `make restart` si quelque chose ne va pas

## 📊 Monitoring

Accédez à Grafana sur http://localhost:3000 pour surveiller :
- Performances de l'API
- Utilisation des ressources
- Métriques métier

Identifiants par défaut :
- **Utilisateur** : `admin`
- **Mot de passe** : `admin`

---

**💡 Astuce** : Utilisez `make setup && make docker-up` pour un démarrage en une commande !
