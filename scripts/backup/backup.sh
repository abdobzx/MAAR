#!/bin/bash

# Script de sauvegarde automatisée pour le système RAG
# Usage: ./backup.sh [environment] [backup-type]

set -euo pipefail

ENVIRONMENT=${1:-production}
BACKUP_TYPE=${2:-full}  # full, incremental, config-only
NAMESPACE="rag-${ENVIRONMENT}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backup/rag-system/${ENVIRONMENT}/${TIMESTAMP}"
S3_BUCKET="rag-backups-${ENVIRONMENT}"

# Configuration
RETENTION_DAYS=30
POSTGRES_DATABASE="rag_db"
REDIS_SNAPSHOT_INTERVAL=3600

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
        log_error "Sauvegarde échouée. Nettoyage..."
        rm -rf "${BACKUP_DIR}" 2>/dev/null || true
    fi
}

trap cleanup EXIT

validate_prerequisites() {
    log_step "Validation des prérequis..."
    
    # Vérifier les outils requis
    local required_tools=("kubectl" "pg_dump" "aws" "tar" "gzip")
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
    
    # Vérifier l'accès S3
    if ! aws s3 ls "s3://${S3_BUCKET}" &> /dev/null; then
        log_warn "Bucket S3 non accessible, création en cours..."
        aws s3 mb "s3://${S3_BUCKET}"
    fi
    
    # Créer le répertoire de sauvegarde
    mkdir -p "$BACKUP_DIR"
    
    log_info "Prérequis validés"
}

backup_database() {
    log_step "Sauvegarde de la base de données PostgreSQL..."
    
    local db_backup_file="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql"
    
    # Dump complet de la base de données
    kubectl exec deployment/postgres -n "$NAMESPACE" -- pg_dump \
        -U postgres \
        -d "$POSTGRES_DATABASE" \
        --verbose \
        --clean \
        --if-exists \
        --create \
        --encoding=UTF8 \
        > "$db_backup_file"
    
    # Compression
    gzip "$db_backup_file"
    
    # Vérification de l'intégrité
    if [ -f "${db_backup_file}.gz" ]; then
        local size=$(stat -f%z "${db_backup_file}.gz" 2>/dev/null || stat -c%s "${db_backup_file}.gz")
        log_info "Base de données sauvegardée: ${size} bytes"
    else
        log_error "Échec de la sauvegarde de la base de données"
        return 1
    fi
}

backup_redis() {
    log_step "Sauvegarde de Redis..."
    
    local redis_backup_file="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
    
    # Forcer un snapshot Redis
    kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli BGSAVE
    
    # Attendre que le snapshot soit terminé
    while true; do
        local lastsave=$(kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli LASTSAVE)
        sleep 5
        local current_lastsave=$(kubectl exec deployment/redis -n "$NAMESPACE" -- redis-cli LASTSAVE)
        if [ "$lastsave" != "$current_lastsave" ]; then
            break
        fi
    done
    
    # Copier le fichier RDB
    kubectl cp "${NAMESPACE}/$(kubectl get pod -l app=redis -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}'):/data/dump.rdb" "$redis_backup_file"
    
    # Compression
    gzip "$redis_backup_file"
    
    log_info "Redis sauvegardé"
}

backup_vector_database() {
    log_step "Sauvegarde de Qdrant..."
    
    local qdrant_backup_dir="${BACKUP_DIR}/qdrant"
    mkdir -p "$qdrant_backup_dir"
    
    # Créer un snapshot Qdrant
    local collections=$(kubectl exec deployment/qdrant -n "$NAMESPACE" -- curl -s localhost:6333/collections | jq -r '.result.collections[].name')
    
    for collection in $collections; do
        log_info "Sauvegarde de la collection: $collection"
        
        # Créer un snapshot de la collection
        kubectl exec deployment/qdrant -n "$NAMESPACE" -- curl -X POST \
            "localhost:6333/collections/${collection}/snapshots"
        
        # Récupérer la liste des snapshots
        local snapshots=$(kubectl exec deployment/qdrant -n "$NAMESPACE" -- curl -s \
            "localhost:6333/collections/${collection}/snapshots" | jq -r '.result[].name' | tail -1)
        
        if [ -n "$snapshots" ]; then
            # Télécharger le snapshot
            kubectl exec deployment/qdrant -n "$NAMESPACE" -- curl -s \
                "localhost:6333/collections/${collection}/snapshots/${snapshots}" \
                > "${qdrant_backup_dir}/${collection}_${snapshots}"
        fi
    done
    
    # Compression du répertoire
    tar -czf "${qdrant_backup_dir}.tar.gz" -C "$BACKUP_DIR" qdrant
    rm -rf "$qdrant_backup_dir"
    
    log_info "Qdrant sauvegardé"
}

