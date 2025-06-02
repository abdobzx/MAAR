#!/bin/bash

# Script de déploiement automatisé pour le système RAG
# Usage: ./deploy.sh [environment] [version]

set -euo pipefail

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
NAMESPACE="rag-${ENVIRONMENT}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
DOCKER_REGISTRY="your-registry.com"
IMAGE_TAG="${DOCKER_REGISTRY}/rag-system:${VERSION}"
HELM_CHART_PATH="${PROJECT_ROOT}/infrastructure/helm"

# Couleurs pour l'affichage
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

cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Déploiement échoué. Nettoyage..."
        # Rollback automatique si nécessaire
        if [ -n "${PREVIOUS_VERSION:-}" ]; then
            log_warn "Rollback vers la version précédente: $PREVIOUS_VERSION"
            rollback_deployment
        fi
    fi
}

trap cleanup EXIT

validate_environment() {
    log_step "Validation de l'environnement..."
    
    # Vérifier les outils requis
    local required_tools=("kubectl" "helm" "docker" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Outil requis manquant: $tool"
            exit 1
        fi
    done
    
    # Vérifier la connexion kubectl
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Impossible de se connecter au cluster Kubernetes"
        exit 1
    fi
    
    # Vérifier les permissions
    if ! kubectl auth can-i create deployment --namespace="$NAMESPACE"; then
        log_error "Permissions insuffisantes pour déployer dans le namespace $NAMESPACE"
        exit 1
    fi
    
    log_info "Environnement validé"
}

prepare_namespace() {
    log_step "Préparation du namespace $NAMESPACE..."
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Création du namespace $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    fi
    
    # Appliquer les labels
    kubectl label namespace "$NAMESPACE" environment="$ENVIRONMENT" --overwrite
    kubectl label namespace "$NAMESPACE" managed-by=helm --overwrite
    
    log_info "Namespace préparé"
}

build_and_push_images() {
    log_step "Construction et push des images Docker..."
    
    cd "$PROJECT_ROOT"
    
    # Build de l'image principale
    log_info "Construction de l'image principale..."
    docker build -t "$IMAGE_TAG" .
    
    # Build des images des agents
    for agent in ingestion vectorization feedback; do
        log_info "Construction de l'image $agent..."
        docker build -t "${DOCKER_REGISTRY}/rag-${agent}:${VERSION}" \
            -f "agents/${agent}/Dockerfile" .
    done
    
    # Push des images
    log_info "Push des images vers le registry..."
    docker push "$IMAGE_TAG"
    
    for agent in ingestion vectorization feedback; do
        docker push "${DOCKER_REGISTRY}/rag-${agent}:${VERSION}"
    done
    
    log_info "Images construites et poussées"
}

apply_secrets() {
    log_step "Application des secrets..."
    
    # Créer les secrets depuis les variables d'environnement ou les fichiers
    if [ -f "${PROJECT_ROOT}/.env.${ENVIRONMENT}" ]; then
        log_info "Application des secrets depuis .env.${ENVIRONMENT}"
        
        # Convertir le fichier .env en secret Kubernetes
        kubectl create secret generic rag-config \
            --from-env-file="${PROJECT_ROOT}/.env.${ENVIRONMENT}" \
            --namespace="$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # Secrets pour les certificats TLS
    if [ -f "${PROJECT_ROOT}/certs/tls.crt" ] && [ -f "${PROJECT_ROOT}/certs/tls.key" ]; then
        log_info "Application des certificats TLS"
        kubectl create secret tls rag-tls \
            --cert="${PROJECT_ROOT}/certs/tls.crt" \
            --key="${PROJECT_ROOT}/certs/tls.key" \
            --namespace="$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    log_info "Secrets appliqués"
}

get_current_version() {
    # Récupérer la version actuelle pour le rollback
    PREVIOUS_VERSION=$(helm get values rag-system -n "$NAMESPACE" -o json 2>/dev/null | jq -r '.image.tag // "none"' || echo "none")
    if [ "$PREVIOUS_VERSION" = "none" ]; then
        log_info "Première installation détectée"
    else
        log_info "Version actuelle: $PREVIOUS_VERSION"
    fi
}

deploy_with_helm() {
    log_step "Déploiement avec Helm..."
    
    get_current_version
    
    # Préparer les valeurs spécifiques à l'environnement
    local values_file="${HELM_CHART_PATH}/values-${ENVIRONMENT}.yaml"
    if [ ! -f "$values_file" ]; then
        values_file="${HELM_CHART_PATH}/values.yaml"
    fi
    
    # Déploiement Helm
    helm upgrade --install rag-system "$HELM_CHART_PATH" \
        --namespace="$NAMESPACE" \
        --values="$values_file" \
        --set image.tag="$VERSION" \
        --set environment="$ENVIRONMENT" \
        --wait \
        --timeout=10m \
        --atomic
    
    log_info "Déploiement Helm terminé"
}

apply_monitoring() {
    log_step "Configuration du monitoring..."
    
    # Appliquer les règles Prometheus
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/monitoring/alerts/" -n "$NAMESPACE"
    
    # Configurer Grafana si ce n'est pas déjà fait
    if ! kubectl get configmap grafana-dashboards -n "$NAMESPACE" &> /dev/null; then
        kubectl create configmap grafana-dashboards \
            --from-file="${PROJECT_ROOT}/infrastructure/monitoring/grafana/dashboards/" \
            --namespace="$NAMESPACE"
    fi
    
    log_info "Monitoring configuré"
}

apply_security_policies() {
    log_step "Application des politiques de sécurité..."
    
    # RBAC
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/security/rbac/" -n "$NAMESPACE"
    
    # Network Policies
    kubectl apply -f "${PROJECT_ROOT}/infrastructure/security/policies/" -n "$NAMESPACE"
    
    log_info "Politiques de sécurité appliquées"
}

run_database_migrations() {
    log_step "Exécution des migrations de base de données..."
    
    # Attendre que PostgreSQL soit prêt
    kubectl wait --for=condition=ready pod -l app=postgres -n "$NAMESPACE" --timeout=300s
    
    # Exécuter les migrations
    kubectl run db-migrate-${VERSION} \
        --image="$IMAGE_TAG" \
        --rm -i --restart=Never \
        --namespace="$NAMESPACE" \
        --command -- python -m alembic upgrade head
    
    log_info "Migrations exécutées"
}

warm_up_services() {
    log_step "Préchauffage des services..."
    
    # Attendre que tous les pods soient prêts
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=rag-system -n "$NAMESPACE" --timeout=600s
    
    # Appels de warm-up
    local api_url
    if [ "$ENVIRONMENT" = "production" ]; then
        api_url="https://api.rag-system.com"
    else
        api_url="https://${ENVIRONMENT}-api.rag-system.com"
    fi
    
    # Health check
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -f "${api_url}/health" &> /dev/null; then
            log_info "API accessible"
            break
        fi
        retries=$((retries + 1))
        log_info "Attente de l'API... (tentative $retries/10)"
        sleep 30
    done
    
    # Préchargement du cache
    kubectl exec deployment/rag-api -n "$NAMESPACE" -- python -c "
from core.cache import warm_cache
warm_cache(['models', 'embeddings'])
"
    
    log_info "Services préchauffés"
}

run_smoke_tests() {
    log_step "Exécution des tests de fumée..."
    
    # Lancer les tests de base
    kubectl run smoke-tests-${VERSION} \
        --image="$IMAGE_TAG" \
        --rm -i --restart=Never \
        --namespace="$NAMESPACE" \
        --command -- python -m pytest tests/smoke/ -v
    
    log_info "Tests de fumée réussis"
}

rollback_deployment() {
    log_error "Rollback vers la version $PREVIOUS_VERSION..."
    
    if [ "$PREVIOUS_VERSION" != "none" ]; then
        helm rollback rag-system -n "$NAMESPACE"
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=rag-system -n "$NAMESPACE" --timeout=300s
        log_info "Rollback terminé"
    else
        log_warn "Aucune version précédente disponible pour le rollback"
    fi
}

update_status_page() {
    log_step "Mise à jour de la page de statut..."
    
    # Notifier la page de statut du déploiement
    if [ -n "${STATUS_PAGE_API_KEY:-}" ]; then
        curl -X POST "https://api.statuspage.io/v1/pages/${STATUS_PAGE_ID}/incidents" \
            -H "Authorization: OAuth ${STATUS_PAGE_API_KEY}" \
            -H "Content-Type: application/json" \
            -d "{
                \"incident\": {
                    \"name\": \"Déploiement ${ENVIRONMENT} - Version ${VERSION}\",
                    \"status\": \"resolved\",
                    \"impact_override\": \"none\",
                    \"body\": \"Déploiement réussi de la version ${VERSION} en ${ENVIRONMENT}\"
                }
            }"
    fi
    
    log_info "Page de statut mise à jour"
}

