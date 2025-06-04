# 🐳 Guide des Stratégies Docker - RAG Enterprise

## 📋 Vue d'ensemble

Ce projet supporte **3 stratégies de containerisation** selon vos besoins :

### 🎯 **1. MONOLITHE (Recommandé pour test/staging)**

**Fichiers utilisés :**
- `Dockerfile.staging`
- `docker-compose.staging.yml`

**Caractéristiques :**
- ✅ **1 seule image** pour tous les services
- ✅ **Simple à maintenir** et déboguer
- ✅ **Déploiement rapide**
- ⚠️ **Image plus lourde** (~800MB)
- ⚠️ **Scaling limité**

**Usage :**
```bash
# Lancement
./test-docker-strategies.sh monolith

# Ou directement
docker-compose -f docker-compose.staging.yml up -d
```

---

### 🔧 **2. MICROSERVICES (Pour production)**

**Fichiers utilisés :**
- `infrastructure/docker/api.Dockerfile` (~200MB)
- `infrastructure/docker/agents.Dockerfile` (~600MB) 
- `infrastructure/docker/scheduler.Dockerfile` (~150MB)
- `docker-compose.hybrid.yml`

**Caractéristiques :**
- ✅ **Images optimisées** par fonction
- ✅ **Scaling granulaire** (API vs Agents)
- ✅ **Ressources optimisées**
- ⚠️ **Plus complexe** à maintenir
- ⚠️ **Multiple builds** nécessaires

**Usage :**
```bash
# Lancement automatique
./test-docker-strategies.sh microservices

# Ou étape par étape
docker build -f infrastructure/docker/api.Dockerfile -t rag-api:latest .
docker build -f infrastructure/docker/agents.Dockerfile -t rag-agents:latest .
docker build -f infrastructure/docker/scheduler.Dockerfile -t rag-scheduler:latest .
docker-compose -f docker-compose.hybrid.yml up -d
```

---

### 🚀 **3. KUBERNETES (Pour cloud enterprise)**

**Fichiers utilisés :**
- `infrastructure/kubernetes/*.yaml`
- Images microservices

**Caractéristiques :**
- ✅ **Auto-scaling**
- ✅ **High Availability**
- ✅ **Rolling updates**
- ❌ **Requires K8s cluster**
- ❌ **Complex setup**

**Usage :**
```bash
# Appliquer les manifests
kubectl apply -f infrastructure/kubernetes/

# Ou avec Helm
helm install rag-system infrastructure/helm/
```

---

## 📊 Comparaison des performances

| Métrique | Monolithe | Microservices | Kubernetes |
|----------|-----------|---------------|------------|
| **Temps de build** | ~3 min | ~5 min | ~5 min + cluster |
| **RAM totale** | ~1GB | ~800MB | ~600MB |
| **Temps démarrage** | ~30s | ~45s | ~60s |
| **Scaling** | Manuel | Docker Swarm | Auto |
| **Maintenance** | ⭐⭐⭐ | ⭐⭐ | ⭐ |

---

## 🎯 Recommandations par phase

### **Phase Actuelle (Test/Dev) :** 
👉 **Utilisez MONOLITHE**
```bash
./test-docker-strategies.sh monolith
```

### **Phase Production (Première version) :**
👉 **Passez aux MICROSERVICES**
```bash
./test-docker-strategies.sh microservices
```

### **Phase Scale (Enterprise) :**
👉 **Migrez vers KUBERNETES**
```bash
kubectl apply -f infrastructure/kubernetes/
```

---

## 🛠️ Migration facile

Le projet est conçu pour une **migration progressive** :

1. **Actuellement** : Monolithe (docker-compose.staging.yml)
2. **Plus tard** : Microservices (docker-compose.hybrid.yml)  
3. **Future** : Kubernetes (infrastructure/kubernetes/)

**Aucun changement de code requis** - juste changement de déploiement !

---

## 🔍 Tests et validation

Pour chaque stratégie, testez avec :

```bash
# Santé des services
curl http://localhost:8000/health

# API fonctionnelle
curl http://localhost:8000/docs

# Agents actifs
docker-compose logs rag-agents

# Métriques
curl http://localhost:8000/metrics
```

---

## ❓ FAQ

**Q: Quelle stratégie pour commencer ?**
A: Monolithe - simple et efficace pour les tests.

**Q: Quand passer aux microservices ?**
A: En production, quand vous avez besoin de scaler différemment l'API vs les agents.

**Q: Kubernetes est-il nécessaire ?**
A: Seulement pour les déploiements enterprise avec haute disponibilité.

**Q: Les données sont-elles partagées ?**
A: Oui, toutes les stratégies utilisent les mêmes databases (PostgreSQL, Redis, Qdrant).
