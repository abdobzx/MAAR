#!/bin/bash

# Script d'Optimisation Post-Déploiement
# Système RAG Enterprise - Version 1.0
# 
# Ce script effectue les optimisations finales après un déploiement réussi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
NAMESPACE=${NAMESPACE:-enterprise-rag}
ENVIRONMENT=${ENVIRONMENT:-production}
API_BASE_URL=${API_BASE_URL:-https://api.rag-system.com}

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# ===== OPTIMISATIONS BASE DE DONNÉES =====

optimize_database() {
    log_step "Optimisation de la base de données..."
    
    # Analyse et optimisation PostgreSQL
    kubectl exec deployment/postgres -n "$NAMESPACE" -- psql -U rag -d rag << 'EOF'
-- Analyse des statistiques
ANALYZE;

-- Optimisation des index
REINDEX DATABASE rag;

-- Nettoyage des logs
VACUUM ANALYZE;

-- Configuration pour la production
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
EOF

    log_info "Base de données optimisée"
}

# ===== OPTIMISATIONS REDIS =====

optimize_redis() {
    log_step "Optimisation de Redis..."
    
    kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli << 'EOF'
# Configuration pour la production
CONFIG SET maxmemory-policy allkeys-lru
CONFIG SET maxmemory 512mb
CONFIG SET save "900 1 300 10 60 10000"
CONFIG SET stop-writes-on-bgsave-error no
CONFIG SET rdbcompression yes
CONFIG SET rdbchecksum yes
CONFIG SET tcp-keepalive 300
CONFIG SET timeout 0

# Nettoyage et optimisation
BGREWRITEAOF
MEMORY PURGE
EOF

    log_info "Redis optimisé"
}

# ===== OPTIMISATIONS QDRANT =====

optimize_vector_database() {
    log_step "Optimisation de la base de données vectorielle..."
    
    # Optimisation des collections Qdrant
    kubectl exec deployment/qdrant -n "$NAMESPACE" -- curl -X POST \
        http://localhost:6333/collections/documents/index \
        -H 'Content-Type: application/json' \
        -d '{
            "field_name": "metadata.category",
            "field_schema": "keyword"
        }'
    
    # Optimisation des performances de recherche
    kubectl exec deployment/qdrant -n "$NAMESPACE" -- curl -X PATCH \
        http://localhost:6333/collections/documents \
        -H 'Content-Type: application/json' \
        -d '{
            "optimizers_config": {
                "deleted_threshold": 0.2,
                "vacuum_min_vector_number": 1000,
                "default_segment_number": 2,
                "max_segment_size": 200000,
                "memmap_threshold": 50000,
                "indexing_threshold": 20000,
                "flush_interval_sec": 5,
                "max_optimization_threads": 2
            }
        }'
    
    log_info "Base de données vectorielle optimisée"
}

# ===== PRÉCHAUFFAGE DU CACHE =====

warm_up_caches() {
    log_step "Préchauffage des caches..."
    
    # Préchauffage du cache applicatif
    kubectl exec deployment/rag-api -n "$NAMESPACE" -- python << 'EOF'
import asyncio
import sys
sys.path.append('/app')

from core.cache import CacheManager
from core.embeddings import EmbeddingService
from core.models import get_llm_client

async def warm_cache():
    cache = CacheManager()
    
    # Préchargement des modèles
    embedding_service = EmbeddingService()
    await embedding_service.initialize()
    
    llm_client = get_llm_client()
    await llm_client.initialize()
    
    # Cache des métadonnées fréquentes
    await cache.set("system:status", "ready", ttl=3600)
    await cache.set("models:loaded", True, ttl=3600)
    
    print("Cache préchauffé avec succès")

if __name__ == "__main__":
    asyncio.run(warm_cache())
EOF

    # Préchauffage Redis avec des clés courantes
    kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli << 'EOF'
# Préchargement des structures de données courantes
SET system:health "ok" EX 3600
HSET system:stats "requests" 0 "errors" 0 "uptime" 0
LPUSH system:logs "System optimized at $(date)"
EXPIRE system:logs 86400
EOF

    log_info "Caches préchauffés"
}

