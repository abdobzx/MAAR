# 🚀 Guide DevOps - Mise en Production du Système RAG Enterprise

## 📋 Étapes Prioritaires pour la Production

### **ÉTAPE 1 : Validation Locale (ACTUELLE)**
```bash
# 1. Validation du système en local
cd /Users/abderrahman/Documents/MAR
./scripts/initial-deployment.sh local

# 2. Tests de base
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### **ÉTAPE 2 : Configuration du Serveur**

#### **Option A : Serveur Unique (Docker Compose)**
```bash
# 1. Préparer le serveur
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose git nginx certbot -y

# 2. Cloner le projet
git clone <your-repo> /opt/rag-system
cd /opt/rag-system

# 3. Configuration production
cp .env.production.example .env.production
# Éditer .env.production avec vos vraies valeurs

# 4. Déploiement
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

#### **Option B : Cluster Kubernetes (Recommandé)**
```bash
# 1. Configurer kubectl vers votre cluster
kubectl config current-context

# 2. Déploiement staging
./scripts/initial-deployment.sh staging

# 3. Déploiement production (après validation)
./scripts/initial-deployment.sh production
```

### **ÉTAPE 3 : Configuration CI/CD**

#### **GitHub Actions (Inclus)**
- Le repository contient déjà `.github/workflows/ci-cd.yml`
- Configurez les secrets GitHub :
  - `DOCKER_REGISTRY_USERNAME`
  - `DOCKER_REGISTRY_PASSWORD`
  - `KUBE_CONFIG_STAGING`
  - `KUBE_CONFIG_PRODUCTION`
  - `SOTHEMAAI_API_KEY`

#### **Pipeline de Déploiement**
1. **Push sur `develop`** → Déploie sur staging
2. **Push sur `main`** → Déploie sur production
3. **Tests automatiques** à chaque étape
4. **Rollback automatique** en cas d'échec

### **ÉTAPE 4 : Monitoring et Observabilité**

#### **Déploiement du Stack de Monitoring**
```bash
# Prometheus + Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# ELK Stack
kubectl apply -f infrastructure/monitoring/elk/

# Accès aux dashboards
kubectl port-forward svc/grafana 3000:80 -n monitoring
# Grafana: http://localhost:3000 (admin/prom-operator)
```

### **ÉTAPE 5 : Sécurité**

#### **Certificats SSL/TLS**
```bash
# Avec cert-manager (Kubernetes)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Avec Let's Encrypt (serveur unique)
sudo certbot --nginx -d api.votre-domaine.com
```

#### **Secrets Management**
```bash
# Kubernetes Secrets
kubectl create secret generic rag-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=sothemaai-api-key="your-key" \
  --namespace=rag-production

# Ou utiliser un gestionnaire de secrets externe (Vault, AWS Secrets Manager)
```

---

## 🎯 Plan d'Action Immédiat

### **AUJOURD'HUI** ⭐
1. **Tester en local** : `./scripts/initial-deployment.sh local`
2. **Valider les services** : Vérifier que tout fonctionne
3. **Préparer la configuration production** : Éditer `.env.production`

### **CETTE SEMAINE**
1. **Préparer le serveur de staging**
2. **Configurer le CI/CD** avec GitHub Actions
3. **Déployer sur staging** : `./scripts/initial-deployment.sh staging`
4. **Tests d'intégration** complets

### **SEMAINE SUIVANTE**
1. **Configuration du monitoring**
2. **Sécurisation** (SSL, secrets, RBAC)
3. **Déploiement production**
4. **Documentation** des runbooks

---

## 📊 Architecture de Déploiement Recommandée

### **Environnements**
- **Local** : Docker Compose (développement)
- **Staging** : Kubernetes cluster (tests pré-production)
- **Production** : Kubernetes cluster (haute disponibilité)

### **Services de Base**
- **API RAG** : 3 replicas minimum
- **Celery Workers** : 4 replicas
- **PostgreSQL** : Cluster HA ou service managé
- **Redis** : Cluster HA
- **Qdrant** : Persistance + backup
- **Nginx** : LoadBalancer + SSL termination

### **Monitoring Stack**
- **Prometheus** : Métriques
- **Grafana** : Dashboards
- **Jaeger** : Tracing distribué
- **ELK Stack** : Logs centralisés
- **Alertmanager** : Notifications

---

## 🔐 Check-list Sécurité Production

- [ ] Certificats SSL/TLS configurés
- [ ] Secrets chiffrés (pas de mots de passe en clair)
- [ ] RBAC Kubernetes configuré
- [ ] Network Policies appliquées
- [ ] Images Docker scannées (vulnérabilités)
- [ ] Backup automatisé configuré
- [ ] Monitoring et alertes actifs
- [ ] Plan de récupération documenté

---

## 📞 Support et Maintenance

### **Commandes Utiles**
```bash
# Status des services
kubectl get pods -n rag-production
docker-compose ps

# Logs en temps réel
kubectl logs -f deployment/rag-api -n rag-production
docker-compose logs -f rag_api

# Mise à jour
helm upgrade rag-system ./infrastructure/helm -n rag-production
docker-compose up -d --build

# Rollback
helm rollback rag-system -n rag-production
docker-compose down && docker-compose up -d
```

### **Métriques Importantes**
- **API Response Time** : < 500ms (95e percentile)
- **Database Connections** : < 80% du pool
- **Memory Usage** : < 80% par pod
- **Error Rate** : < 1%
- **Uptime** : > 99.9%
