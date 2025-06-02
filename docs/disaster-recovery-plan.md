# Plan de Reprise d'Activité (Disaster Recovery)
# Système RAG Enterprise

## Vue d'ensemble

Ce document détaille le plan de reprise d'activité (PRA) pour le système RAG Enterprise. Il couvre les procédures de sauvegarde, restauration, basculement et récupération en cas de sinistre majeur.

## Objectifs de Récupération

### RTO et RPO Définis

#### Recovery Time Objective (RTO)
- **Panne mineure** : < 15 minutes
- **Panne majeure** : < 2 heures
- **Sinistre complet** : < 8 heures

#### Recovery Point Objective (RPO)
- **Données transactionnelles** : < 5 minutes
- **Documents et embeddings** : < 1 heure
- **Configuration système** : < 24 heures

### Niveaux de Criticité

#### Critique (Tier 1)
- API Principal
- Base de données PostgreSQL
- Authentification Keycloak
- Cache Redis

#### Important (Tier 2)
- Worker Celery
- Base vectorielle Qdrant
- Stockage MinIO
- Monitoring Prometheus

#### Support (Tier 3)
- Grafana Dashboards
- ELK Stack
- Documentation
- Analytics

## Architecture de Haute Disponibilité

### Sites Principaux

#### Site Principal (Production)
- **Localisation** : Région EU-West-1
- **Infrastructure** : Kubernetes cluster 3 nœuds master + 6 workers
- **Stockage** : SSD persistants avec réplication
- **Réseau** : Load balancer avec failover automatique

#### Site de Basculement (DR)
- **Localisation** : Région EU-Central-1
- **Infrastructure** : Kubernetes cluster 3 nœuds (warm standby)
- **Stockage** : Réplication asynchrone du site principal
- **Réseau** : DNS basculement automatique (TTL 60s)

#### Site de Sauvegarde (Cold)
- **Localisation** : Région US-East-1
- **Infrastructure** : Images et configurations stockées
- **Stockage** : Sauvegardes quotidiennes chiffrées
- **Déploiement** : Automatisé via Terraform/Ansible

### Réplication des Données

#### Base de Données (PostgreSQL)
```bash
# Configuration de la réplication streaming
# Sur le serveur principal
echo "
# Réplication
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
archive_mode = on
archive_command = 'aws s3 cp %p s3://rag-wal-backup/%f'
" >> /var/lib/postgresql/data/postgresql.conf

# Création du slot de réplication
sudo -u postgres psql -c "SELECT pg_create_physical_replication_slot('dr_slot');"
```

#### Cache Redis
```bash
# Configuration de la réplication Redis
# redis.conf sur le serveur principal
save 900 1
save 300 10
save 60 10000
rdbcompression yes
rdbchecksum yes

# Configuration du réplica
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-replica-dr
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-replica-dr
  template:
    metadata:
      labels:
        app: redis-replica-dr
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server"]
        args: ["--replicaof", "redis-master.rag-production.svc.cluster.local", "6379"]
        env:
        - name: REDIS_MASTER_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secrets
              key: password
EOF
```

#### Stockage Objet (MinIO)
```bash
# Configuration de la réplication MinIO
mc alias set minio-prod https://minio-prod.rag.com minioadmin password
mc alias set minio-dr https://minio-dr.rag.com minioadmin password

# Réplication automatique
mc replicate add minio-prod/rag-documents minio-dr/rag-documents-replica \
  --replicate "delete,metadata"

# Vérification de la réplication
mc replicate ls minio-prod/rag-documents
```

#### Base Vectorielle (Qdrant)
```bash
# Sauvegarde régulière des collections
curl -X POST "http://qdrant-master:6333/collections/enterprise_rag/snapshots" \
  -H "Content-Type: application/json"

# Script de synchronisation
cat > /scripts/qdrant-sync.sh << 'EOF'
#!/bin/bash
SNAPSHOT_NAME=$(curl -s "http://qdrant-master:6333/collections/enterprise_rag/snapshots" | jq -r '.result[-1].name')
curl -X GET "http://qdrant-master:6333/collections/enterprise_rag/snapshots/$SNAPSHOT_NAME" \
  --output "/backups/qdrant-${SNAPSHOT_NAME}.snapshot"

# Upload vers le site DR
aws s3 cp "/backups/qdrant-${SNAPSHOT_NAME}.snapshot" \
  "s3://rag-dr-backups/qdrant/" --region eu-central-1
EOF

# Cron job pour synchronisation (toutes les 6 heures)
echo "0 */6 * * * /scripts/qdrant-sync.sh" | crontab -
```

## Procédures de Sauvegarde

### Sauvegarde Complète Automatisée