send_notifications() {
    log_step "Envoi des notifications..."
    
    # Slack notification
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            --data "{
                \"text\": \"✅ Déploiement réussi\",
                \"attachments\": [{
                    \"color\": \"good\",
                    \"fields\": [
                        {\"title\": \"Environnement\", \"value\": \"${ENVIRONMENT}\", \"short\": true},
                        {\"title\": \"Version\", \"value\": \"${VERSION}\", \"short\": true},
                        {\"title\": \"Déployé par\", \"value\": \"$(whoami)\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"$(date -u)\", \"short\": true}
                    ]
                }]
            }"
    fi
    
    log_info "Notifications envoyées"
}

generate_deployment_report() {
    local deployment_time=$1
    
    echo
    echo "==============================="
    echo "RAPPORT DE DÉPLOIEMENT"
    echo "==============================="
    echo "Environnement: $ENVIRONMENT"
    echo "Version: $VERSION"
    echo "Version précédente: $PREVIOUS_VERSION"
    echo "Namespace: $NAMESPACE"
    echo "Durée: ${deployment_time}s"
    echo "Déployé par: $(whoami)"
    echo "Timestamp: $(date -u)"
    echo
    echo "Services déployés:"
    kubectl get pods -n "$NAMESPACE" -o custom-columns="NAME:.metadata.name,STATUS:.status.phase,AGE:.metadata.creationTimestamp"
    echo
    echo "URL d'accès:"
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "  API: https://api.rag-system.com"
        echo "  Docs: https://api.rag-system.com/docs"
    else
        echo "  API: https://${ENVIRONMENT}-api.rag-system.com"
        echo "  Docs: https://${ENVIRONMENT}-api.rag-system.com/docs"
    fi
    echo
}

main() {
    local start_time=$(date +%s)
    
    echo "🚀 Déploiement du Système RAG"
    echo "============================="
    echo "Environnement: $ENVIRONMENT"
    echo "Version: $VERSION"
    echo "Namespace: $NAMESPACE"
    echo
    
    validate_environment
    prepare_namespace
    
    if [ "$VERSION" != "latest" ] && [ "$VERSION" != "current" ]; then
        build_and_push_images
    fi
    
    apply_secrets
    apply_security_policies
    deploy_with_helm
    apply_monitoring
    run_database_migrations
    warm_up_services
    run_smoke_tests
    update_status_page
    send_notifications
    
    local end_time=$(date +%s)
    local deployment_time=$((end_time - start_time))
    
    generate_deployment_report $deployment_time
    
    log_info "🎉 Déploiement terminé avec succès en ${deployment_time}s!"
}

# Exécution du script
main "$@"
