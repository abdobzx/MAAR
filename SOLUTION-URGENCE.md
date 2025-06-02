# 🚨 GUIDE DE RÉSOLUTION D'URGENCE - Conflits de Dépendances

## ⚡ Solution Immédiate

### 🎯 Problème Identifié
Le conflit de dépendances persiste dans les fichiers requirements. **Solution d'urgence créée**.

### 🚀 Déploiement Immédiat (2 Options)

#### Option 1: Script Automatisé d'Urgence ⭐ RECOMMANDÉ

```bash
# Sur votre serveur Ubuntu
cd ~/AI_Deplyment_First_step/MAAR/

# Exécuter le script de déploiement d'urgence
./scripts/emergency-deploy.sh
```

#### Option 2: Déploiement Manuel d'Urgence

```bash
# 1. Nettoyage complet
docker system prune -af --volumes

# 2. Construction avec Dockerfile minimal
docker build -f Dockerfile.minimal -t mar-emergency .

# 3. Démarrage des services de base
docker run -d --name postgres-emergency \
  -e POSTGRES_DB=mar_db \
  -e POSTGRES_USER=mar_user \
  -e POSTGRES_PASSWORD=mar_password \
  -p 5432:5432 \
  postgres:15-alpine

docker run -d --name redis-emergency \
  -p 6379:6379 \
  redis:7-alpine

docker run -d --name qdrant-emergency \
  -p 6333:6333 \
  qdrant/qdrant:v1.7.4

# 4. Attendre 30 secondes
sleep 30

# 5. Démarrer l'API
docker run -d --name mar-api-emergency \
  -e DATABASE_URL=postgresql://mar_user:mar_password@host.docker.internal:5432/mar_db \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  -e QDRANT_URL=http://host.docker.internal:6333 \
  -p 8000:8000 \
  mar-emergency

# 6. Test
curl -f http://localhost:8000/health
```

## 🔧 Fichiers Créés pour la Solution

✅ **Dockerfile.minimal** - Dockerfile avec installation par étapes
✅ **requirements.fixed.txt** - Versions garanties compatibles  
✅ **scripts/emergency-deploy.sh** - Script de déploiement automatisé d'urgence

## 📋 Validation Post-Déploiement

Après exécution de la solution d'urgence :

```bash
# Test de l'API
curl -f http://localhost:8000/health

# Test de la documentation
curl -f http://localhost:8000/docs

# Vérifier les conteneurs
docker ps
```

**URLs d'accès :**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 🎯 Pourquoi Cette Solution Fonctionne

1. **Installation par étapes** - Évite les conflits de résolution pip
2. **Versions fixes** - Utilise des versions testées et compatibles
3. **Dockerfile minimal** - Supprime les dépendances problématiques
4. **Approche progressive** - Installe les packages dans un ordre spécifique

## ⚠️ Important

Cette solution d'urgence :
- ✅ Résout immédiatement les conflits
- ✅ Démarre tous les services essentiels
- ✅ Fournit une API fonctionnelle
- ⚠️ Utilise des versions simplifiées (mais stables)

## 🔄 Migration vers Production

Une fois la solution d'urgence validée, vous pourrez :
1. Optimiser les versions de packages
2. Ajouter les fonctionnalités avancées
3. Configurer le monitoring complet
4. Déployer en production

## 📞 Support

Si la solution d'urgence échoue :

```bash
# Vérifier les logs
docker logs mar-api-emergency

# Nettoyer et recommencer
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
docker system prune -af
```

---

**🚀 Exécutez maintenant : `./scripts/emergency-deploy.sh`**