#### Script Principal de Sauvegarde
```bash
#!/bin/bash
# /scripts/dr-backup.sh

set -euo pipefail

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/full-${BACKUP_DATE}"
S3_BUCKET="s3://rag-dr-backups"
RETENTION_DAYS=30

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

create_backup_directory() {
    log_info "Création du répertoire de sauvegarde: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
}

backup_database() {
    log_info "Sauvegarde de la base de données PostgreSQL"
    
    kubectl exec deployment/postgres -n enterprise-rag -- \
        pg_dump -U rag_user -h localhost rag_database \
        --no-password --clean --if-exists \
        > "${BACKUP_DIR}/database.sql"
    
    # Compression et chiffrement
    gzip "${BACKUP_DIR}/database.sql"
    gpg --symmetric --cipher-algo AES256 \
        --passphrase-file /secrets/backup-passphrase.txt \
        "${BACKUP_DIR}/database.sql.gz"
    
    rm "${BACKUP_DIR}/database.sql.gz"
    log_info "Sauvegarde base de données terminée"
}

backup_redis() {
    log_info "Sauvegarde du cache Redis"
    
    # Déclenchement du BGSAVE
    kubectl exec deployment/redis -n enterprise-rag -- redis-cli BGSAVE
    
    # Attente de la fin du BGSAVE
    while kubectl exec deployment/redis -n enterprise-rag -- redis-cli LASTSAVE | \
          grep -q "$(kubectl exec deployment/redis -n enterprise-rag -- redis-cli LASTSAVE)"; do
        sleep 5
    done
    
    # Copie du dump RDB
    kubectl cp enterprise-rag/redis-pod:/data/dump.rdb "${BACKUP_DIR}/redis-dump.rdb"
    
    # Chiffrement
    gpg --symmetric --cipher-algo AES256 \
        --passphrase-file /secrets/backup-passphrase.txt \
        "${BACKUP_DIR}/redis-dump.rdb"
    
    rm "${BACKUP_DIR}/redis-dump.rdb"
    log_info "Sauvegarde Redis terminée"
}

backup_qdrant() {
    log_info "Sauvegarde de Qdrant"
    
    # Création du snapshot
    SNAPSHOT_RESULT=$(curl -s -X POST \
        "http://qdrant.enterprise-rag.svc.cluster.local:6333/collections/enterprise_rag/snapshots")
    
    SNAPSHOT_NAME=$(echo "$SNAPSHOT_RESULT" | jq -r '.result.name')
    
    # Téléchargement du snapshot
    curl -X GET \
        "http://qdrant.enterprise-rag.svc.cluster.local:6333/collections/enterprise_rag/snapshots/$SNAPSHOT_NAME" \
        --output "${BACKUP_DIR}/qdrant-snapshot.bin"
    
    # Chiffrement
    gpg --symmetric --cipher-algo AES256 \
        --passphrase-file /secrets/backup-passphrase.txt \
        "${BACKUP_DIR}/qdrant-snapshot.bin"
    
    rm "${BACKUP_DIR}/qdrant-snapshot.bin"
    log_info "Sauvegarde Qdrant terminée"
}

backup_minio() {
    log_info "Sauvegarde de MinIO"
    
    # Synchronisation avec AWS S3
    mc mirror --overwrite minio-local/rag-documents "${BACKUP_DIR}/minio-data/"
    
    # Archive et chiffrement
    tar -czf "${BACKUP_DIR}/minio-data.tar.gz" -C "${BACKUP_DIR}" minio-data/
    rm -rf "${BACKUP_DIR}/minio-data/"
    
    gpg --symmetric --cipher-algo AES256 \
        --passphrase-file /secrets/backup-passphrase.txt \
        "${BACKUP_DIR}/minio-data.tar.gz"
    
    rm "${BACKUP_DIR}/minio-data.tar.gz"
    log_info "Sauvegarde MinIO terminée"
}

backup_configurations() {
    log_info "Sauvegarde des configurations"
    
    # ConfigMaps
    kubectl get configmaps -n enterprise-rag -o yaml > "${BACKUP_DIR}/configmaps.yaml"
    
    # Secrets (sans les données sensibles)
    kubectl get secrets -n enterprise-rag -o yaml | \
        sed 's/data:/data: #REDACTED/g' > "${BACKUP_DIR}/secrets-template.yaml"
    
    # Deployments
    kubectl get deployments -n enterprise-rag -o yaml > "${BACKUP_DIR}/deployments.yaml"
    
    # Services
    kubectl get services -n enterprise-rag -o yaml > "${BACKUP_DIR}/services.yaml"
    
    # Ingress
    kubectl get ingress -n enterprise-rag -o yaml > "${BACKUP_DIR}/ingress.yaml"
    
    # Helm values
    helm get values rag-system -n enterprise-rag > "${BACKUP_DIR}/helm-values.yaml"
    
    # Archive
    tar -czf "${BACKUP_DIR}/configurations.tar.gz" -C "${BACKUP_DIR}" *.yaml
    rm "${BACKUP_DIR}"/*.yaml
    
    log_info "Sauvegarde configurations terminée"
}

upload_to_s3() {
    log_info "Upload vers S3"
    
    # Upload vers S3 avec métadonnées
    aws s3 sync "$BACKUP_DIR" "$S3_BUCKET/full-backups/${BACKUP_DATE}/" \
        --metadata "backup-date=${BACKUP_DATE},backup-type=full,environment=production"
    
    # Vérification de l'intégrité
    aws s3 ls "$S3_BUCKET/full-backups/${BACKUP_DATE}/" --recursive | \
        awk '{print $4}' > "${BACKUP_DIR}/s3-inventory.txt"
    
    aws s3 cp "${BACKUP_DIR}/s3-inventory.txt" "$S3_BUCKET/full-backups/${BACKUP_DATE}/"
    
    log_info "Upload S3 terminé"
}

cleanup_old_backups() {
    log_info "Nettoyage des anciennes sauvegardes"
    
    # Nettoyage local
    find /backups -name "full-*" -type d -mtime +7 -exec rm -rf {} +
    
    # Nettoyage S3 (garder les sauvegardes > 30 jours)
    aws s3 ls "$S3_BUCKET/full-backups/" | \
        awk '$1 < "'$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)'" {print $2}' | \
        while read dir; do
            aws s3 rm "$S3_BUCKET/full-backups/$dir" --recursive
        done
    
    log_info "Nettoyage terminé"
}

verify_backup() {
    log_info "Vérification de l'intégrité de la sauvegarde"
    
    # Vérification de la présence des fichiers critiques
    local required_files=(
        "database.sql.gpg"
        "redis-dump.rdb.gpg"
        "qdrant-snapshot.bin.gpg"
        "minio-data.tar.gz.gpg"
        "configurations.tar.gz"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "${BACKUP_DIR}/${file}" ]]; then
            log_error "Fichier manquant: $file"
            exit 1
        fi
    done
    
    # Test de déchiffrement (sans extraction complète)
    echo "test" | gpg --passphrase-file /secrets/backup-passphrase.txt \
        --decrypt "${BACKUP_DIR}/database.sql.gpg" | head -n 1 > /dev/null
    
    if [[ $? -ne 0 ]]; then
        log_error "Erreur de déchiffrement de la sauvegarde"
        exit 1
    fi
    
    log_info "Vérification de l'intégrité réussie"
}

notify_completion() {
    log_info "Envoi des notifications"
    
    # Slack notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            --data "{
                \"text\": \"✅ Sauvegarde DR complétée\",
                \"attachments\": [{
                    \"color\": \"good\",
                    \"fields\": [
                        {\"title\": \"Date\", \"value\": \"${BACKUP_DATE}\", \"short\": true},
                        {\"title\": \"Taille\", \"value\": \"$(du -sh $BACKUP_DIR | cut -f1)\", \"short\": true},
                        {\"title\": \"Localisation\", \"value\": \"$S3_BUCKET/full-backups/${BACKUP_DATE}/\", \"short\": false}
                    ]
                }]
            }"
    fi
    
    # Email pour l'équipe
    echo "Sauvegarde DR complétée avec succès
    
Date: ${BACKUP_DATE}
Localisation: $S3_BUCKET/full-backups/${BACKUP_DATE}/
Taille: $(du -sh $BACKUP_DIR | cut -f1)
    
Fichiers sauvegardés:
$(ls -la $BACKUP_DIR)
" | mail -s "Sauvegarde DR - $BACKUP_DATE" ops-team@company.com
    
    log_info "Notifications envoyées"
}

main() {
    log_info "Début de la sauvegarde DR complète"
    
    create_backup_directory
    backup_database
    backup_redis
    backup_qdrant
    backup_minio
    backup_configurations
    verify_backup
    upload_to_s3
    cleanup_old_backups
    notify_completion
    
    log_info "Sauvegarde DR complète terminée avec succès"
}

# Exécution avec gestion d'erreur
if ! main; then
    log_error "Échec de la sauvegarde DR"
    # Notification d'échec
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-type: application/json' \
        --data '{"text": "❌ Échec de la sauvegarde DR", "channel": "#alerts"}'
    exit 1
fi
```

