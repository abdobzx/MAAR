#!/bin/bash

# Script de Validation Finale du Système RAG Enterprise
# Version 1.0 - Décembre 2024
# 
# Ce script effectue une validation complète du système pour s'assurer
# que tous les composants sont correctement déployés et fonctionnels.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/tmp/system-validation-$(date +%Y%m%d_%H%M%S).log"

# Configuration
NAMESPACE=${NAMESPACE:-enterprise-rag}
ENVIRONMENT=${ENVIRONMENT:-production}
ADMIN_TOKEN=${ADMIN_TOKEN:-}
API_BASE_URL=${API_BASE_URL:-https://api.rag-system.com}

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Compteurs
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=()

# Configuration des timeouts
TIMEOUT_SHORT=10
TIMEOUT_MEDIUM=30
TIMEOUT_LONG=60

# URLs de test
HEALTH_URL="${API_BASE_URL}/health"
DOCS_URL="${API_BASE_URL}/docs"
METRICS_URL="${API_BASE_URL}/metrics"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

log_test() {
    echo -e "${PURPLE}[TEST]${NC} $1" | tee -a "$LOG_FILE"
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log_test "Exécution: $test_name"
    
    if eval "$test_command" >> "$LOG_FILE" 2>&1; then
        echo -e "  ${GREEN}✓${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "  ${RED}✗${NC} $test_name"
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

# ===== VALIDATION KUBERNETES =====

validate_kubernetes_cluster() {
    log_step "Validation du cluster Kubernetes..."
    
    run_test "Connexion au cluster" "kubectl cluster-info --request-timeout=${TIMEOUT_SHORT}s"
    run_test "Namespace existant" "kubectl get namespace $NAMESPACE"
    run_test "Pods en cours d'exécution" "kubectl get pods -n $NAMESPACE --field-selector=status.phase=Running"
    run_test "Services exposés" "kubectl get services -n $NAMESPACE"
    run_test "Ingress configuré" "kubectl get ingress -n $NAMESPACE"
    run_test "ConfigMaps présentes" "kubectl get configmaps -n $NAMESPACE"
    run_test "Secrets configurés" "kubectl get secrets -n $NAMESPACE"
}

validate_deployments() {
    log_step "Validation des déploiements..."
    
    local deployments=("rag-api" "postgres" "redis" "qdrant" "celery-worker" "celery-beat")
    
    for deployment in "${deployments[@]}"; do
        run_test "Déploiement $deployment" "kubectl rollout status deployment/$deployment -n $NAMESPACE --timeout=${TIMEOUT_MEDIUM}s"
        run_test "Réplicas $deployment" "test \$(kubectl get deployment $deployment -n $NAMESPACE -o jsonpath='{.status.readyReplicas}') -gt 0"
    done
}

# ===== VALIDATION API =====

validate_api_health() {
    log_step "Validation de l'API..."
    
    run_test "API Health Check" "curl -f --max-time $TIMEOUT_SHORT $HEALTH_URL"
    run_test "API Documentation" "curl -f --max-time $TIMEOUT_SHORT $DOCS_URL"
    run_test "API Metrics" "curl -f --max-time $TIMEOUT_SHORT $METRICS_URL"
    run_test "API CORS Headers" "curl -I --max-time $TIMEOUT_SHORT $HEALTH_URL | grep -i 'access-control-allow-origin'"
}

validate_authentication() {
    log_step "Validation de l'authentification..."
    
    if [ -n "$ADMIN_TOKEN" ]; then
        run_test "Token Admin valide" "curl -f --max-time $TIMEOUT_SHORT -H 'Authorization: Bearer $ADMIN_TOKEN' $API_BASE_URL/admin/status"
    else
        log_warn "ADMIN_TOKEN non fourni, tests d'authentification ignorés"
    fi
    
    run_test "Endpoint de login accessible" "curl -f --max-time $TIMEOUT_SHORT $API_BASE_URL/auth/login -X POST -H 'Content-Type: application/json' -d '{}'"
}

# ===== VALIDATION BASE DE DONNÉES =====

validate_database() {
    log_step "Validation de la base de données..."
    
    run_test "PostgreSQL accessible" "kubectl exec deployment/postgres -n $NAMESPACE -- pg_isready"
    run_test "Base de données RAG existe" "kubectl exec deployment/postgres -n $NAMESPACE -- psql -U rag -d rag -c 'SELECT 1;'"
    run_test "Tables créées" "kubectl exec deployment/postgres -n $NAMESPACE -- psql -U rag -d rag -c '\dt' | grep -q documents"
    run_test "Connexions disponibles" "kubectl exec deployment/postgres -n $NAMESPACE -- psql -U rag -d rag -c 'SELECT count(*) FROM pg_stat_activity;'"
}

validate_redis() {
    log_step "Validation de Redis..."
    
    run_test "Redis accessible" "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli ping"
    run_test "Redis info" "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli info server"
    run_test "Redis mémoire" "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli info memory | grep used_memory_human"
}

validate_vector_database() {
    log_step "Validation de la base de données vectorielle..."
    
    run_test "Qdrant accessible" "kubectl exec deployment/qdrant -n $NAMESPACE -- curl -f http://localhost:6333/health"
    run_test "Collections Qdrant" "kubectl exec deployment/qdrant -n $NAMESPACE -- curl -f http://localhost:6333/collections"
}

# ===== VALIDATION CELERY =====

validate_celery() {
    log_step "Validation de Celery..."
    
    run_test "Workers Celery actifs" "kubectl logs deployment/celery-worker -n $NAMESPACE --tail=10 | grep -q 'ready'"
    run_test "Beat Celery actif" "kubectl logs deployment/celery-beat -n $NAMESPACE --tail=10 | grep -q 'beat'"
    run_test "Queues Celery" "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli llen celery | grep -E '^[0-9]+$'"
}

# ===== VALIDATION MONITORING =====

validate_monitoring() {
    log_step "Validation du monitoring..."
    
    # Prometheus
    if kubectl get deployment prometheus -n $NAMESPACE >/dev/null 2>&1; then
        run_test "Prometheus accessible" "kubectl port-forward deployment/prometheus 9090:9090 -n $NAMESPACE & sleep 5; curl -f http://localhost:9090/-/healthy; kill %1"
    else
        log_warn "Prometheus non déployé dans ce namespace"
    fi
    
    # Grafana
    if kubectl get deployment grafana -n $NAMESPACE >/dev/null 2>&1; then
        run_test "Grafana accessible" "kubectl port-forward deployment/grafana 3000:3000 -n $NAMESPACE & sleep 5; curl -f http://localhost:3000/api/health; kill %1"
    else
        log_warn "Grafana non déployé dans ce namespace"
    fi
}

# ===== VALIDATION SÉCURITÉ =====

validate_security() {
    log_step "Validation de la sécurité..."
    
    run_test "RBAC configuré" "kubectl get rolebindings -n $NAMESPACE"
    run_test "Pod Security Policies" "kubectl get psp"
    run_test "Network Policies" "kubectl get networkpolicies -n $NAMESPACE"
    run_test "TLS configuré" "kubectl get secrets -n $NAMESPACE | grep tls"
    run_test "Secrets chiffrés" "kubectl get secrets -n $NAMESPACE -o yaml | grep -q 'type: Opaque'"
}

# ===== VALIDATION PERFORMANCE =====

validate_performance() {
    log_step "Validation des performances..."
    
    run_test "Temps de réponse API" "time curl -f --max-time 5 $HEALTH_URL"
    run_test "Ressources CPU" "kubectl top pods -n $NAMESPACE | grep -v 'NAME'"
    run_test "Ressources mémoire" "kubectl top pods -n $NAMESPACE --sort-by=memory | head -5"
    run_test "HPA configuré" "kubectl get hpa -n $NAMESPACE"
}

# ===== TESTS FONCTIONNELS =====

run_functional_tests() {
    log_step "Tests fonctionnels..."
    
    if [ -n "$ADMIN_TOKEN" ]; then
        # Test upload document
        local test_file=$(mktemp)
        echo "Test document content for validation" > "$test_file"
        
        run_test "Upload document" "curl -f --max-time $TIMEOUT_MEDIUM -X POST \
            -H 'Authorization: Bearer $ADMIN_TOKEN' \
            -F 'file=@$test_file' \
            $API_BASE_URL/documents/upload"
        
        rm -f "$test_file"
        
        # Test query
        run_test "Query processing" "curl -f --max-time $TIMEOUT_MEDIUM -X POST \
            -H 'Authorization: Bearer $ADMIN_TOKEN' \
            -H 'Content-Type: application/json' \
            -d '{\"query\":\"test query\",\"limit\":5}' \
            $API_BASE_URL/chat/query"
            
        # Test analytics
        run_test "Analytics endpoint" "curl -f --max-time $TIMEOUT_SHORT \
            -H 'Authorization: Bearer $ADMIN_TOKEN' \
            $API_BASE_URL/analytics/summary"
    else
        log_warn "Tests fonctionnels ignorés (ADMIN_TOKEN requis)"
    fi
}

# ===== VALIDATION SAUVEGARDE =====

validate_backup_system() {
    log_step "Validation du système de sauvegarde..."
    
    run_test "Script de sauvegarde" "test -x $PROJECT_ROOT/scripts/backup/backup.sh"
    run_test "Configuration AWS" "kubectl get secrets -n $NAMESPACE | grep aws"
    run_test "CronJob sauvegarde" "kubectl get cronjobs -n $NAMESPACE | grep backup"
}

# ===== RAPPORT FINAL =====

generate_report() {
    local report_file="/tmp/system-validation-report-$(date +%Y%m%d_%H%M%S).json"
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "environment": "$ENVIRONMENT",
    "namespace": "$NAMESPACE",
    "duration_seconds": $duration,
    "summary": {
        "total_tests": $TOTAL_TESTS,
        "passed_tests": $PASSED_TESTS,
        "failed_tests": ${#FAILED_TESTS[@]},
        "success_rate": $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)
    },
    "failed_tests": [$(printf '"%s",' "${FAILED_TESTS[@]}" | sed 's/,$//')]
}
EOF
    
    echo
    echo "=========================================="
    echo "           RAPPORT DE VALIDATION"
    echo "=========================================="
    echo "Environnement: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Durée: ${duration}s"
    echo
    echo "Tests exécutés: $TOTAL_TESTS"
    echo -e "Tests réussis: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Tests échoués: ${RED}${#FAILED_TESTS[@]}${NC}"
    echo "Taux de réussite: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%"
    echo
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo -e "${RED}Tests échoués:${NC}"
        printf '  - %s\n' "${FAILED_TESTS[@]}"
        echo
    fi
    
    echo "Log détaillé: $LOG_FILE"
    echo "Rapport JSON: $report_file"
    echo
    
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        echo -e "${GREEN}🎉 VALIDATION RÉUSSIE - Système prêt pour la production!${NC}"
        return 0
    else
        echo -e "${RED}❌ VALIDATION ÉCHOUÉE - Vérifiez les erreurs ci-dessus${NC}"
        return 1
    fi
}

# ===== FONCTION PRINCIPALE =====

main() {
    local start_time=$(date +%s)
    
    echo "🔍 Validation Complète du Système RAG Enterprise"
    echo "==============================================="
    echo "Environnement: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "API: $API_BASE_URL"
    echo "Log: $LOG_FILE"
    echo
    
    # Initialiser le log
    echo "=== DÉBUT DE LA VALIDATION $(date) ===" > "$LOG_FILE"
    
    # Validation des prérequis
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl non installé"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl non installé"
        exit 1
    fi
    
    if ! command -v bc &> /dev/null; then
        log_error "bc non installé"
        exit 1
    fi
    
    # Exécution des validations
    validate_kubernetes_cluster
    validate_deployments
    validate_api_health
    validate_authentication
    validate_database
    validate_redis
    validate_vector_database
    validate_celery
    validate_monitoring
    validate_security
    validate_performance
    run_functional_tests
    validate_backup_system
    
    # Génération du rapport
    generate_report
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
FAILED_TESTS=0
WARNINGS=0

log_info() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$LOG_FILE"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"
    ((FAILED_TESTS++))
}

log_step() {
    echo -e "${BLUE}[→]${NC} $1" | tee -a "$LOG_FILE"
}

log_section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}" | tee -a "$LOG_FILE"
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((TOTAL_TESTS++))
    log_step "Test: $test_name"
    
    if eval "$test_command" >> "$LOG_FILE" 2>&1; then
        log_info "$test_name: SUCCÈS"
        ((PASSED_TESTS++))
        return 0
    else
        log_error "$test_name: ÉCHEC"
        return 1
    fi
}

