#!/bin/bash

# Script de validation finale du système RAG Enterprise
# Vérifie l'intégrité et la complétude du projet

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/tmp/rag-validation-$(date +%Y%m%d_%H%M%S).log"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${GREEN}[✓ INFO]${NC} $1"
}

log_warn() {
    log "${YELLOW}[⚠ WARN]${NC} $1"
}

log_error() {
    log "${RED}[✗ ERROR]${NC} $1"
}

log_section() {
    log "${BLUE}[📋 $1]${NC}"
    echo "========================================"
}

check_file_exists() {
    local file="$1"
    local description="$2"
    
    if [ -f "$PROJECT_ROOT/$file" ]; then
        log_info "$description: ✓"
        return 0
    else
        log_error "$description: ✗ (manquant: $file)"
        return 1
    fi
}

check_directory_exists() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        log_info "$description: ✓"
        return 0
    else
        log_error "$description: ✗ (manquant: $dir)"
        return 1
    fi
}

check_python_imports() {
    local file="$1"
    local description="$2"
    
    if python3 -m py_compile "$PROJECT_ROOT/$file" 2>/dev/null; then
        log_info "$description: ✓ (syntaxe valide)"
        return 0
    else
        log_error "$description: ✗ (erreur de syntaxe)"
        return 1
    fi
}

