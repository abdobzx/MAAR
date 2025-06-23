# Guide de Maintenance Opérationnelle - Système RAG Enterprise

## Vue d'ensemble

Ce guide détaille toutes les procédures de maintenance opérationnelle pour maintenir le système RAG Enterprise en fonctionnement optimal. Il couvre les tâches quotidiennes, hebdomadaires, mensuelles et les procédures d'urgence.

## Tâches de Maintenance Quotidiennes

### 1. Vérification de l'État du Système

#### Health Check Automatisé
```bash
# Exécution du script de santé global
./scripts/monitoring/health-check.sh

# Vérification spécifique par composant
kubectl get pods -n enterprise-rag
kubectl get services -n enterprise-rag
kubectl get ingress -n enterprise-rag
```

#### Métriques Critiques à Surveiller
- **CPU Usage** : < 80% sur tous les nœuds
- **Memory Usage** : < 85% sur tous les pods
- **Disk Usage** : < 90% sur tous les volumes
- **API Response Time** : < 500ms moyenne
- **Queue Length** : < 100 tâches en attente

#### Points de Contrôle
1. **Services Core** : API, Celery, Base de données
2. **Services Support** : Redis, Qdrant, MinIO
3. **Monitoring** : Prometheus, Grafana, Jaeger
4. **Sécurité** : Certificats, authentification

### 2. Surveillance des Logs

#### Centralisation ELK
```bash
# Accès aux dashboards Kibana
kubectl port-forward service/kibana 5601:5601 -n enterprise-rag

# Recherche d'erreurs critiques
curl -X GET "localhost:9200/logstash-*/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "must": [
        {"range": {"@timestamp": {"gte": "now-1d"}}},
        {"terms": {"level": ["ERROR", "CRITICAL"]}}
      ]
    }
  },
  "sort": [{"@timestamp": {"order": "desc"}}],
  "size": 100
}'
```

#### Alertes à Surveiller
- **Erreurs d'Application** : Exceptions non gérées
- **Erreurs de Base de Données** : Connexions échouées
- **Erreurs de Queue** : Tâches qui échouent
- **Erreurs de Sécurité** : Tentatives d'authentification

### 3. Surveillance des Métriques Business

#### Indicateurs Clés
```bash
# Via l'API de métriques
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.rag-system.com/admin/metrics/daily"

# Métriques Prometheus
curl "http://prometheus:9090/api/v1/query?query=rag_requests_total"
curl "http://prometheus:9090/api/v1/query?query=rag_response_time_seconds"
```

#### KPIs à Vérifier
- **Requêtes par heure** : Tendance d'utilisation
- **Temps de réponse moyen** : Performance utilisateur
- **Taux d'erreur** : Qualité du service
- **Documents traités** : Productivité de traitement

## Tâches de Maintenance Hebdomadaires

### 1. Nettoyage des Données

#### Nettoyage des Logs
```bash
# Suppression des logs anciens (> 30 jours)
kubectl exec deployment/elasticsearch -n enterprise-rag -- \
  curl -X DELETE "localhost:9200/logstash-$(date -d '30 days ago' +%Y.%m.%d)"

# Nettoyage des logs d'application
find /var/log/rag/ -name "*.log" -mtime +30 -delete

# Rotation des logs Nginx
kubectl exec deployment/nginx -n enterprise-rag -- \
  logrotate /etc/logrotate.conf
```

#### Nettoyage du Cache
```bash
# Analyse de l'utilisation Redis
kubectl exec deployment/redis -n enterprise-rag -- redis-cli info memory

# Nettoyage des clés expirées
kubectl exec deployment/redis -n enterprise-rag -- redis-cli --scan \
  --pattern "temp:*" | xargs -I {} kubectl exec deployment/redis -n enterprise-rag -- redis-cli del {}

# Optimisation de la mémoire Redis
kubectl exec deployment/redis -n enterprise-rag -- redis-cli memory purge
```

### 2. Optimisation des Performances

#### Analyse des Requêtes Lentes
```bash
# PostgreSQL - Requêtes lentes
kubectl exec deployment/postgres -n enterprise-rag -- psql -U rag_user -d rag_database -c "
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
WHERE mean_time > 1000 
ORDER BY mean_time DESC 
LIMIT 10;"

# Qdrant - Performance des collections
kubectl exec deployment/qdrant -n enterprise-rag -- \
  curl "localhost:6333/collections/enterprise_rag/cluster"
```

#### Optimisation de la Base de Données
```bash
# Analyse et maintenance PostgreSQL
kubectl exec deployment/postgres -n enterprise-rag -- psql -U rag_user -d rag_database -c "
-- Analyse des tables
ANALYZE;

-- Statistiques de performance
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;

-- Index non utilisés
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0;
"
```

### 3. Mise à Jour des Certificats

#### Vérification des Certificats
```bash
# Vérification des dates d'expiration
kubectl get certificates -n enterprise-rag -o custom-columns="NAME:.metadata.name,READY:.status.conditions[?(@.type=='Ready')].status,EXPIRY:.status.notAfter"

# Vérification manuelle
echo | openssl s_client -servername rag-system.com -connect rag-system.com:443 2>/dev/null | openssl x509 -noout -dates
```