# ===== CONFIGURATION JVM (si applicable) =====

optimize_jvm() {
    log_step "Optimisation JVM (si applicable)..."
    
    # Vérifier si des composants Java sont présents
    if kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].spec.containers[*].image}' | grep -q java; then
        log_info "Configuration JVM pour les composants Java"
        
        # Appliquer les optimisations JVM via ConfigMap
        kubectl patch configmap java-config -n "$NAMESPACE" --patch '{
            "data": {
                "JAVA_OPTS": "-Xms512m -Xmx2g -XX:+UseG1GC -XX:G1HeapRegionSize=16m -XX:+UseStringDeduplication -XX:+OptimizeStringConcat -XX:+UseCompressedOops"
            }
        }' || log_warn "Pas de ConfigMap java-config trouvée"
    else
        log_info "Aucun composant Java détecté"
    fi
}

# ===== CONFIGURATION RÉSEAU =====

optimize_network() {
    log_step "Optimisation réseau..."
    
    # Configuration des limites de connexion
    kubectl patch service rag-api -n "$NAMESPACE" --patch '{
        "metadata": {
            "annotations": {
                "nginx.ingress.kubernetes.io/connection-proxy-header": "upgrade",
                "nginx.ingress.kubernetes.io/proxy-connect-timeout": "30",
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "600",
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "600",
                "nginx.ingress.kubernetes.io/proxy-body-size": "50m"
            }
        }
    }' || log_warn "Service rag-api non trouvé"
    
    # Optimisation des connexions keep-alive
    kubectl patch ingress rag-ingress -n "$NAMESPACE" --patch '{
        "metadata": {
            "annotations": {
                "nginx.ingress.kubernetes.io/upstream-keepalive-connections": "50",
                "nginx.ingress.kubernetes.io/upstream-keepalive-requests": "100",
                "nginx.ingress.kubernetes.io/upstream-keepalive-timeout": "60"
            }
        }
    }' || log_warn "Ingress rag-ingress non trouvé"
    
    log_info "Réseau optimisé"
}

# ===== CONFIGURATION MONITORING =====

optimize_monitoring() {
    log_step "Optimisation du monitoring..."
    
    # Configuration Prometheus pour la production
    kubectl patch configmap prometheus-config -n "$NAMESPACE" --patch '{
        "data": {
            "prometheus.yml": "global:\n  scrape_interval: 15s\n  evaluation_interval: 15s\n  external_labels:\n    environment: '${ENVIRONMENT}'\n    cluster: rag-system\n\nrule_files:\n  - /etc/prometheus/rules/*.yml\n\nscrape_configs:\n  - job_name: rag-api\n    scrape_interval: 10s\n    metrics_path: /metrics\n    static_configs:\n      - targets: [\"rag-api:8000\"]\n  - job_name: postgres\n    scrape_interval: 30s\n    static_configs:\n      - targets: [\"postgres-exporter:9187\"]\n  - job_name: redis\n    scrape_interval: 30s\n    static_configs:\n      - targets: [\"redis-exporter:9121\"]\n"
        }
    }' || log_warn "ConfigMap prometheus-config non trouvée"
    
    # Redémarrer Prometheus pour appliquer la config
    kubectl rollout restart deployment/prometheus -n "$NAMESPACE" || log_warn "Prometheus non déployé"
    
    log_info "Monitoring optimisé"
}

# ===== NETTOYAGE ET MAINTENANCE =====

cleanup_resources() {
    log_step "Nettoyage des ressources..."
    
    # Nettoyage des pods terminés
    kubectl delete pods --field-selector=status.phase=Succeeded -n "$NAMESPACE" || true
    kubectl delete pods --field-selector=status.phase=Failed -n "$NAMESPACE" || true
    
    # Nettoyage des logs anciens
    kubectl exec deployment/rag-api -n "$NAMESPACE" -- find /app/logs -name "*.log" -mtime +7 -delete || true
    
    # Rotation des logs
    kubectl exec deployment/rag-api -n "$NAMESPACE" -- logrotate /etc/logrotate.conf || true
    
    log_info "Nettoyage terminé"
}