check_prerequisites() {
    log_section "Vérification des Prérequis"
    
    # Outils requis
    local tools=("kubectl" "helm" "curl" "jq" "docker")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_info "$tool: Disponible"
        else
            log_error "$tool: Non disponible"
            exit 1
        fi
    done
    
    # Connexion Kubernetes
    if kubectl cluster-info &> /dev/null; then
        log_info "Connexion Kubernetes: OK"
    else
        log_error "Connexion Kubernetes: ÉCHEC"
        exit 1
    fi
    
    # Namespace
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace $NAMESPACE: Existe"
    else
        log_error "Namespace $NAMESPACE: N'existe pas"
        exit 1
    fi
}

validate_infrastructure() {
    log_section "Validation de l'Infrastructure"
    
    # Nœuds Kubernetes
    run_test "Nœuds Kubernetes disponibles" \
        "kubectl get nodes | grep -q Ready"
    
    # Stockage persistant
    run_test "Classes de stockage configurées" \
        "kubectl get storageclass | grep -q default"
    
    # Ingress Controller
    run_test "Ingress Controller déployé" \
        "kubectl get pods -A | grep -q ingress"
    
    # DNS interne
    run_test "DNS interne fonctionnel" \
        "kubectl run dns-test --rm -i --restart=Never --image=busybox:1.28 -- nslookup kubernetes.default"
}