backup_configurations() {
    log_step "Sauvegarde des configurations Kubernetes..."
    
    local config_backup_dir="${BACKUP_DIR}/kubernetes"
    mkdir -p "$config_backup_dir"
    
    # Sauvegarder les ConfigMaps
    kubectl get configmaps -n "$NAMESPACE" -o yaml > "${config_backup_dir}/configmaps.yaml"
    
    # Sauvegarder les Secrets (attention: contient des données sensibles)
    kubectl get secrets -n "$NAMESPACE" -o yaml > "${config_backup_dir}/secrets.yaml"
    
    # Sauvegarder les Deployments
    kubectl get deployments -n "$NAMESPACE" -o yaml > "${config_backup_dir}/deployments.yaml"
    
    # Sauvegarder les Services
    kubectl get services -n "$NAMESPACE" -o yaml > "${config_backup_dir}/services.yaml"
    
    # Sauvegarder les Ingress
    kubectl get ingress -n "$NAMESPACE" -o yaml > "${config_backup_dir}/ingress.yaml"
    
    # Sauvegarder les PVCs
    kubectl get pvc -n "$NAMESPACE" -o yaml > "${config_backup_dir}/pvc.yaml"
    
    # Sauvegarder les configurations Helm
    helm get values rag-system -n "$NAMESPACE" -o yaml > "${config_backup_dir}/helm-values.yaml"
    
    # Compression
    tar -czf "${config_backup_dir}.tar.gz" -C "$BACKUP_DIR" kubernetes
    rm -rf "$config_backup_dir"
    
    log_info "Configurations sauvegardées"
}

backup_application_data() {
    log_step "Sauvegarde des données applicatives..."
    
    local app_backup_dir="${BACKUP_DIR}/application"
    mkdir -p "$app_backup_dir"
    
    # Sauvegarder les logs récents
    kubectl logs deployment/rag-api -n "$NAMESPACE" --since=24h > "${app_backup_dir}/api-logs.txt" 2>/dev/null || true
    kubectl logs deployment/rag-celery -n "$NAMESPACE" --since=24h > "${app_backup_dir}/celery-logs.txt" 2>/dev/null || true
    
    # Sauvegarder les métriques Prometheus (si disponible)
    if kubectl get pod -l app.kubernetes.io/name=prometheus -n "$NAMESPACE" &> /dev/null; then
        kubectl exec deployment/prometheus -n "$NAMESPACE" -- tar -czf - /prometheus/data 2>/dev/null > "${app_backup_dir}/prometheus-data.tar.gz" || true
    fi
    
    # Sauvegarder les fichiers uploadés (MinIO/S3)
    if command -v aws &> /dev/null && [ -n "${MINIO_BUCKET:-}" ]; then
        aws s3 sync "s3://${MINIO_BUCKET}" "${app_backup_dir}/files/"
    fi
    
    # Compression
    tar -czf "${app_backup_dir}.tar.gz" -C "$BACKUP_DIR" application
    rm -rf "$app_backup_dir"
    
    log_info "Données applicatives sauvegardées"
}