#### Renouvellement Automatique (Let's Encrypt)
```bash
# Vérification du cert-manager
kubectl get pods -n cert-manager
kubectl logs -n cert-manager deployment/cert-manager

# Force le renouvellement si nécessaire
kubectl delete certificate rag-tls -n enterprise-rag
# Le cert-manager va automatiquement recréer le certificat
```

## Tâches de Maintenance Mensuelles

### 1. Sauvegarde Complète

#### Exécution de la Sauvegarde
```bash
# Sauvegarde automatisée complète
./scripts/backup/backup.sh --full --environment production

# Vérification de l'intégrité des sauvegardes
./scripts/backup/verify-backup.sh --latest

# Test de restauration (sur environnement de test)
./scripts/backup/restore.sh --backup-date 2024-01-15 --environment staging
```

#### Archivage
```bash
# Archive des sauvegardes anciennes (> 90 jours)
find /backups/rag-system -name "*.tar.gz" -mtime +90 -exec mv {} /archives/ \;

# Compression des archives
tar -czf /archives/rag-backup-$(date +%Y%m).tar.gz /archives/backup-*
```

### 2. Audit de Sécurité

#### Scan de Vulnérabilités
```bash
# Scan des images Docker
trivy image --exit-code 1 --severity HIGH,CRITICAL rag-system:latest

# Scan du cluster Kubernetes
kube-bench run --targets node,policies,managedservices

# Audit des permissions RBAC
kubectl auth can-i --list --as=system:serviceaccount:enterprise-rag:default
```

#### Audit des Accès
```bash
# Analyse des logs d'authentification
kubectl logs -n enterprise-rag deployment/keycloak | grep "LOGIN\|LOGOUT\|FAILED"

# Utilisateurs actifs
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://auth.rag-system.com/admin/realms/rag-realm/users?max=1000" | \
  jq '.[] | select(.enabled == true) | {username, lastAccess}'
```

### 3. Analyse des Performances

#### Rapport de Performance Mensuel
```bash
# Génération du rapport automatisé
python scripts/monitoring/generate-monthly-report.py --month $(date +%Y-%m)

# Métriques d'utilisation
curl "http://prometheus:9090/api/v1/query_range?query=rag_requests_total&start=$(date -d '1 month ago' +%s)&end=$(date +%s)&step=3600"

# Analyse des tendances
python scripts/analytics/trend-analysis.py --period monthly
```

#### Recommandations d'Optimisation
```bash
# Utilisation des ressources
kubectl top nodes
kubectl top pods -n enterprise-rag --sort-by=memory

# Recommandations de scaling
python scripts/monitoring/resource-recommendations.py
```

## Tâches de Maintenance Trimestrielles

### 1. Mise à Jour Majeure du Système

#### Planification de la Mise à Jour
```bash
# Vérification des versions disponibles
helm repo update
helm search repo enterprise-rag

# Test en staging
helm upgrade --install rag-system ./infrastructure/helm \
  -n enterprise-rag-staging \
  --set image.tag=v1.2.0 \
  --dry-run

# Backup avant mise à jour
./scripts/backup/backup.sh --full --pre-upgrade
```

#### Mise à Jour Progressive
```bash
# Rolling update avec surveillance
helm upgrade rag-system ./infrastructure/helm \
  -n enterprise-rag \
  --set image.tag=v1.2.0 \
  --wait --timeout=600s

# Validation post-mise à jour
./scripts/monitoring/health-check.sh --comprehensive
./scripts/testing/smoke-tests.sh
```

### 2. Optimisation de l'Infrastructure

#### Révision de l'Architecture
- **Analyse de capacité** : Projection des besoins
- **Optimisation des coûts** : Révision des ressources
- **Amélioration des performances** : Bottlenecks identifiés
- **Sécurité** : Mise à jour des politiques

#### Tuning des Performances
```bash
# Optimisation PostgreSQL
kubectl exec deployment/postgres -n enterprise-rag -- psql -U rag_user -d rag_database -c "
-- Configuration optimisée
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
SELECT pg_reload_conf();
"

# Optimisation Qdrant
kubectl patch deployment qdrant -n enterprise-rag --patch '
spec:
  template:
    spec:
      containers:
      - name: qdrant
        env:
        - name: QDRANT__STORAGE__OPTIMIZERS__DELETED_THRESHOLD
          value: "0.2"
        - name: QDRANT__STORAGE__OPTIMIZERS__VACUUM_MIN_VECTOR_NUMBER
          value: "1000"
'
```

## Procédures d'Urgence

### 1. Panne Majeure du Système

#### Diagnostic Rapide
```bash
# Vérification globale du cluster
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running

# Vérification des ressources critiques
kubectl describe nodes | grep -A5 "Conditions:"
kubectl top nodes
```

