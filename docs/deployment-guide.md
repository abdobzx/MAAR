# Guide de Déploiement - Système RAG Enterprise

## Vue d'ensemble

Ce guide fournit les instructions complètes pour déployer le système RAG multi-agent en production avec toutes les composantes de monitoring, sécurité et haute disponibilité.

## Prérequis

### Infrastructure
- Cluster Kubernetes 1.25+
- Minimum 3 nodes avec 16GB RAM et 4 CPU cores chacun
- Stockage persistant (100GB+ recommandé)
- Load balancer externe (AWS ALB, GCP LB, etc.)

### Outils requis
- kubectl 1.25+
- Helm 3.8+
- Docker 20.10+
- jq pour le parsing JSON

### Accès requis
- Registry Docker privé (optionnel)
- DNS management
- Certificats SSL/TLS

## Déploiement par Environnement

### 1. Environnement de Développement

```bash
# Cloner le repository
git clone <repository-url>
cd MAR

# Configuration de l'environnement local
cp .env.example .env.development
# Éditer .env.development avec vos valeurs

# Déploiement avec Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Vérification des services
docker-compose ps
docker-compose logs -f rag-api
```

### 2. Environnement de Staging

```bash
# Préparation du namespace
kubectl create namespace rag-staging
kubectl label namespace rag-staging name=rag-staging

# Configuration des secrets
kubectl create secret generic rag-secrets \
  --from-literal=database-url="postgresql://user:pass@postgres:5432/rag_db" \
  --from-literal=redis-url="redis://redis:6379/0" \
  --from-literal=openai-api-key="sk-..." \
  --from-literal=jwt-secret="your-jwt-secret" \
  -n rag-staging

# Déploiement avec Helm
helm upgrade --install rag-system ./infrastructure/helm \
  -n rag-staging \
  -f ./infrastructure/helm/values-staging.yaml

# Vérification du déploiement
kubectl get pods -n rag-staging
kubectl get services -n rag-staging
```

### 3. Environnement de Production

```bash
# Préparation du namespace avec sécurité renforcée
kubectl create namespace rag-production
kubectl label namespace rag-production name=rag-production

# Application des politiques de sécurité
kubectl apply -f infrastructure/security/rbac/ -n rag-production
kubectl apply -f infrastructure/security/policies/ -n rag-production

# Configuration des secrets sécurisés
kubectl create secret generic rag-secrets \
  --from-file=database-url=secrets/database-url.txt \
  --from-file=redis-url=secrets/redis-url.txt \
  --from-file=openai-api-key=secrets/openai-api-key.txt \
  --from-file=jwt-secret=secrets/jwt-secret.txt \
  -n rag-production

# Déploiement de production
helm upgrade --install rag-system ./infrastructure/helm \
  -n rag-production \
  -f ./infrastructure/helm/values-production.yaml \
  --wait --timeout=600s

# Configuration du monitoring
helm upgrade --install prometheus-stack prometheus-community/kube-prometheus-stack \
  -n rag-production \
  -f ./infrastructure/monitoring/prometheus-values.yaml

# Configuration ELK Stack
kubectl apply -f infrastructure/monitoring/elk/ -n rag-production
```

## Configuration des Services Externes

### Base de Données PostgreSQL

#### Option 1: Managed Database (Recommandé pour production)
```bash
# AWS RDS, GCP Cloud SQL, Azure Database
# Configuration via Terraform ou console cloud provider
```

#### Option 2: Déploiement dans Kubernetes
```bash
helm upgrade --install postgresql bitnami/postgresql \
  -n rag-production \
  --set auth.postgresPassword="secure-password" \
  --set auth.database="rag_db" \
  --set primary.persistence.size="100Gi" \
  --set primary.resources.requests.memory="2Gi" \
  --set primary.resources.requests.cpu="1000m"
```

### Vector Database (Qdrant)

```bash
helm upgrade --install qdrant ./infrastructure/helm/qdrant \
  -n rag-production \
  --set persistence.size="50Gi" \
  --set resources.requests.memory="4Gi" \
  --set resources.requests.cpu="2000m"
```

### Cache Redis

```bash
helm upgrade --install redis bitnami/redis \
  -n rag-production \
  --set auth.password="secure-redis-password" \
  --set master.persistence.size="10Gi" \
  --set replica.replicaCount=2
```

## Configuration du Monitoring

### Prometheus et Grafana

```bash
# Installation de Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n rag-production \
  --set grafana.adminPassword="secure-grafana-password" \
  --set prometheus.prometheusSpec.retention="30d" \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage="50Gi"

# Configuration des dashboards Grafana
kubectl create configmap grafana-dashboards \
  --from-file=infrastructure/monitoring/grafana/dashboards/ \
  -n rag-production

# Application des alertes personnalisées
kubectl apply -f infrastructure/monitoring/alerts/ -n rag-production
```

### ELK Stack pour les Logs