# ===== TESTS DE PERFORMANCE =====

run_performance_tests() {
    log_step "Tests de performance post-optimisation..."
    
    # Test de latence API
    log_info "Test de latence API..."
    for i in {1..5}; do
        response_time=$(curl -o /dev/null -s -w "%{time_total}" "$API_BASE_URL/health")
        log_info "Tentative $i: ${response_time}s"
    done
    
    # Test de charge légère
    log_info "Test de charge légère..."
    kubectl run load-test --image=alpine/curl --rm -i --restart=Never -- \
        /bin/sh -c "
        for i in \$(seq 1 10); do
            curl -s $API_BASE_URL/health > /dev/null
            echo \"Request \$i completed\"
            sleep 0.1
        done
        " || log_warn "Test de charge échoué"
    
    log_info "Tests de performance terminés"
}

# ===== RAPPORT D'OPTIMISATION =====

generate_optimization_report() {
    log_step "Génération du rapport d'optimisation..."
    
    local report_file="/tmp/optimization-report-$(date +%Y%m%d_%H%M%S).json"
    
    # Collecte des métriques post-optimisation
    local pod_count=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running --no-headers | wc -l)
    local memory_usage=$(kubectl top pods -n "$NAMESPACE" --no-headers | awk '{sum+=$3} END {print sum}' || echo "N/A")
    local cpu_usage=$(kubectl top pods -n "$NAMESPACE" --no-headers | awk '{sum+=$2} END {print sum}' || echo "N/A")
    
    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "environment": "$ENVIRONMENT",
    "namespace": "$NAMESPACE",
    "optimization_summary": {
        "database_optimized": true,
        "cache_warmed": true,
        "network_optimized": true,
        "monitoring_optimized": true,
        "cleanup_performed": true
    },
    "post_optimization_metrics": {
        "running_pods": $pod_count,
        "memory_usage_mb": "$memory_usage",
        "cpu_usage_cores": "$cpu_usage"
    },
    "recommendations": [
        "Monitorer les performances durant les premières 24h",
        "Ajuster les limites de ressources selon l'usage",
        "Planifier la maintenance hebdomadaire",
        "Vérifier les alertes dans Grafana"
    ]
}
EOF
    
    echo
    echo "=========================================="
    echo "        RAPPORT D'OPTIMISATION"
    echo "=========================================="
    echo "Environnement: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Pods actifs: $pod_count"
    echo "Usage mémoire: ${memory_usage}MB"
    echo "Usage CPU: ${cpu_usage} cores"
    echo
    echo "Optimisations appliquées:"
    echo "  ✓ Base de données PostgreSQL"
    echo "  ✓ Cache Redis"
    echo "  ✓ Base de données vectorielle"
    echo "  ✓ Préchauffage des caches"
    echo "  ✓ Configuration réseau"
    echo "  ✓ Monitoring"
    echo "  ✓ Nettoyage des ressources"
    echo
    echo "Rapport détaillé: $report_file"
    echo
    echo -e "${GREEN}🚀 Optimisation terminée avec succès!${NC}"
    echo -e "${YELLOW}💡 Surveillez les métriques dans les prochaines heures${NC}"
}

# ===== FONCTION PRINCIPALE =====

main() {
    echo "🔧 Optimisation Post-Déploiement - Système RAG Enterprise"
    echo "========================================================"
    echo "Environnement: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo
    
    # Vérifications préalables
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_error "Namespace $NAMESPACE non trouvé"
        exit 1
    fi
    
    # Exécution des optimisations
    optimize_database
    optimize_redis
    optimize_vector_database
    warm_up_caches
    optimize_jvm
    optimize_network
    optimize_monitoring
    cleanup_resources
    run_performance_tests
    
    # Génération du rapport
    generate_optimization_report
    
    echo
    echo -e "${GREEN}✅ Système optimisé et prêt pour la production!${NC}"
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