create_backup_manifest() {
    log_step "Création du manifeste de sauvegarde..."
    
    local manifest_file="${BACKUP_DIR}/backup_manifest.json"
    
    # Collecter les métadonnées
    local db_size=$(stat -f%z "${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz" 2>/dev/null || stat -c%s "${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz")
    local redis_size=$(stat -f%z "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb.gz" 2>/dev/null || stat -c%s "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb.gz")
    
    cat > "$manifest_file" <<EOF
{
    "backup_id": "${TIMESTAMP}",
    "environment": "${ENVIRONMENT}",
    "backup_type": "${BACKUP_TYPE}",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "components": {
        "database": {
            "type": "postgresql",
            "size_bytes": ${db_size},
            "file": "postgres_${TIMESTAMP}.sql.gz"
        },
        "cache": {
            "type": "redis",
            "size_bytes": ${redis_size},
            "file": "redis_${TIMESTAMP}.rdb.gz"
        },
        "vector_db": {
            "type": "qdrant",
            "file": "qdrant.tar.gz"
        },
        "configurations": {
            "type": "kubernetes",
            "file": "kubernetes.tar.gz"
        },
        "application_data": {
            "type": "mixed",
            "file": "application.tar.gz"
        }
    },
    "kubernetes": {
        "namespace": "${NAMESPACE}",
        "cluster": "$(kubectl config current-context)"
    },
    "retention": {
        "expire_date": "$(date -u -d "+${RETENTION_DAYS} days" +"%Y-%m-%dT%H:%M:%SZ")"
    }
}
EOF
    
    log_info "Manifeste créé"
}

upload_to_s3() {
    log_step "Upload vers S3..."
    
    # Créer une archive complète
    local archive_name="rag_backup_${ENVIRONMENT}_${TIMESTAMP}.tar.gz"
    local archive_path="/tmp/${archive_name}"
    
    tar -czf "$archive_path" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
    
    # Upload vers S3
    aws s3 cp "$archive_path" "s3://${S3_BUCKET}/${archive_name}" \
        --metadata environment="$ENVIRONMENT",backup-type="$BACKUP_TYPE",timestamp="$TIMESTAMP"
    
    # Vérifier l'upload
    if aws s3 ls "s3://${S3_BUCKET}/${archive_name}" &> /dev/null; then
        local s3_size=$(aws s3 ls "s3://${S3_BUCKET}/${archive_name}" | awk '{print $3}')
        log_info "Sauvegarde uploadée vers S3: ${s3_size} bytes"
    else
        log_error "Échec de l'upload vers S3"
        return 1
    fi
    
    # Nettoyage local
    rm -f "$archive_path"
}

cleanup_old_backups() {
    log_step "Nettoyage des anciennes sauvegardes..."
    
    # Nettoyage local
    find "/backup/rag-system/${ENVIRONMENT}" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true
    
    # Nettoyage S3
    local cutoff_date=$(date -u -d "-${RETENTION_DAYS} days" +"%Y-%m-%d")
    aws s3 ls "s3://${S3_BUCKET}/" | while read -r line; do
        local file_date=$(echo "$line" | awk '{print $1}')
        local file_name=$(echo "$line" | awk '{print $4}')
        
        if [[ "$file_date" < "$cutoff_date" ]]; then
            log_info "Suppression de l'ancienne sauvegarde: $file_name"
            aws s3 rm "s3://${S3_BUCKET}/${file_name}"
        fi
    done
    
    log_info "Nettoyage terminé"
}