```bash
# Déploiement Elasticsearch
helm repo add elastic https://helm.elastic.co
helm upgrade --install elasticsearch elastic/elasticsearch \
  -n rag-production \
  --set replicas=3 \
  --set minimumMasterNodes=2 \
  --set resources.requests.memory="4Gi" \
  --set resources.requests.cpu="1000m" \
  --set volumeClaimTemplate.resources.requests.storage="100Gi"

# Déploiement Kibana
helm upgrade --install kibana elastic/kibana \
  -n rag-production \
  --set resources.requests.memory="2Gi"

# Déploiement Logstash
helm upgrade --install logstash elastic/logstash \
  -n rag-production \
  --set-file logstashConfig.logstash\\.yml=infrastructure/monitoring/elk/logstash/config/logstash.yml \
  --set-file logstashPipeline.logstash\\.conf=infrastructure/monitoring/elk/logstash/pipeline/logstash.conf

# Déploiement Filebeat
kubectl apply -f infrastructure/monitoring/elk/filebeat/ -n rag-production
```

## Configuration SSL/TLS

### Cert-Manager pour les certificats automatiques

```bash
# Installation de cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Configuration Let's Encrypt issuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@your-domain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Tests de Déploiement

### Tests de Santé

```bash
# Script de vérification automatique
./scripts/health-check.sh

# Tests manuels
kubectl get pods -n rag-production
kubectl get services -n rag-production
kubectl get ingress -n rag-production

# Test de l'API
curl -H "Authorization: Bearer <token>" https://api.rag-system.com/health
```

### Tests de Performance

```bash
# Lancement des tests de charge
cd tests/load
python -m locust -f locustfile.py --host=https://api.rag-system.com

# Tests de performance avec k6
k6 run performance-test.js
```

## Maintenance et Sauvegarde

### Sauvegarde des Données

```bash
# Script de sauvegarde automatique
./scripts/backup.sh

# Sauvegarde manuelle de la base de données
kubectl exec -n rag-production deployment/postgres -- pg_dump -U postgres rag_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Sauvegarde des vecteurs Qdrant
kubectl exec -n rag-production deployment/qdrant -- tar czf /tmp/qdrant_backup.tar.gz /qdrant/storage
kubectl cp rag-production/qdrant-pod:/tmp/qdrant_backup.tar.gz ./qdrant_backup_$(date +%Y%m%d_%H%M%S).tar.gz
```

### Mise à jour

```bash
# Mise à jour rolling update
helm upgrade rag-system ./infrastructure/helm \
  -n rag-production \
  -f ./infrastructure/helm/values-production.yaml \
  --set image.tag="v1.1.0"

# Vérification du rollout
kubectl rollout status deployment/rag-api -n rag-production
kubectl rollout status deployment/rag-celery -n rag-production
```

## Troubleshooting

### Problèmes Courants

#### 1. Pods qui ne démarrent pas
```bash
kubectl describe pod <pod-name> -n rag-production
kubectl logs <pod-name> -n rag-production --previous
```

#### 2. Problèmes de connectivité base de données
```bash
kubectl exec -it deployment/rag-api -n rag-production -- /bin/bash
# Test de connexion depuis le pod
pg_isready -h postgres -p 5432
```

#### 3. Problèmes de performance
```bash
# Monitoring des ressources
kubectl top pods -n rag-production
kubectl top nodes

# Analyse des métriques
curl http://prometheus:9090/api/v1/query?query=up
```

### Logs et Diagnostics

```bash
# Centralisation des logs
kubectl logs -f deployment/rag-api -n rag-production
kubectl logs -f deployment/rag-celery -n rag-production

# Accès aux métriques
kubectl port-forward service/prometheus 9090:9090 -n rag-production
kubectl port-forward service/grafana 3000:80 -n rag-production
```

## Sécurité en Production

### Hardening du Cluster

1. **Network Policies** : Appliquées automatiquement avec le déploiement
2. **RBAC** : Permissions minimales pour chaque service
3. **Pod Security Policies** : Restrictions sur les conteneurs
4. **Secrets Management** : Chiffrement au repos et en transit

### Monitoring de Sécurité

```bash
# Audit des permissions
kubectl auth can-i --list --as=system:serviceaccount:rag-production:rag-api-service-account -n rag-production

# Scan de vulnérabilités
trivy image rag-system:latest
```

## Support et Escalade

### Contacts d'Urgence
- **Équipe DevOps** : devops@company.com
- **Équipe Sécurité** : security@company.com
- **Astreinte 24/7** : +33 X XX XX XX XX

### Procédures d'Escalade
1. **P1 (Critique)** : Service indisponible → Escalade immédiate
2. **P2 (Majeur)** : Dégradation performance → Escalade sous 2h
3. **P3 (Mineur)** : Problèmes non critiques → Escalade sous 24h

### Runbooks
- [Incident Response](./runbooks/incident-response.md)
- [Performance Issues](./runbooks/performance-issues.md)
- [Security Incidents](./runbooks/security-incidents.md)