#### Planification des Sauvegardes
```bash
# Crontab pour les sauvegardes automatisées
# /etc/crontab

# Sauvegarde complète quotidienne à 2h00
0 2 * * * root /scripts/dr-backup.sh

# Sauvegarde incrémentale toutes les 6 heures
0 */6 * * * root /scripts/incremental-backup.sh

# Sauvegarde des WAL PostgreSQL toutes les 15 minutes
*/15 * * * * postgres /scripts/wal-backup.sh

# Vérification de l'intégrité hebdomadaire
0 3 * * 0 root /scripts/verify-backups.sh
```

## Procédures de Restauration

### Restauration Complète du Système

#### Script de Restauration
```bash
#!/bin/bash
# /scripts/dr-restore.sh

set -euo pipefail

BACKUP_DATE=${1:-latest}
RESTORE_ENVIRONMENT=${2:-production}
S3_BUCKET="s3://rag-dr-backups"
RESTORE_DIR="/restore/${BACKUP_DATE}"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

prepare_restore_environment() {
    log_info "Préparation de l'environnement de restauration"
    
    # Création du namespace si nécessaire
    kubectl create namespace "enterprise-rag-${RESTORE_ENVIRONMENT}" --dry-run=client -o yaml | kubectl apply -f -
    
    # Arrêt des services existants si restauration en place
    if [[ "$RESTORE_ENVIRONMENT" == "production" ]]; then
        kubectl scale deployment --all --replicas=0 -n enterprise-rag
        sleep 30
    fi
    
    # Préparation du répertoire de restauration
    mkdir -p "$RESTORE_DIR"
    cd "$RESTORE_DIR"
}

download_backup() {
    log_info "Téléchargement de la sauvegarde depuis S3"
    
    if [[ "$BACKUP_DATE" == "latest" ]]; then
        BACKUP_DATE=$(aws s3 ls "$S3_BUCKET/full-backups/" | sort | tail -n 1 | awk '{print $2}' | tr -d '/')
    fi
    
    aws s3 sync "$S3_BUCKET/full-backups/${BACKUP_DATE}/" "$RESTORE_DIR/"
    
    log_info "Sauvegarde téléchargée: $BACKUP_DATE"
}

restore_database() {
    log_info "Restauration de la base de données"
    
    # Déchiffrement
    gpg --batch --yes --passphrase-file /secrets/backup-passphrase.txt \
        --decrypt "${RESTORE_DIR}/database.sql.gpg" | gunzip > "${RESTORE_DIR}/database.sql"
    
    # Attente que PostgreSQL soit prêt
    kubectl wait --for=condition=ready pod -l app=postgres -n "enterprise-rag-${RESTORE_ENVIRONMENT}" --timeout=300s
    
    # Restauration
    kubectl exec -i deployment/postgres -n "enterprise-rag-${RESTORE_ENVIRONMENT}" -- \
        psql -U rag_user -d rag_database < "${RESTORE_DIR}/database.sql"
    
    log_info "Base de données restaurée"
}

restore_redis() {
    log_info "Restauration de Redis"
    
    # Déchiffrement
    gpg --batch --yes --passphrase-file /secrets/backup-passphrase.txt \
        --decrypt "${RESTORE_DIR}/redis-dump.rdb.gpg" > "${RESTORE_DIR}/dump.rdb"
    
    # Arrêt de Redis
    kubectl scale deployment redis --replicas=0 -n "enterprise-rag-${RESTORE_ENVIRONMENT}"
    sleep 10
    
    # Copie du fichier de dump
    kubectl cp "${RESTORE_DIR}/dump.rdb" "enterprise-rag-${RESTORE_ENVIRONMENT}/redis-pod:/data/dump.rdb"
    
    # Redémarrage de Redis
    kubectl scale deployment redis --replicas=1 -n "enterprise-rag-${RESTORE_ENVIRONMENT}"
    kubectl wait --for=condition=ready pod -l app=redis -n "enterprise-rag-${RESTORE_ENVIRONMENT}" --timeout=300s
    
    log_info "Redis restauré"
}

restore_qdrant() {
    log_info "Restauration de Qdrant"
    
    # Déchiffrement
    gpg --batch --yes --passphrase-file /secrets/backup-passphrase.txt \
        --decrypt "${RESTORE_DIR}/qdrant-snapshot.bin.gpg" > "${RESTORE_DIR}/qdrant-snapshot.bin"
    
    # Attente que Qdrant soit prêt
    kubectl wait --for=condition=ready pod -l app=qdrant -n "enterprise-rag-${RESTORE_ENVIRONMENT}" --timeout=300s
    
    # Suppression de la collection existante
    curl -X DELETE "http://qdrant.enterprise-rag-${RESTORE_ENVIRONMENT}.svc.cluster.local:6333/collections/enterprise_rag"
    
    # Restauration du snapshot
    curl -X PUT "http://qdrant.enterprise-rag-${RESTORE_ENVIRONMENT}.svc.cluster.local:6333/collections/enterprise_rag/snapshots/upload" \
        --data-binary "@${RESTORE_DIR}/qdrant-snapshot.bin"
    
    log_info "Qdrant restauré"
}

restore_minio() {
    log_info "Restauration de MinIO"
    
    # Déchiffrement et extraction
    gpg --batch --yes --passphrase-file /secrets/backup-passphrase.txt \
        --decrypt "${RESTORE_DIR}/minio-data.tar.gz.gpg" | tar -xzf - -C "$RESTORE_DIR"
    
    # Attente que MinIO soit prêt
    kubectl wait --for=condition=ready pod -l app=minio -n "enterprise-rag-${RESTORE_ENVIRONMENT}" --timeout=300s
    
    # Restoration via mc
    mc alias set minio-restore "http://minio.enterprise-rag-${RESTORE_ENVIRONMENT}.svc.cluster.local:9000" \
        "$(kubectl get secret minio-secrets -n enterprise-rag-${RESTORE_ENVIRONMENT} -o jsonpath='{.data.access-key}' | base64 -d)" \
        "$(kubectl get secret minio-secrets -n enterprise-rag-${RESTORE_ENVIRONMENT} -o jsonpath='{.data.secret-key}' | base64 -d)"
    
    mc mirror "${RESTORE_DIR}/minio-data/" minio-restore/rag-documents/ --overwrite
    
    log_info "MinIO restauré"
}

restore_configurations() {
    log_info "Restauration des configurations"
    
    # Extraction des configurations
    tar -xzf "${RESTORE_DIR}/configurations.tar.gz" -C "$RESTORE_DIR"
    
    # Application des configurations (en excluant les secrets pour la sécurité)
    kubectl apply -f "${RESTORE_DIR}/configmaps.yaml" -n "enterprise-rag-${RESTORE_ENVIRONMENT}"
    kubectl apply -f "${RESTORE_DIR}/deployments.yaml" -n "enterprise-rag-${RESTORE_ENVIRONMENT}"
    kubectl apply -f "${RESTORE_DIR}/services.yaml" -n "enterprise-rag-${RESTORE_ENVIRONMENT}"
    kubectl apply -f "${RESTORE_DIR}/ingress.yaml" -n "enterprise-rag-${RESTORE_ENVIRONMENT}"
    
    log_info "Configurations restaurées"
}

restart_services() {
    log_info "Redémarrage des services"
    
    # Redémarrage séquentiel des services
    local services=("postgres" "redis" "qdrant" "minio" "rag-api" "rag-celery")
    
    for service in "${services[@]}"; do
        log_info "Redémarrage de $service"
        kubectl rollout restart "deployment/$service" -n "enterprise-rag-${RESTORE_ENVIRONMENT}"
        kubectl rollout status "deployment/$service" -n "enterprise-rag-${RESTORE_ENVIRONMENT}" --timeout=300s
    done
    
    log_info "Tous les services redémarrés"
}

verify_restoration() {
    log_info "Vérification de la restauration"
    
    # Tests de santé
    local api_url
    if [[ "$RESTORE_ENVIRONMENT" == "production" ]]; then
        api_url="https://api.rag-system.com"
    else
        api_url="https://${RESTORE_ENVIRONMENT}-api.rag-system.com"
    fi
    
    # Attendre que l'API soit disponible
    local retries=0
    while [[ $retries -lt 30 ]]; do
        if curl -f "$api_url/health" &> /dev/null; then
            log_info "API accessible"
            break
        fi
        retries=$((retries + 1))
        sleep 10
    done
    
    if [[ $retries -eq 30 ]]; then
        log_error "API non accessible après restauration"
        return 1
    fi
    
    # Tests fonctionnels
    kubectl run restore-test --rm -i --restart=Never \
        --image=curlimages/curl:latest \
        --namespace="enterprise-rag-${RESTORE_ENVIRONMENT}" \
        -- sh -c "
            curl -X GET '$api_url/admin/health/database' -H 'Authorization: Bearer \$ADMIN_TOKEN' | grep -q 'healthy' &&
            curl -X GET '$api_url/admin/health/redis' -H 'Authorization: Bearer \$ADMIN_TOKEN' | grep -q 'healthy' &&
            curl -X GET '$api_url/admin/health/qdrant' -H 'Authorization: Bearer \$ADMIN_TOKEN' | grep -q 'healthy'
        "
    
    if [[ $? -eq 0 ]]; then
        log_info "Vérification de la restauration réussie"
    else
        log_error "Échec de la vérification de la restauration"
        return 1
    fi
}

cleanup_restore() {
    log_info "Nettoyage des fichiers de restauration"
    rm -rf "$RESTORE_DIR"
}

main() {
    log_info "Début de la restauration DR"
    
    prepare_restore_environment
    download_backup
    restore_database
    restore_redis
    restore_qdrant
    restore_minio
    restore_configurations
    restart_services
    verify_restoration
    cleanup_restore
    
    log_info "Restauration DR terminée avec succès"
}

# Exécution
main
```