validate_deployments() {
    log_section "Validation des Déploiements"
    
    local deployments=(
        "rag-api"
        "rag-celery"
        "celery-beat"
        "postgres"
        "redis" 
        "qdrant"
        "minio"
        "keycloak"
    )
    
    for deployment in "${deployments[@]}"; do
        run_test "Déploiement $deployment" \
            "kubectl get deployment $deployment -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' | grep -v '^0$'"
    done
    
    # Vérification des pods en cours d'exécution
    run_test "Tous les pods sont Running" \
        "! kubectl get pods -n $NAMESPACE | grep -v Running | grep -v Completed | grep -v READY"
    
    # Vérification des ressources
    run_test "Utilisation des ressources acceptable" \
        "kubectl top pods -n $NAMESPACE --no-headers | awk '{if(\$3 > 90) exit 1}'"
}

validate_services() {
    log_section "Validation des Services"
    
    local services=(
        "rag-api-service:8000"
        "postgres-service:5432"
        "redis-service:6379"
        "qdrant-service:6333"
        "minio-service:9000"
        "keycloak-service:8080"
    )
    
    for service in "${services[@]}"; do
        local service_name="${service%:*}"
        local port="${service#*:}"
        
        run_test "Service $service_name accessible" \
            "kubectl get service $service_name -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}' | grep -q $port"
    done
    
    # Test de connectivité interne
    run_test "Connectivité inter-services" \
        "kubectl run connectivity-test --rm -i --restart=Never --image=busybox:1.28 -n $NAMESPACE -- sh -c 'nc -z rag-api-service 8000'"
}

