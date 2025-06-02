# Guide de Déploiement Final - Résolution des Conflits de Dépendances

## Problème Identifié

Le conflit de dépendances persiste avec `httpx==0.26.0` et `ollama==0.1.7`. Voici la solution complète.

## Solutions Appliquées

### 1. Correction des Fichiers Requirements

✅ **requirements.txt** - Corrigé avec versions compatibles
✅ **requirements.staging.txt** - Optimisé pour staging
✅ **requirements-minimal.txt** - Corrigé pour éviter confusion

### 2. Configuration Docker Optimisée

✅ **Dockerfile.staging** - Utilise `requirements.staging.txt`
✅ **docker-compose.staging.yml** - Configuré pour utiliser `Dockerfile.staging`

### 3. Scripts de Déploiement

✅ **staging-deploy.sh** - Script complet avec nettoyage cache Docker
✅ **final-validation.sh** - Validation des configurations

## Instructions de Déploiement sur Serveur

### Étape 1: Transférer les Fichiers Corrigés

```bash
# Sur votre machine locale, transférer les fichiers corrigés vers le serveur
scp -r /Users/abderrahman/Documents/MAR/requirements*.txt votre_serveur:~/AI_Deplyment_First_step/MAAR/
scp /Users/abderrahman/Documents/MAR/Dockerfile.staging votre_serveur:~/AI_Deplyment_First_step/MAAR/
scp /Users/abderrahman/Documents/MAR/docker-compose.staging.yml votre_serveur:~/AI_Deplyment_First_step/MAAR/
scp /Users/abderrahman/Documents/MAR/.env.staging votre_serveur:~/AI_Deplyment_First_step/MAAR/
scp -r /Users/abderrahman/Documents/MAR/scripts/ votre_serveur:~/AI_Deplyment_First_step/MAAR/
```

### Étape 2: Sur le Serveur - Nettoyer l'Environnement Docker

```bash
cd ~/AI_Deplyment_First_step/MAAR/

# Arrêter tous les conteneurs et nettoyer
docker-compose -f docker-compose.yml -f docker-compose.staging.yml down --remove-orphans

# Supprimer toutes les images liées au projet
docker images | grep -E "(maar|rag|staging)" | awk '{print $3}' | xargs -r docker rmi -f

# Nettoyer le cache Docker
docker builder prune -af
docker system prune -af

# Supprimer les volumes pour un démarrage propre
docker volume prune -f
```

### Étape 3: Validation des Dépendances

```bash
# Vérifier que les fichiers requirements sont corrects
grep -n "httpx" requirements*.txt
grep -n "ollama" requirements*.txt

# Les résultats attendus:
# requirements.txt:httpx>=0.25.2,<0.26.0
# requirements.staging.txt:httpx>=0.25.0
# requirements-minimal.txt:httpx>=0.25.2,<0.26.0
# requirements.txt:ollama>=0.2.0
# requirements.staging.txt:ollama>=0.2.0
# requirements-minimal.txt:ollama>=0.2.0
```

### Étape 4: Déploiement avec Script Automatisé

```bash
# Rendre le script exécutable
chmod +x scripts/staging-deploy.sh

# Exécuter le déploiement staging
./scripts/staging-deploy.sh
```

### Étape 5: Déploiement Manuel (Alternative)

Si le script automatisé ne fonctionne pas:

```bash
# Construction forcée avec le Dockerfile.staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging build --no-cache --pull

# Démarrage des services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d

# Vérification des logs
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging logs -f rag_api
```

## Vérifications Post-Déploiement

### Test de l'API

```bash
# Vérifier que l'API répond
curl -f http://localhost:8000/health

# Tester l'endpoint de documentation
curl -f http://localhost:8000/docs
```

### Vérification des Services

```bash
# Statut de tous les services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging ps

# Logs des services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging logs --tail=50
```

## Résolution de Problèmes

### Si le Conflit Persiste

1. **Vérifier le cache pip dans le conteneur:**
```bash
docker run --rm -it python:3.11-slim bash
pip install --dry-run httpx==0.26.0 ollama==0.1.7
```

2. **Forcer l'utilisation de requirements.staging.txt:**
```bash
# Modifier temporairement le Dockerfile.staging pour être plus explicite
docker build -f Dockerfile.staging --build-arg REQUIREMENTS_FILE=requirements.staging.txt -t mar-staging .
```

3. **Installation manuelle des dépendances:**
```bash
# Dans le conteneur
pip uninstall -y httpx ollama
pip install "httpx>=0.25.2,<0.26.0" "ollama>=0.2.0"
```

## URLs d'Accès (Post-Déploiement)

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Jaeger**: http://localhost:16686
- **Prometheus**: http://localhost:9090

## Support et Monitoring

Les logs sont accessibles via:
```bash
# Logs de l'API principale
docker logs rag_api_staging -f

# Logs de tous les services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging logs -f
```