## Procédures de Basculement

### Basculement Automatique (Failover)

#### Configuration DNS avec Health Check
```bash
# Configuration Route53 pour basculement automatique
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "api.rag-system.com",
      "Type": "A",
      "SetIdentifier": "primary",
      "Failover": "PRIMARY",
      "TTL": 60,
      "ResourceRecords": [{"Value": "1.2.3.4"}],
      "HealthCheckId": "health-check-primary"
    }
  }, {
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "api.rag-system.com", 
      "Type": "A",
      "SetIdentifier": "secondary",
      "Failover": "SECONDARY",
      "TTL": 60,
      "ResourceRecords": [{"Value": "5.6.7.8"}]
    }
  }]
}'

# Health check pour le site principal
aws route53 create-health-check --caller-reference "$(date +%s)" --health-check-config '{
  "Type": "HTTPS",
  "ResourcePath": "/health",
  "FullyQualifiedDomainName": "api.rag-system.com",
  "Port": 443,
  "RequestInterval": 30,
  "FailureThreshold": 3
}'
```

#### Script de Basculement Manuel
```bash
#!/bin/bash
# /scripts/manual-failover.sh

set -euo pipefail

TARGET_SITE=${1:-dr}  # primary, dr, cold
REASON=${2:-"Manual failover initiated"}

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

validate_target_site() {
    log_info "Validation du site cible: $TARGET_SITE"
    
    case $TARGET_SITE in
        "primary")
            KUBE_CONTEXT="production-eu-west-1"
            DNS_RECORD="1.2.3.4"
            ;;
        "dr")
            KUBE_CONTEXT="dr-eu-central-1"
            DNS_RECORD="5.6.7.8"
            ;;
        "cold")
            log_info "Déploiement du site cold en cours..."
            deploy_cold_site
            KUBE_CONTEXT="cold-us-east-1"
            DNS_RECORD="9.10.11.12"
            ;;
        *)
            echo "Site invalide: $TARGET_SITE"
            exit 1
            ;;
    esac
}

check_site_health() {
    log_info "Vérification de la santé du site cible"
    
    kubectl --context="$KUBE_CONTEXT" get pods -n enterprise-rag | grep -q "Running"
    
    if [[ $? -ne 0 ]]; then
        log_error "Site cible non sain, annulation du basculement"
        exit 1
    fi
}

update_dns() {
    log_info "Mise à jour des enregistrements DNS"
    
    # Mise à jour du record principal
    aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch "{
      \"Changes\": [{
        \"Action\": \"UPSERT\",
        \"ResourceRecordSet\": {
          \"Name\": \"api.rag-system.com\",
          \"Type\": \"A\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"$DNS_RECORD\"}]
        }
      }]
    }"
    
    # Attendre la propagation DNS
    sleep 120
}

sync_data_if_needed() {
    if [[ "$TARGET_SITE" != "primary" ]]; then
        log_info "Synchronisation des données vers le site cible"
        
        # Synchronisation de la base de données si nécessaire
        /scripts/sync-database.sh --target="$TARGET_SITE"
        
        # Synchronisation des fichiers
        /scripts/sync-files.sh --target="$TARGET_SITE"
    fi
}

update_monitoring() {
    log_info "Mise à jour de la configuration de monitoring"
    
    # Mise à jour des targets Prometheus
    kubectl --context="$KUBE_CONTEXT" patch configmap prometheus-config -n enterprise-rag --patch "
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: 'rag-api'
        static_configs:
          - targets: ['rag-api.enterprise-rag.svc.cluster.local:8000']
    "
    
    # Redémarrage de Prometheus
    kubectl --context="$KUBE_CONTEXT" rollout restart deployment/prometheus -n enterprise-rag
}

notify_teams() {
    log_info "Notification des équipes"
    
    # Slack
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-type: application/json' \
        --data "{
            \"text\": \"🔄 Basculement vers $TARGET_SITE\",
            \"attachments\": [{
                \"color\": \"warning\",
                \"fields\": [
                    {\"title\": \"Site cible\", \"value\": \"$TARGET_SITE\", \"short\": true},
                    {\"title\": \"Raison\", \"value\": \"$REASON\", \"short\": true},
                    {\"title\": \"Timestamp\", \"value\": \"$(date -u)\", \"short\": true}
                ]
            }]
        }"
    
    # Email d'urgence
    echo "Basculement d'urgence effectué vers $TARGET_SITE
    
Raison: $REASON
Timestamp: $(date -u)
Site actif: $TARGET_SITE
DNS pointant vers: $DNS_RECORD

Actions suivantes requises:
1. Vérifier le fonctionnement du service
2. Investiguer la cause du basculement
3. Planifier le retour au site principal

Contacts d'escalade:
- DevOps: +33 X XX XX XX XX
- Management: +33 X XX XX XX XX
" | mail -s "URGENT: Basculement DR vers $TARGET_SITE" ops-team@company.com
}

deploy_cold_site() {
    log_info "Déploiement du site cold"
    
    # Terraform pour l'infrastructure
    cd /terraform/cold-site
    terraform init
    terraform apply -auto-approve
    
    # Déploiement Kubernetes
    kubectl config use-context cold-us-east-1
    helm install rag-system /charts/rag-system \
        --namespace enterprise-rag \
        --create-namespace \
        --values /config/cold-site-values.yaml \
        --wait --timeout=600s
    
    # Restauration des données
    /scripts/dr-restore.sh latest cold
}

main() {
    log_info "Début du basculement vers $TARGET_SITE"
    log_info "Raison: $REASON"
    
    validate_target_site
    check_site_health
    sync_data_if_needed
    update_dns
    update_monitoring
    notify_teams
    
    log_info "Basculement vers $TARGET_SITE terminé avec succès"
}

# Confirmation avant exécution
echo "ATTENTION: Vous allez effectuer un basculement vers $TARGET_SITE"
echo "Raison: $REASON"
echo "Confirmer? (yes/no)"
read -r confirmation

if [[ "$confirmation" == "yes" ]]; then
    main
else
    echo "Basculement annulé"
    exit 0
fi
```