verify_backup_integrity() {
    log_step "Vérification de l'intégrité de la sauvegarde..."
    
    local errors=0
    
    # Vérifier que tous les fichiers attendus existent
    local expected_files=(
        "postgres_${TIMESTAMP}.sql.gz"
        "redis_${TIMESTAMP}.rdb.gz"
        "qdrant.tar.gz"
        "kubernetes.tar.gz"
        "application.tar.gz"
        "backup_manifest.json"
    )
    
    for file in "${expected_files[@]}"; do
        if [ ! -f "${BACKUP_DIR}/${file}" ]; then
            log_error "Fichier manquant: $file"
            errors=$((errors + 1))
        fi
    done
    
    # Vérifier l'intégrité des archives
    for archive in "${BACKUP_DIR}"/*.tar.gz; do
        if [ -f "$archive" ]; then
            if ! tar -tzf "$archive" &> /dev/null; then
                log_error "Archive corrompue: $(basename "$archive")"
                errors=$((errors + 1))
            fi
        fi
    done
    
    # Vérifier l'intégrité des fichiers gzip
    for gzfile in "${BACKUP_DIR}"/*.gz; do
        if [ -f "$gzfile" ] && [[ ! "$gzfile" =~ \.tar\.gz$ ]]; then
            if ! gzip -t "$gzfile" &> /dev/null; then
                log_error "Fichier gzip corrompu: $(basename "$gzfile")"
                errors=$((errors + 1))
            fi
        fi
    done
    
    if [ $errors -eq 0 ]; then
        log_info "Vérification d'intégrité réussie"
        return 0
    else
        log_error "$errors erreurs détectées lors de la vérification"
        return 1
    fi
}

send_notification() {
    local status=$1
    local duration=$2
    
    log_step "Envoi de notification..."
    
    # Slack notification
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local color="good"
        local emoji="✅"
        if [ "$status" != "success" ]; then
            color="danger"
            emoji="❌"
        fi
        
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            --data "{
                \"text\": \"${emoji} Sauvegarde ${status}\",
                \"attachments\": [{
                    \"color\": \"${color}\",
                    \"fields\": [
                        {\"title\": \"Environnement\", \"value\": \"${ENVIRONMENT}\", \"short\": true},
                        {\"title\": \"Type\", \"value\": \"${BACKUP_TYPE}\", \"short\": true},
                        {\"title\": \"Durée\", \"value\": \"${duration}s\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"${TIMESTAMP}\", \"short\": true}
                    ]
                }]
            }"
    fi
}

generate_backup_report() {
    local status=$1
    local duration=$2
    
    echo
    echo "==============================="
    echo "RAPPORT DE SAUVEGARDE"
    echo "==============================="
    echo "Environnement: $ENVIRONMENT"
    echo "Type: $BACKUP_TYPE"
    echo "Timestamp: $TIMESTAMP"
    echo "Durée: ${duration}s"
    echo "Statut: $status"
    echo
    echo "Composants sauvegardés:"
    if [ -f "${BACKUP_DIR}/backup_manifest.json" ]; then
        jq -r '.components | to_entries[] | "  \(.key): \(.value.file)"' "${BACKUP_DIR}/backup_manifest.json"
    fi
    echo
    echo "Localisation:"
    echo "  Local: $BACKUP_DIR"
    echo "  S3: s3://${S3_BUCKET}/rag_backup_${ENVIRONMENT}_${TIMESTAMP}.tar.gz"
    echo
    
    if [ "$status" = "success" ]; then
        echo "✅ Sauvegarde terminée avec succès"
    else
        echo "❌ Sauvegarde échouée"
    fi
}

main() {
    local start_time=$(date +%s)
    local status="success"
    
    echo "💾 Sauvegarde du Système RAG"
    echo "============================"
    echo "Environnement: $ENVIRONMENT"
    echo "Type: $BACKUP_TYPE"
    echo "Timestamp: $TIMESTAMP"
    echo
    
    validate_prerequisites
    
    case "$BACKUP_TYPE" in
        "full")
            backup_database
            backup_redis
            backup_vector_database
            backup_configurations
            backup_application_data
            ;;
        "incremental")
            backup_database
            backup_configurations
            ;;
        "config-only")
            backup_configurations
            ;;
        *)
            log_error "Type de sauvegarde non supporté: $BACKUP_TYPE"
            exit 1
            ;;
    esac
    
    create_backup_manifest
    
    if verify_backup_integrity; then
        upload_to_s3
        cleanup_old_backups
    else
        status="failed"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    send_notification "$status" "$duration"
    generate_backup_report "$status" "$duration"
    
    if [ "$status" = "success" ]; then
        log_info "🎉 Sauvegarde terminée avec succès en ${duration}s!"
    else
        log_error "💥 Sauvegarde échouée après ${duration}s"
        exit 1
    fi
}

# Exécution du script
main "$@"