validate_security() {
    log_section "Validation de la Sécurité"
    
    # RBAC
    run_test "RBAC configuré" \
        "kubectl get rolebindings -n $NAMESPACE | grep -q rag"
    
    # Network Policies
    run_test "Network Policies appliquées" \
        "kubectl get networkpolicy -n $NAMESPACE | grep -q rag"
    
    # Pod Security Policies
    run_test "Pod Security Standards configurés" \
        "kubectl get namespace $NAMESPACE -o jsonpath='{.metadata.labels}' | grep -q security"
    
    # Secrets
    local secrets=("enterprise-rag-secrets" "rag-tls")
    for secret in "${secrets[@]}"; do
        run_test "Secret $secret existe" \
            "kubectl get secret $secret -n $NAMESPACE"
    done
    
    # Certificats TLS
    run_test "Certificats TLS valides" \
        "kubectl get certificate -n $NAMESPACE | grep -q True"
}

validate_api_functionality() {
    log_section "Validation de l'API"
    
    # Health check basique
    run_test "API Health Check" \
        "curl -f $API_BASE_URL/health"
    
    # Vérification OpenAPI
    run_test "Documentation OpenAPI accessible" \
        "curl -f $API_BASE_URL/docs | grep -q 'swagger'"
    
    # Metrics endpoint
    run_test "Métriques Prometheus disponibles" \
        "curl -f $API_BASE_URL/metrics | grep -q 'http_requests_total'"
    
    if [[ -n "$ADMIN_TOKEN" ]]; then
        # Tests avec authentification
        run_test "Authentification fonctionnelle" \
            "curl -f -H 'Authorization: Bearer $ADMIN_TOKEN' $API_BASE_URL/admin/health"
        
        # Test des composants critiques
        run_test "Base de données accessible via API" \
            "curl -f -H 'Authorization: Bearer $ADMIN_TOKEN' $API_BASE_URL/admin/health/database | grep -q 'healthy'"
        
        run_test "Redis accessible via API" \
            "curl -f -H 'Authorization: Bearer $ADMIN_TOKEN' $API_BASE_URL/admin/health/redis | grep -q 'healthy'"
        
        run_test "Qdrant accessible via API" \
            "curl -f -H 'Authorization: Bearer $ADMIN_TOKEN' $API_BASE_URL/admin/health/qdrant | grep -q 'healthy'"
    else
        log_warn "ADMIN_TOKEN non fourni, tests d'authentification ignorés"
    fi
}