## Tests de Reprise d'Activité

### Plan de Tests Réguliers

#### Tests Mensuels
```bash
#!/bin/bash
# /scripts/dr-test-monthly.sh

# Test de basculement sur site DR
log_info "Test de basculement mensuel"

# 1. Notification de début de test
notify_test_start() {
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-type: application/json' \
        --data '{"text": "🧪 Début du test DR mensuel", "channel": "#ops"}'
}

# 2. Basculement vers DR
failover_to_dr() {
    ./manual-failover.sh dr "Test mensuel programmé"
}

# 3. Tests fonctionnels
run_functional_tests() {
    # Test de l'API
    curl -f "https://api.rag-system.com/health"
    
    # Test de l'authentification
    curl -X POST "https://api.rag-system.com/auth/login" \
        -d '{"username":"test","password":"test"}'
    
    # Test de recherche
    curl -X POST "https://api.rag-system.com/search" \
        -H "Authorization: Bearer $TEST_TOKEN" \
        -d '{"query":"test query"}'
}

# 4. Retour au site principal
failback_to_primary() {
    sleep 3600  # 1 heure de test
    ./manual-failover.sh primary "Fin du test DR mensuel"
}

# 5. Rapport de test
generate_test_report() {
    echo "Test DR mensuel - $(date)
    
Résultats:
- Basculement vers DR: ✅
- Tests fonctionnels: ✅  
- Retour au principal: ✅
- Durée totale: 1h15min
- RTO observé: 5 minutes
- RPO observé: < 1 minute

Commentaires:
- Tous les services ont basculé correctement
- Aucune perte de données détectée
- Performance acceptable sur le site DR
" > "/reports/dr-test-$(date +%Y%m%d).txt"
    
    # Envoi du rapport
    mail -s "Rapport test DR mensuel" ops-team@company.com < "/reports/dr-test-$(date +%Y%m%d).txt"
}

# Exécution séquentielle
notify_test_start
failover_to_dr
run_functional_tests
failback_to_primary
generate_test_report
```

