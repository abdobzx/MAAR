# Runbook - Problèmes de Performance

## Diagnostic de Performance

### 1. Identification des Symptômes

#### Latence Élevée (> 2s)
```bash
# Vérification des métriques de latence
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job='rag-api'}[5m])) by (le))"

# Analyse des logs de performance
kubectl logs deployment/rag-api -n rag-production | grep "slow_query\|high_latency" | tail -20
```

#### Throughput Faible (< 100 req/s)
```bash
# Métriques de débit
curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(http_requests_total{job='rag-api'}[5m]))"

# Statut des workers Celery
kubectl exec deployment/rag-celery -n rag-production -- celery -A core.celery inspect active
```

#### Taux d'Erreur Élevé (> 1%)
```bash
# Taux d'erreur global
curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(http_requests_total{job='rag-api',status=~'5..'}[5m])) / sum(rate(http_requests_total{job='rag-api'}[5m]))"

# Top des erreurs
kubectl logs deployment/rag-api -n rag-production | grep ERROR | cut -d' ' -f3- | sort | uniq -c | sort -nr | head -10
```

### 2. Analyse par Composant

#### API Gateway / Load Balancer
```bash
# Métriques Nginx
kubectl exec deployment/nginx -n rag-production -- curl -s localhost/nginx_status

# Connexions actives
kubectl exec deployment/nginx -n rag-production -- netstat -an | grep :80 | wc -l

# Configuration Nginx
kubectl get configmap nginx-config -n rag-production -o yaml
```

#### Application Layer
```bash
# Utilisation CPU/Mémoire des pods
kubectl top pods -n rag-production | grep rag-api

# Profiling de l'application
kubectl exec -it deployment/rag-api -n rag-production -- python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'CPU: {process.cpu_percent()}%')
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
print(f'Threads: {process.num_threads()}')
"

# Traces distribuées avec Jaeger
# Accéder à http://jaeger:16686
# Rechercher les traces avec latence > 2s
```

#### Base de Données
```bash
# Connexions actives
kubectl exec deployment/postgres -n rag-production -- psql -U postgres -c "
SELECT count(*) as active_connections, state 
FROM pg_stat_activity 
WHERE state IS NOT NULL 
GROUP BY state;"

# Requêtes lentes
kubectl exec deployment/postgres -n rag-production -- psql -U postgres -c "
SELECT query, mean_exec_time, calls, total_exec_time
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;"

# Verrous et blocages
kubectl exec deployment/postgres -n rag-production -- psql -U postgres -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;"
```

#### Cache Redis
```bash
# Métriques Redis
kubectl exec deployment/redis -n rag-production -- redis-cli info memory
kubectl exec deployment/redis -n rag-production -- redis-cli info stats

# Hit ratio du cache
kubectl exec deployment/redis -n rag-production -- redis-cli info stats | grep keyspace
```

#### Vector Database (Qdrant)
```bash
# Statut des collections
kubectl exec deployment/qdrant -n rag-production -- curl -s localhost:6333/collections

# Métriques de performance
kubectl exec deployment/qdrant -n rag-production -- curl -s localhost:6333/metrics
```

### 3. Actions d'Optimisation

#### Scaling Horizontal
```bash
# Augmenter le nombre de replicas API
kubectl scale deployment rag-api --replicas=5 -n rag-production

# Augmenter le nombre de workers Celery
kubectl scale deployment rag-celery --replicas=3 -n rag-production

# Auto-scaling basé sur CPU
kubectl patch hpa rag-api-hpa -n rag-production -p '{"spec":{"minReplicas":3,"maxReplicas":10}}'
```

#### Scaling Vertical
```bash
# Augmenter les ressources temporairement
kubectl patch deployment rag-api -n rag-production -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "rag-api",
          "resources": {
            "limits": {"memory": "4Gi", "cpu": "2000m"},
            "requests": {"memory": "2Gi", "cpu": "1000m"}
          }
        }]
      }
    }
  }
}'
```

#### Optimisation Base de Données
```bash
# Analyse et optimisation des requêtes
kubectl exec deployment/postgres -n rag-production -- psql -U postgres -c "
-- Identifier les requêtes à optimiser
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM documents WHERE content LIKE '%search%';

-- Créer des index manquants
CREATE INDEX CONCURRENTLY idx_documents_created_at ON documents(created_at);
CREATE INDEX CONCURRENTLY idx_embeddings_vector_gin ON embeddings USING gin(vector);
"

# Maintenance de la base
kubectl exec deployment/postgres -n rag-production -- psql -U postgres -c "
VACUUM (ANALYZE, VERBOSE) documents;
REINDEX INDEX CONCURRENTLY idx_documents_content;
"
```

#### Optimisation Cache
```bash
# Ajustement des TTL
kubectl exec deployment/redis -n rag-production -- redis-cli config set maxmemory-policy allkeys-lru

# Préchargement du cache
kubectl exec deployment/rag-api -n rag-production -- python -c "
from core.cache import warm_cache
warm_cache(['popular_queries', 'user_preferences'])
"
```

#### Optimisation Applicative
```bash
# Configuration de pool de connexions
kubectl patch configmap rag-config -n rag-production --patch '{
  "data": {
    "DATABASE_POOL_SIZE": "20",
    "DATABASE_MAX_OVERFLOW": "10",
    "REDIS_POOL_SIZE": "50"
  }
}'

# Ajustement des timeouts
kubectl patch configmap rag-config -n rag-production --patch '{
  "data": {
    "HTTP_TIMEOUT": "30",
    "EMBEDDING_TIMEOUT": "60",
    "VECTOR_SEARCH_TIMEOUT": "10"
  }
}'
```

### 4. Monitoring Continu

#### Alertes de Performance
```yaml
# Ajouter à prometheus-rules
- alert: HighLatency
  expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 2
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "API latency is high"

- alert: LowThroughput  
  expr: sum(rate(http_requests_total[5m])) < 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "API throughput is low"
```

#### Dashboard de Performance
```bash
# Grafana queries clés
# P95 Latency: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
# RPS: sum(rate(http_requests_total[5m]))
# Error Rate: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
# CPU Usage: sum(rate(container_cpu_usage_seconds_total[5m])) by (pod)
# Memory Usage: sum(container_memory_working_set_bytes) by (pod)
```

### 5. Tests de Performance

#### Baseline Performance Test
```bash
# Lancer un test de charge pour établir la baseline
cd tests/load
python -m locust -f locustfile.py --host=https://api.rag-system.com \
  --users=100 --spawn-rate=10 --run-time=300s --html=baseline_report.html
```

#### Stress Testing
```bash
# Test de montée en charge progressive
python -m locust -f locustfile.py --host=https://api.rag-system.com \
  --users=500 --spawn-rate=20 --run-time=600s --html=stress_report.html
```

## Métriques de Performance Cibles

| Métrique | Cible | Seuil d'Alerte |
|----------|-------|----------------|
| P95 Latency | < 1s | > 2s |
| P99 Latency | < 2s | > 5s |
| Throughput | > 1000 RPS | < 100 RPS |
| Error Rate | < 0.1% | > 1% |
| CPU Usage | < 70% | > 90% |
| Memory Usage | < 80% | > 95% |
| DB Connections | < 80% max | > 95% max |