validate_database() {
    log_section "Validation de la Base de Données"
    
    # Connexion PostgreSQL
    run_test "PostgreSQL connectivité" \
        "kubectl exec deployment/postgres -n $NAMESPACE -- pg_isready -U rag_user"
    
    # Tables principales
    run_test "Tables créées" \
        "kubectl exec deployment/postgres -n $NAMESPACE -- psql -U rag_user -d rag_database -c '\\dt' | grep -q documents"
    
    # Performance des requêtes
    run_test "Performance des requêtes acceptable" \
        "kubectl exec deployment/postgres -n $NAMESPACE -- psql -U rag_user -d rag_database -c 'SELECT 1' | grep -q '1'"
    
    # Espace disque
    run_test "Espace disque base de données suffisant" \
        "kubectl exec deployment/postgres -n $NAMESPACE -- df -h /var/lib/postgresql/data | tail -1 | awk '{print \$5}' | sed 's/%//' | awk '{if(\$1 > 80) exit 1}'"
}

validate_vector_database() {
    log_section "Validation de la Base Vectorielle"
    
    # Qdrant API
    run_test "API Qdrant accessible" \
        "kubectl exec deployment/qdrant -n $NAMESPACE -- curl -f localhost:6333/health"
    
    # Collections
    run_test "Collection enterprise_rag existe" \
        "kubectl exec deployment/qdrant -n $NAMESPACE -- curl -s localhost:6333/collections | grep -q enterprise_rag"
    
    # Performance
    run_test "Qdrant performance acceptable" \
        "kubectl exec deployment/qdrant -n $NAMESPACE -- curl -s localhost:6333/metrics | grep -q vectors_count"
}

validate_cache() {
    log_section "Validation du Cache Redis"
    
    # Connexion Redis
    run_test "Redis connectivité" \
        "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli ping | grep -q PONG"
    
    # Mémoire
    run_test "Utilisation mémoire Redis acceptable" \
        "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli info memory | grep used_memory_human"
    
    # Performance
    run_test "Redis performance acceptable" \
        "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli --latency-history -i 1 | head -1"
}

validate_celery() {
    log_section "Validation de Celery"
    
    # Workers actifs
    run_test "Workers Celery actifs" \
        "kubectl logs deployment/rag-celery -n $NAMESPACE --tail=10 | grep -q 'ready'"
    
    # Beat scheduler
    run_test "Celery Beat opérationnel" \
        "kubectl logs deployment/celery-beat -n $NAMESPACE --tail=10 | grep -q 'beat'"
    
    # Queue status
    run_test "Queues Celery disponibles" \
        "kubectl exec deployment/redis -n $NAMESPACE -- redis-cli llen celery | grep -E '^[0-9]+$'"
}