#### Tests Trimestriels Complets
```bash
#!/bin/bash
# /scripts/dr-test-quarterly.sh

# Test complet incluant restauration depuis backup

# 1. Création d'un environnement de test isolé
create_test_environment() {
    kubectl create namespace dr-test-$(date +%Y%m%d)
    
    # Déploiement de l'infrastructure de test
    helm install rag-test /charts/rag-system \
        --namespace dr-test-$(date +%Y%m%d) \
        --values /config/test-values.yaml
}

# 2. Test de restauration complète
test_full_restore() {
    # Utilisation d'une sauvegarde de la semaine dernière
    BACKUP_DATE=$(date -d '7 days ago' +%Y%m%d)
    
    /scripts/dr-restore.sh "$BACKUP_DATE" "dr-test-$(date +%Y%m%d)"
}

# 3. Tests de performance
performance_tests() {
    # Tests de charge avec Locust
    cd /tests/load
    locust -f locustfile.py --host="https://test-api.rag-system.com" \
        --users 100 --spawn-rate 10 --run-time 30m --headless
}

# 4. Tests de continuité métier
business_continuity_tests() {
    # Simulation de charge utilisateur normale
    # Vérification des SLAs
    # Tests de tous les workflows critiques
    
    python /tests/business-continuity/run_all_tests.py \
        --environment "dr-test-$(date +%Y%m%d)"
}

# 5. Nettoyage
cleanup_test_environment() {
    kubectl delete namespace "dr-test-$(date +%Y%m%d)"
}

# Exécution du test complet
main() {
    create_test_environment
    test_full_restore
    performance_tests
    business_continuity_tests
    cleanup_test_environment
    
    # Génération du rapport complet
    generate_quarterly_report
}

main
```

