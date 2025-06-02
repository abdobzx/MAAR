#!/bin/bash

# Script de vérification de santé du système RAG
# Usage: ./health-check.sh [environment]

set -euo pipefail

ENVIRONMENT=${1:-production}
NAMESPACE="rag-${ENVIRONMENT}"
TIMEOUT=30

# Configuration
API_URL="https://api.rag-system.com"
if [ "$ENVIRONMENT" = "staging" ]; then
    API_URL="https://staging-api.rag-system.com"
elif [ "$ENVIRONMENT" = "development" ]; then
    API_URL="http://localhost:8000"
fi

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_kubernetes() {
    log_info "Vérification de l'état des pods Kubernetes..."
    
    # Vérifier que le namespace existe
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_error "Namespace $NAMESPACE n'existe pas"
        return 1
    fi
    
    # Vérifier l'état des pods
    local failed_pods=0
    while read -r pod status; do
        if [ "$status" != "Running" ] && [ "$status" != "Completed" ]; then
            log_error "Pod $pod est en état: $status"
            failed_pods=$((failed_pods + 1))
        else
            log_info "Pod $pod: $status"
        fi
    done < <(kubectl get pods -n "$NAMESPACE" --no-headers -o custom-columns=":metadata.name,:status.phase")
    
    return $failed_pods
}

check_services() {
    log_info "Vérification des services Kubernetes..."
    
    local services=("rag-api" "postgres" "redis" "qdrant")
    local failed_services=0
    
    for service in "${services[@]}"; do
        if kubectl get service "$service" -n "$NAMESPACE" >/dev/null 2>&1; then
            local endpoints=$(kubectl get endpoints "$service" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)
            if [ "$endpoints" -gt 0 ]; then
                log_info "Service $service: $endpoints endpoints actifs"
            else
                log_error "Service $service: aucun endpoint actif"
                failed_services=$((failed_services + 1))
            fi
        else
            log_error "Service $service: non trouvé"
            failed_services=$((failed_services + 1))
        fi
    done
    
    return $failed_services
}

check_api_health() {
    log_info "Vérification de l'API de santé..."
    
    local response
    local http_code
    
    if ! response=$(curl -s -w "%{http_code}" --max-time "$TIMEOUT" "$API_URL/health"); then
        log_error "Impossible de contacter l'API à $API_URL/health"
        return 1
    fi
    
    http_code="${response: -3}"
    response="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        log_info "API Health Check: OK"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        log_error "API Health Check: HTTP $http_code"
        echo "$response"
        return 1
    fi
}

check_database() {
    log_info "Vérification de la base de données..."
    
    if ! kubectl exec deployment/postgres -n "$NAMESPACE" -- pg_isready -q; then
        log_error "Base de données PostgreSQL non accessible"
        return 1
    fi
    
    local connections
    connections=$(kubectl exec deployment/postgres -n "$NAMESPACE" -- psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | tr -d ' ')
    
    if [ -n "$connections" ]; then
        log_info "Base de données: $connections connexions actives"
    else
        log_error "Impossible de récupérer le nombre de connexions"
        return 1
    fi
}

check_redis() {
    log_info "Vérification de Redis..."
    
    if ! kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli ping >/dev/null 2>&1; then
        log_error "Redis non accessible"
        return 1
    fi
    
    local memory_usage
    memory_usage=$(kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    
    log_info "Redis: $memory_usage utilisés"
}

check_vector_database() {
    log_info "Vérification de Qdrant..."
    
    local response
    if response=$(kubectl exec deployment/qdrant -n "$NAMESPACE" -- curl -s localhost:6333/collections 2>/dev/null); then
        local collections_count
        collections_count=$(echo "$response" | jq '.result.collections | length' 2>/dev/null || echo "unknown")
        log_info "Qdrant: $collections_count collections"
    else
        log_error "Qdrant non accessible"
        return 1
    fi
}

check_celery() {
    log_info "Vérification des workers Celery..."
    
    local active_workers
    if active_workers=$(kubectl exec deployment/rag-celery -n "$NAMESPACE" -- celery -A core.celery inspect active 2>/dev/null | grep -c "worker" || echo "0"); then
        log_info "Celery: $active_workers workers actifs"
    else
        log_error "Impossible de vérifier les workers Celery"
        return 1
    fi
}

check_monitoring() {
    log_info "Vérification du monitoring..."
    
    # Prometheus
    if kubectl get pod -l app.kubernetes.io/name=prometheus -n "$NAMESPACE" >/dev/null 2>&1; then
        log_info "Prometheus: actif"
    else
        log_warn "Prometheus: non trouvé"
    fi
    
    # Grafana
    if kubectl get pod -l app.kubernetes.io/name=grafana -n "$NAMESPACE" >/dev/null 2>&1; then
        log_info "Grafana: actif"
    else
        log_warn "Grafana: non trouvé"
    fi
}

run_functional_tests() {
    log_info "Exécution des tests fonctionnels..."
    
    # Test d'authentification
    local auth_response
    if auth_response=$(curl -s -X POST "$API_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"test"}' \
        --max-time "$TIMEOUT"); then
        
        if echo "$auth_response" | jq -e '.access_token' >/dev/null 2>&1; then
            log_info "Test d'authentification: OK"
        else
            log_warn "Test d'authentification: réponse inattendue"
        fi
    else
        log_warn "Test d'authentification: échec"
    fi
    
    # Test de upload de document (sans authentification réelle)
    log_info "Test de l'endpoint de upload: simulation"
    
    # Test de chat
    log_info "Test de l'endpoint de chat: simulation"
}

generate_report() {
    local exit_code=$1
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo
    echo "===================="
    echo "RAPPORT DE SANTÉ"
    echo "===================="
    echo "Environnement: $ENVIRONMENT"
    echo "Timestamp: $timestamp"
    echo "Statut global: $([ $exit_code -eq 0 ] && echo "✅ HEALTHY" || echo "❌ UNHEALTHY")"
    echo
    
    if [ $exit_code -ne 0 ]; then
        echo "Des problèmes ont été détectés. Consultez les logs ci-dessus."
        echo "Pour plus de détails:"
        echo "  kubectl get pods -n $NAMESPACE"
        echo "  kubectl logs -f deployment/rag-api -n $NAMESPACE"
    fi
}

main() {
    local exit_code=0
    
    echo "🏥 Health Check du Système RAG - Environment: $ENVIRONMENT"
    echo "============================================================"
    
    # Vérifications séquentielles
    check_kubernetes || exit_code=1
    check_services || exit_code=1
    check_api_health || exit_code=1
    check_database || exit_code=1
    check_redis || exit_code=1
    check_vector_database || exit_code=1
    check_celery || exit_code=1
    check_monitoring
    run_functional_tests
    
    generate_report $exit_code
    
    exit $exit_code
}

# Exécution du script
main "$@"