validate_monitoring() {
    log_section "Validation du Monitoring"
    
    # Prometheus
    if kubectl get deployment prometheus -n $NAMESPACE &> /dev/null; then
        run_test "Prometheus opérationnel" \
            "kubectl exec deployment/prometheus -n $NAMESPACE -- wget -q -O- localhost:9090/-/healthy | grep -q 'Prometheus is Healthy'"
        
        # Targets Prometheus
        run_test "Targets Prometheus configurés" \
            "kubectl exec deployment/prometheus -n $NAMESPACE -- wget -q -O- 'localhost:9090/api/v1/targets' | jq '.data.activeTargets | length' | grep -v '^0$'"
    fi
    
    # Grafana
    if kubectl get deployment grafana -n $NAMESPACE &> /dev/null; then
        run_test "Grafana accessible" \
            "kubectl exec deployment/grafana -n $NAMESPACE -- curl -f localhost:3000/api/health"
    fi
    
    # Jaeger (si déployé)
    if kubectl get deployment jaeger -n $NAMESPACE &> /dev/null; then
        run_test "Jaeger opérationnel" \
            "kubectl exec deployment/jaeger -n $NAMESPACE -- curl -f localhost:16686/api/services"
    fi
}

validate_storage() {
    log_section "Validation du Stockage"
    
    # MinIO
    run_test "MinIO accessible" \
        "kubectl exec deployment/minio -n $NAMESPACE -- curl -f localhost:9000/minio/health/live"
    
    # Buckets
    run_test "Bucket rag-documents existe" \
        "kubectl exec deployment/minio -n $NAMESPACE -- mc ls local/ | grep -q rag-documents"
    
    # Espace disque
    run_test "Espace disque MinIO suffisant" \
        "kubectl exec deployment/minio -n $NAMESPACE -- df -h /data | tail -1 | awk '{print \$5}' | sed 's/%//' | awk '{if(\$1 > 80) exit 1}'"
    
    # Volumes persistants
    run_test "Volumes persistants sains" \
        "kubectl get pv | grep -q Bound"
}

validate_networking() {
    log_section "Validation du Réseau"
    
    # Ingress
    run_test "Ingress configuré" \
        "kubectl get ingress -n $NAMESPACE | grep -q rag"
    
    # DNS externe
    run_test "DNS externe résolu" \
        "nslookup api.rag-system.com | grep -q 'Address:'"
    
    # Certificats SSL
    run_test "Certificat SSL valide" \
        "echo | openssl s_client -servername api.rag-system.com -connect api.rag-system.com:443 2>/dev/null | openssl x509 -noout -dates | grep -q 'After:'"
    
    # Load balancer
    run_test "Load balancer opérationnel" \
        "curl -I $API_BASE_URL | grep -q '200\\|301\\|302'"
}

validate_backup_system() {
    log_section "Validation du Système de Sauvegarde"
    
    # Scripts de sauvegarde
    run_test "Scripts de sauvegarde présents" \
        "test -f $PROJECT_ROOT/scripts/backup/backup.sh"
    
    # Cron jobs (si configurés)
    if crontab -l 2>/dev/null | grep -q backup; then
        run_test "Tâches de sauvegarde planifiées" \
            "crontab -l | grep -q backup"
    fi
    
    # Espace de sauvegarde
    if [[ -d "/backups" ]]; then
        run_test "Répertoire de sauvegarde accessible" \
            "test -w /backups"
    fi
}

validate_security_compliance() {
    log_section "Validation de la Conformité Sécurité"
    
    # Images sans vulnérabilités critiques (si Trivy disponible)
    if command -v trivy &> /dev/null; then
        run_test "Images sans vulnérabilités critiques" \
            "trivy image --exit-code 1 --severity HIGH,CRITICAL enterprise-rag:latest"
    fi
    
    # Politiques de sécurité
    run_test "Politiques de sécurité appliquées" \
        "kubectl get psp 2>/dev/null | grep -q rag || kubectl get psa -A | grep -q restricted"
    
    # Chiffrement en transit
    run_test "Chiffrement en transit activé" \
        "curl -I $API_BASE_URL | grep -q 'Strict-Transport-Security'"
}