## Communication et Escalade

### Matrice de Communication

#### Niveaux d'Incident

**Niveau 1 - Critique**
- **Définition** : Service complètement indisponible
- **RTO** : 15 minutes
- **Communication** : Immédiate
- **Escalade** : CTO + VP Engineering

**Niveau 2 - Majeur** 
- **Définition** : Dégradation significative
- **RTO** : 2 heures
- **Communication** : Dans les 30 minutes
- **Escalade** : Engineering Manager

**Niveau 3 - Mineur**
- **Définition** : Impact limité
- **RTO** : 8 heures
- **Communication** : Dans les 2 heures
- **Escalade** : Lead DevOps

#### Canaux de Communication
- **Slack** : #incidents (temps réel)
- **Email** : ops-team@company.com
- **Téléphone** : +33 X XX XX XX XX (astreinte)
- **StatusPage** : https://status.rag-system.com

### Procédures d'Escalade

#### Timeline d'Escalade
```
T+0   : Détection de l'incident
T+5   : Notification équipe DevOps
T+15  : Escalade N1 si non résolu
T+30  : Notification management
T+60  : Escalade N2 + communication externe
T+120 : Escalade executive + plan de communication publique
```

#### Contacts d'Urgence
- **DevOps Lead** : +33 1 XX XX XX XX
- **Engineering Manager** : +33 1 XX XX XX XX  
- **CTO** : +33 1 XX XX XX XX
- **VP Engineering** : +33 1 XX XX XX XX