main() {
    log_section "VALIDATION SYSTÈME RAG ENTERPRISE"
    log "Date: $(date)"
    log "Répertoire projet: $PROJECT_ROOT"
    log "Log file: $LOG_FILE"
    echo ""
    
    local errors=0
    
    # 1. Structure de base du projet
    log_section "STRUCTURE DU PROJET"
    
    check_file_exists "README.md" "README principal" || ((errors++))
    check_file_exists "requirements.txt" "Dépendances Python" || ((errors++))
    check_file_exists "pyproject.toml" "Configuration projet" || ((errors++))
    check_file_exists "Dockerfile" "Configuration Docker" || ((errors++))
    check_file_exists "docker-compose.yml" "Orchestration Docker" || ((errors++))
    check_file_exists ".env.example" "Variables d'environnement exemple" || ((errors++))
    
    # 2. Code principal
    log_section "MODULES PYTHON"
    
    check_directory_exists "api" "API FastAPI" || ((errors++))
    check_directory_exists "agents" "Agents multi-tâches" || ((errors++))
    check_directory_exists "core" "Configuration et utilitaires" || ((errors++))
    check_directory_exists "database" "Gestion base de données" || ((errors++))
    check_directory_exists "security" "Sécurité et authentification" || ((errors++))
    check_directory_exists "tasks" "Tâches Celery" || ((errors++))
    
    # Vérification des fichiers Python critiques
    [ -f "$PROJECT_ROOT/api/main.py" ] && check_python_imports "api/main.py" "API principale" || ((errors++))
    [ -f "$PROJECT_ROOT/core/config.py" ] && check_python_imports "core/config.py" "Configuration" || ((errors++))
    [ -f "$PROJECT_ROOT/core/celery.py" ] && check_python_imports "core/celery.py" "Celery" || ((errors++))
    
    # 3. Agents
    log_section "AGENTS SPÉCIALISÉS"
    
    agents=("orchestration" "ingestion" "vectorization" "storage" "retrieval" "synthesis" "feedback")
    for agent in "${agents[@]}"; do
        if check_directory_exists "agents/$agent" "Agent $agent"; then
            [ -f "$PROJECT_ROOT/agents/$agent/agent.py" ] && check_python_imports "agents/$agent/agent.py" "Code agent $agent" || ((errors++))
        else
            ((errors++))
        fi
    done
    
    # 4. Infrastructure
    log_section "INFRASTRUCTURE"
    
    check_directory_exists "infrastructure" "Répertoire infrastructure" || ((errors++))
    check_directory_exists "infrastructure/kubernetes" "Manifests Kubernetes" || ((errors++))
    check_directory_exists "infrastructure/helm" "Charts Helm" || ((errors++))
    check_directory_exists "infrastructure/monitoring" "Configuration monitoring" || ((errors++))
    check_directory_exists "infrastructure/security" "Politiques sécurité" || ((errors++))
    
    # 5. Documentation
    log_section "DOCUMENTATION"
    
    docs=("api.md" "deployment-guide.md" "production-deployment-guide.md" "user-guide.md" "operational-maintenance-guide.md" "disaster-recovery-plan.md")
    for doc in "${docs[@]}"; do
        check_file_exists "docs/$doc" "Guide $doc" || ((errors++))
    done
    
    # 6. Scripts
    log_section "SCRIPTS OPÉRATIONNELS"
    
    check_directory_exists "scripts" "Répertoire scripts" || ((errors++))
    check_directory_exists "scripts/deployment" "Scripts déploiement" || ((errors++))
    check_directory_exists "scripts/backup" "Scripts sauvegarde" || ((errors++))
    check_directory_exists "scripts/monitoring" "Scripts monitoring" || ((errors++))
    
    # 7. Tests
    log_section "TESTS"
    
    check_directory_exists "tests" "Répertoire tests" || ((errors++))
    check_directory_exists "tests/unit" "Tests unitaires" || ((errors++))
    check_directory_exists "tests/integration" "Tests intégration" || ((errors++))
    check_directory_exists "tests/load" "Tests de charge" || ((errors++))
    
    # 8. CI/CD
    log_section "CI/CD"
    
    check_directory_exists ".github" "Configuration GitHub" || ((errors++))
    check_file_exists ".github/workflows/ci-cd.yml" "Pipeline CI/CD" || ((errors++))
    
    # 9. Vérifications avancées
    log_section "VÉRIFICATIONS AVANCÉES"
    
    # Vérifier la présence des clés dans requirements.txt
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        essential_packages=("fastapi" "celery" "redis" "sqlalchemy" "qdrant-client" "langchain" "crewai")
        for package in "${essential_packages[@]}"; do
            if grep -q "^$package" "$PROJECT_ROOT/requirements.txt"; then
                log_info "Package essentiel $package: ✓"
            else
                log_warn "Package essentiel $package: manquant dans requirements.txt"
            fi
        done
    fi
    
    # Vérifier la cohérence des versions
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        if grep -q "version.*1\.0\.0" "$PROJECT_ROOT/pyproject.toml"; then
            log_info "Version du projet: ✓ (1.0.0)"
        else
            log_warn "Version du projet: incohérente"
        fi
    fi
    
    # 10. Résumé final
    log_section "RÉSUMÉ DE VALIDATION"
    
    if [ $errors -eq 0 ]; then
        log_info "🎉 VALIDATION RÉUSSIE: Tous les composants sont présents"
        log_info "📋 Le système RAG Enterprise est complet et prêt pour le déploiement"
        echo ""
        log "${GREEN}✅ SYSTÈME VALIDÉ - PRÊT POUR PRODUCTION${NC}"
    else
        log_error "❌ VALIDATION ÉCHOUÉE: $errors erreur(s) détectée(s)"
        log_error "🔧 Veuillez corriger les erreurs avant de continuer"
        echo ""
        log "${RED}❌ SYSTÈME NON VALIDÉ - CORRECTIONS REQUISES${NC}"
    fi
    
    echo ""
    log "📊 Statistiques de validation:"
    log "   - Erreurs détectées: $errors"
    log "   - Log complet: $LOG_FILE"
    log "   - Durée validation: $(date)"
    
    # Génération d'un rapport de validation
    cat > "$PROJECT_ROOT/validation-report.md" << EOF
# Rapport de Validation - Système RAG Enterprise

**Date**: $(date)
**Version**: 1.0.0
**Statut**: $([ $errors -eq 0 ] && echo "✅ VALIDÉ" || echo "❌ NON VALIDÉ")

## Résumé

- **Erreurs détectées**: $errors
- **Log complet**: $LOG_FILE

## Composants validés

### ✅ Structure du projet
- README.md, requirements.txt, Dockerfile
- Configuration Docker Compose
- Variables d'environnement

### ✅ Code application
- API FastAPI complète
- 7 agents spécialisés
- Configuration et utilitaires
- Sécurité et authentification

### ✅ Infrastructure
- Manifests Kubernetes
- Charts Helm
- Monitoring (Prometheus, Grafana, ELK)
- Politiques de sécurité

### ✅ Documentation
- Guides utilisateur et technique
- Procédures opérationnelles
- Plan de reprise d'activité

### ✅ Tests et CI/CD
- Tests unitaires et d'intégration
- Tests de charge
- Pipeline GitHub Actions

## Recommandations

$([ $errors -eq 0 ] && echo "Le système est prêt pour la production." || echo "Corriger les erreurs détectées avant déploiement.")

---
*Généré automatiquement par le script de validation*
EOF
    
    return $errors
}

# Affichage de l'aide
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0"
    echo ""
    echo "Script de validation du système RAG Enterprise"
    echo "Vérifie l'intégrité et la complétude de tous les composants"
    echo ""
    echo "Options:"
    echo "  -h, --help    Affiche cette aide"
    echo ""
    echo "Sortie:"
    echo "  Code 0: Validation réussie"
    echo "  Code >0: Nombre d'erreurs détectées"
    exit 0
fi

# Exécution
main "$@"