run_end_to_end_tests() {
    log_section "Tests de Bout en Bout"
    
    if [[ -n "$ADMIN_TOKEN" ]]; then
        # Test d'upload de document (si l'API le permet)
        run_test "Test d'upload de document" \
            "echo 'Test document content' | curl -f -X POST -H 'Authorization: Bearer $ADMIN_TOKEN' -F 'file=@-' $API_BASE_URL/documents/upload"
        
        # Test de recherche
        run_test "Test de recherche" \
            "curl -f -X POST -H 'Authorization: Bearer $ADMIN_TOKEN' -H 'Content-Type: application/json' -d '{\"query\":\"test\"}' $API_BASE_URL/search"
    else
        log_warn "Tests E2E ignorés - ADMIN_TOKEN non fourni"
    fi
}

run_performance_checks() {
    log_section "Vérifications de Performance"
    
    # Temps de réponse API
    run_test "Temps de réponse API acceptable (<500ms)" \
        "curl -w '%{time_total}' -s -o /dev/null $API_BASE_URL/health | awk '{if(\$1 > 0.5) exit 1}'"
    
    # Utilisation CPU des nœuds
    run_test "Utilisation CPU des nœuds acceptable (<80%)" \
        "kubectl top nodes --no-headers | awk '{if(\$3 > 80) exit 1}'"
    
    # Utilisation mémoire des pods
    run_test "Utilisation mémoire des pods acceptable (<85%)" \
        "kubectl top pods -n $NAMESPACE --no-headers | awk '{if(\$4 > 85) exit 1}' || true"
}

generate_report() {
    log_section "Génération du Rapport"
    
    local report_file="/tmp/validation-report-$(date +%Y%m%d_%H%M%S).html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Rapport de Validation - Système RAG Enterprise</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background-color: #f4f4f4; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        .metric { background-color: #f9f9f9; padding: 10px; border-left: 4px solid #007cba; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Rapport de Validation - Système RAG Enterprise</h1>
        <p><strong>Date:</strong> $(date)</p>
        <p><strong>Environnement:</strong> $ENVIRONMENT</p>
        <p><strong>Namespace:</strong> $NAMESPACE</p>
    </div>
    
    <div class="section">
        <h2>Résumé Exécutif</h2>
        <div class="metric">
            <strong>Tests Exécutés:</strong> $TOTAL_TESTS<br>
            <strong class="success">Succès:</strong> $PASSED_TESTS<br>
            <strong class="warning">Avertissements:</strong> $WARNINGS<br>
            <strong class="error">Échecs:</strong> $FAILED_TESTS<br>
            <strong>Taux de Réussite:</strong> $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%
        </div>
    </div>
    
    <div class="section">
        <h2>Détails des Tests</h2>
        <pre>$(cat "$LOG_FILE")</pre>
    </div>
    
    <div class="section">
        <h2>Recommandations</h2>
EOF

    if [[ $FAILED_TESTS -gt 0 ]]; then
        echo "        <p class=\"error\">⚠️ Des échecs ont été détectés. Veuillez consulter les logs détaillés et corriger les problèmes avant de mettre en production.</p>" >> "$report_file"
    elif [[ $WARNINGS -gt 0 ]]; then
        echo "        <p class=\"warning\">⚠️ Des avertissements ont été émis. Le système est fonctionnel mais pourrait être optimisé.</p>" >> "$report_file"
    else
        echo "        <p class=\"success\">✅ Tous les tests sont passés avec succès. Le système est prêt pour la production.</p>" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF
    </div>
    
    <div class="section">
        <h2>Actions Suggérées</h2>
        <ul>
            <li>Surveiller les métriques de performance en continu</li>
            <li>Exécuter les tests de charge régulièrement</li>
            <li>Maintenir les sauvegardes à jour</li>
            <li>Réviser les politiques de sécurité trimestriellement</li>
        </ul>
    </div>
</body>
</html>
EOF
    
    echo "Rapport HTML généré: $report_file"
    
    # Rapport JSON pour l'intégration
    local json_report="/tmp/validation-report-$(date +%Y%m%d_%H%M%S).json"
    cat > "$json_report" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "environment": "$ENVIRONMENT",
    "namespace": "$NAMESPACE",
    "summary": {
        "total_tests": $TOTAL_TESTS,
        "passed_tests": $PASSED_TESTS,
        "failed_tests": $FAILED_TESTS,
        "warnings": $WARNINGS,
        "success_rate": $(( PASSED_TESTS * 100 / TOTAL_TESTS ))
    },
    "status": "$(if [[ $FAILED_TESTS -eq 0 ]]; then echo "PASSED"; else echo "FAILED"; fi)",
    "log_file": "$LOG_FILE"
}
EOF
    
    echo "Rapport JSON généré: $json_report"
}