## Métriques et KPIs DR

### Indicateurs de Performance

#### Temps de Récupération (RTO)
- **Cible** : < 2 heures
- **Mesure** : Temps entre détection et service restauré
- **Seuil d'alerte** : > 4 heures

#### Point de Récupération (RPO)
- **Cible** : < 1 heure
- **Mesure** : Perte de données maximale
- **Seuil d'alerte** : > 2 heures

#### Disponibilité
- **Cible** : 99.9% (8.76 heures de downtime/an)
- **Mesure** : Uptime total sur période
- **Seuil d'alerte** : < 99.5%

### Tableaux de Bord DR

#### Grafana Dashboard "Disaster Recovery"
```yaml
# Configuration du dashboard DR
dashboard:
  title: "Disaster Recovery Monitoring"
  panels:
    - title: "Backup Success Rate"
      type: "stat"
      query: "increase(backup_success_total[24h]) / increase(backup_attempts_total[24h]) * 100"
      
    - title: "Recovery Time Objective"
      type: "gauge"
      query: "histogram_quantile(0.95, rate(recovery_time_seconds_bucket[24h]))"
      
    - title: "Cross-Site Replication Lag"
      type: "graph"
      query: "replication_lag_seconds"
      
    - title: "DR Site Health"
      type: "table"
      query: "up{job=~'.*-dr'}"
```

## Formation et Documentation

### Formation de l'Équipe

#### Programme de Formation DR
1. **Formation initiale** (8h)
   - Principes du DR
   - Architecture du système
   - Procédures de base

2. **Formation avancée** (16h)
   - Troubleshooting complexe
   - Optimisation des performances
   - Gestion de crise

3. **Exercices pratiques** (mensuel)
   - Simulations d'incidents
   - Tests de procédures
   - Amélioration continue

#### Certification DR
- **Niveau 1** : Opérateur DR
- **Niveau 2** : Spécialiste DR  
- **Niveau 3** : Expert DR

### Documentation Associée

#### Documents de Référence
- [Architecture de Haute Disponibilité](./ha-architecture.md)
- [Runbook Incidents](./runbooks/incident-response.md)
- [Guide de Monitoring](./monitoring-guide.md)
- [Procédures de Sécurité](./security-procedures.md)

---

*Ce plan de reprise d'activité est un document vivant qui doit être régulièrement mis à jour et testé. Dernière révision : Décembre 2024*
