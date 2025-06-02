# 🚀 MAR - Instructions de Déploiement Final

## État Actuel

✅ **Conflits de dépendances résolus** - Corrections appliquées à tous les fichiers requirements
✅ **Docker configurations corrigées** - Dockerfile.staging optimisé
✅ **Scripts de déploiement créés** - Automatisation complète
✅ **Environnement staging configuré** - Prêt pour déploiement

## 📋 Checklist de Déploiement

### Sur votre Machine Locale (macOS)

1. **Vérifier les fichiers corrigés** ✅
   - `requirements.txt` ✅
   - `requirements.staging.txt` ✅ 
   - `requirements-minimal.txt` ✅
   - `Dockerfile.staging` ✅
   - `docker-compose.staging.yml` ✅
   - `.env.staging` ✅

2. **Scripts disponibles** ✅
   - `scripts/staging-deploy.sh` - Déploiement automatisé
   - `scripts/final-validation.sh` - Validation système
   - `scripts/ultimate-fix.sh` - Résolution ultime des conflits

### Sur votre Serveur Ubuntu

#### Étape 1: Transfert des Fichiers

```bash
# Transférer tous les fichiers nécessaires depuis votre Mac
scp -r /Users/abderrahman/Documents/MAR/* votre_serveur:~/AI_Deplyment_First_step/MAAR/
```

#### Étape 2: Connexion au Serveur et Préparation

```bash
# Se connecter au serveur
ssh votre_serveur

# Aller dans le répertoire de travail
cd ~/AI_Deplyment_First_step/MAAR/

# Vérifier que tous les fichiers sont présents
ls -la requirements*.txt
ls -la Dockerfile*
ls -la docker-compose*.yml
ls -la scripts/
```

#### Étape 3: Option A - Déploiement Automatisé (Recommandé)

```bash
# Rendre les scripts exécutables
chmod +x scripts/*.sh

# Exécuter le script de déploiement automatisé
./scripts/staging-deploy.sh
```

#### Étape 4: Option B - Résolution Ultime (Si problèmes persistent)

```bash
# Si le déploiement automatisé échoue, utiliser le script de résolution ultime
./scripts/ultimate-fix.sh
```

#### Étape 5: Option C - Déploiement Manuel (Backup)

```bash
# Nettoyer complètement Docker
docker system prune -af --volumes

# Construire avec le Dockerfile staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging build --no-cache

# Démarrer les services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d

# Vérifier les logs
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging logs -f
```

## 🔍 Vérifications Post-Déploiement

### Tests de Santé

```bash
# Vérifier que l'API répond
curl -f http://localhost:8000/health

# Vérifier la documentation
curl -f http://localhost:8000/docs

# Vérifier le statut des services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging ps
```

### URLs d'Accès

- **API Principale**: http://votre_serveur:8000
- **Documentation**: http://votre_serveur:8000/docs
- **Grafana**: http://votre_serveur:3000 (admin/admin)
- **Jaeger**: http://votre_serveur:16686
- **Prometheus**: http://votre_serveur:9090

## 🛠️ Résolution de Problèmes

### Si l'API ne répond pas

```bash
# Vérifier les logs de l'API
docker logs rag_api_staging -f

# Vérifier tous les services
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging logs --tail=100
```

### Si conflits de dépendances persistent

```bash
# Vérifier les versions installées dans le conteneur
docker exec rag_api_staging pip list | grep -E "(httpx|ollama)"

# Réinstaller manuellement si nécessaire
docker exec rag_api_staging pip uninstall -y httpx ollama
docker exec rag_api_staging pip install "httpx>=0.25.0,<0.26.0" "ollama>=0.2.0"
```

### Si erreurs de construction Docker

```bash
# Construction avec logs détaillés
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging build --no-cache --progress=plain

# Nettoyer le cache complètement
docker builder prune -af
```

## 📞 Support

### Logs Importants

```bash
# Logs en temps réel
docker-compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging logs -f

# Logs spécifiques par service
docker logs postgres-staging-service
docker logs redis-staging-service  
docker logs qdrant-staging-service
docker logs rag_api_staging
```

### Monitoring

- **Métriques**: http://votre_serveur:9090 (Prometheus)
- **Dashboards**: http://votre_serveur:3000 (Grafana)
- **Tracing**: http://votre_serveur:16686 (Jaeger)

## ✅ Validation Finale

Une fois le déploiement réussi, vous devriez voir:

1. ✅ API accessible sur http://votre_serveur:8000/health
2. ✅ Documentation sur http://votre_serveur:8000/docs
3. ✅ Tous les conteneurs en cours d'exécution
4. ✅ Logs sans erreurs critiques
5. ✅ Monitoring opérationnel

## 🎯 Prochaines Étapes

Après validation staging:

1. **Tests d'intégration** - Valider toutes les fonctionnalités
2. **Tests de charge** - Vérifier les performances
3. **Sauvegarde** - Configurer les backups automatiques
4. **Production** - Déployer en production avec les mêmes configurations

---

**📧 Besoin d'aide?** Consultez les logs et utilisez les scripts de diagnostic fournis.