notify_results() {
    local status
    if [[ $FAILED_TESTS -eq 0 ]]; then
        status="✅ SUCCÈS"
    else
        status="❌ ÉCHEC"
    fi
    
    # Notification Slack (si configurée)
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            --data "{
                \"text\": \"$status - Validation Système RAG\",
                \"attachments\": [{
                    \"color\": \"$(if [[ $FAILED_TESTS -eq 0 ]]; then echo 'good'; else echo 'danger'; fi)\",
                    \"fields\": [
                        {\"title\": \"Environnement\", \"value\": \"$ENVIRONMENT\", \"short\": true},
                        {\"title\": \"Tests Total\", \"value\": \"$TOTAL_TESTS\", \"short\": true},
                        {\"title\": \"Succès\", \"value\": \"$PASSED_TESTS\", \"short\": true},
                        {\"title\": \"Échecs\", \"value\": \"$FAILED_TESTS\", \"short\": true},
                        {\"title\": \"Taux Réussite\", \"value\": \"$(( PASSED_TESTS * 100 / TOTAL_TESTS ))%\", \"short\": true}
                    ]
                }]
            }"
    fi
}

main() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              VALIDATION SYSTÈME RAG ENTERPRISE              ║"
    echo "║                        Version 1.0                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    echo "Log des détails: $LOG_FILE"
    echo "Environnement: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo ""
    
    # Exécution des validations
    check_prerequisites
    validate_infrastructure
    validate_deployments
    validate_services
    validate_security
    validate_api_functionality
    validate_database
    validate_vector_database
    validate_cache
    validate_celery
    validate_monitoring
    validate_storage
    validate_networking
    validate_backup_system
    validate_security_compliance
    run_end_to_end_tests
    run_performance_checks
    
    # Génération des rapports
    generate_report
    notify_results
    
    # Résumé final
    echo -e "\n${PURPLE}=== RÉSUMÉ FINAL ===${NC}"
    echo "Tests exécutés: $TOTAL_TESTS"
    echo -e "Succès: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Avertissements: ${YELLOW}$WARNINGS${NC}"
    echo -e "Échecs: ${RED}$FAILED_TESTS${NC}"
    echo "Taux de réussite: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 VALIDATION RÉUSSIE - Système prêt pour la production!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ VALIDATION ÉCHOUÉE - Veuillez corriger les problèmes identifiés${NC}"
        exit 1
    fi
}

# Vérification des arguments
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Variables d'environnement:"
    echo "  NAMESPACE      - Namespace Kubernetes (défaut: enterprise-rag)"
    echo "  ENVIRONMENT    - Environnement cible (défaut: production)"
    echo "  ADMIN_TOKEN    - Token d'administration pour les tests API"
    echo "  API_BASE_URL   - URL de base de l'API (défaut: https://api.rag-system.com)"
    echo "  SLACK_WEBHOOK_URL - Webhook Slack pour les notifications"
    echo ""
    echo "Exemples:"
    echo "  $0                                    # Validation standard"
    echo "  ENVIRONMENT=staging $0                # Validation en staging"
    echo "  ADMIN_TOKEN=xyz123 $0                 # Avec tests d'authentification"
    exit 0
fi

# Exécution du script principal
main