#### Procédure de Récupération
```bash
# 1. Isolation du problème
kubectl cordon <node-with-issues>

# 2. Redémarrage des services critiques
kubectl rollout restart deployment/rag-api -n enterprise-rag
kubectl rollout restart deployment/rag-celery -n enterprise-rag

# 3. Vérification de la récupération
kubectl rollout status deployment/rag-api -n enterprise-rag
./scripts/monitoring/health-check.sh
```

### 2. Corruption de Données

#### Procédure de Restauration
```bash
# 1. Arrêt des écritures
kubectl scale deployment rag-api --replicas=0 -n enterprise-rag

# 2. Restauration depuis backup
./scripts/backup/restore.sh --backup-date $(date -d '1 day ago' +%Y-%m-%d)

# 3. Validation de l'intégrité
python scripts/database/integrity-check.py

# 4. Redémarrage du service
kubectl scale deployment rag-api --replicas=3 -n enterprise-rag
```

### 3. Surcharge du Système

#### Mitigation Immédiate
```bash
# Scaling horizontal automatique
kubectl autoscale deployment rag-api --min=3 --max=10 --cpu-percent=70 -n enterprise-rag

# Limitation du trafic (Nginx)
kubectl patch configmap nginx-config -n enterprise-rag --patch '
data:
  rate-limit.conf: |
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
'

# Redémarrage Nginx pour appliquer
kubectl rollout restart deployment/nginx -n enterprise-rag
```

## Surveillance Continue

### 1. Dashboards de Monitoring

#### Accès aux Interfaces
```bash
# Grafana
kubectl port-forward service/grafana 3000:80 -n enterprise-rag
# Accès: http://localhost:3000

# Prometheus
kubectl port-forward service/prometheus 9090:9090 -n enterprise-rag
# Accès: http://localhost:9090

# Kibana
kubectl port-forward service/kibana 5601:5601 -n enterprise-rag
# Accès: http://localhost:5601
```

#### Dashboards Critiques
1. **RAG Overview** : Vue d'ensemble du système
2. **Infrastructure** : Métriques des nœuds et pods
3. **Application Performance** : Métriques applicatives
4. **Security Monitoring** : Événements de sécurité

### 2. Alertes Automatisées

#### Configuration des Alertes
Les alertes sont configurées dans `infrastructure/monitoring/alerts/advanced-alerts.yml` :

- **Downtime** : Service indisponible > 1 minute
- **High CPU** : Utilisation > 80% pendant 5 minutes
- **High Memory** : Utilisation > 85% pendant 5 minutes
- **Disk Full** : Espace disque > 90%
- **High Error Rate** : Taux d'erreur > 5% pendant 2 minutes

#### Canaux de Notification
- **Slack** : Alertes temps réel pour l'équipe DevOps
- **Email** : Résumés quotidiens et alertes critiques
- **PagerDuty** : Escalade pour les alertes critiques
- **StatusPage** : Communication publique des incidents

### 3. Métriques Business

#### KPIs de Performance
- **Disponibilité** : 99.9% (SLA target)
- **Temps de réponse** : < 500ms moyenne
- **Throughput** : Requêtes par seconde
- **Satisfaction utilisateur** : Score de feedback

#### Métriques d'Usage
- **Utilisateurs actifs** : DAU/MAU
- **Documents traités** : Par jour/semaine
- **Requêtes populaires** : Top des questions
- **Adoption fonctionnalités** : Utilisation par feature

## Documentation et Formation

### 1. Mise à Jour de la Documentation

#### Procédure Mensuelle
1. **Révision** : Vérification de l'exactitude
2. **Mise à jour** : Nouvelles fonctionnalités et changements
3. **Validation** : Test des procédures documentées
4. **Publication** : Mise à disposition des équipes

#### Documents à Maintenir
- Guides de déploiement
- Runbooks d'incidents
- Procédures de maintenance
- Guide utilisateur
- Documentation API

### 2. Formation des Équipes

#### Formation Continue
- **Sessions mensuelles** : Nouvelles fonctionnalités
- **Formation incident** : Simulation d'urgences
- **Certification** : Validation des compétences
- **Veille technologique** : Évolutions de l'écosystème

## Amélioration Continue

### 1. Processus d'Optimisation

#### Cycle d'Amélioration
1. **Mesure** : Collecte des métriques
2. **Analyse** : Identification des opportunités
3. **Plan** : Définition des améliorations
4. **Exécution** : Mise en œuvre des changements
5. **Validation** : Mesure de l'impact

#### Revues Régulières
- **Weekly** : Incidents et problèmes
- **Monthly** : Performance et optimisations
- **Quarterly** : Architecture et stratégie
- **Annually** : Vision et roadmap

### 2. Innovation et Évolution

#### Veille Technologique
- **Nouveaux modèles LLM** : Évaluation et tests
- **Outils DevOps** : Amélioration des processus
- **Sécurité** : Nouvelles menaces et protections
- **Performance** : Optimisations infrastructure

#### Roadmap d'Évolution
- **Q1** : Améliorations performance
- **Q2** : Nouvelles fonctionnalités utilisateur
- **Q3** : Intégrations et APIs
- **Q4** : Optimisations infrastructure

---

*Ce guide est maintenu par l'équipe DevOps. Dernière mise à jour : Décembre 2024*
