#!/bin/bash
# Script de vérification du statut de la plateforme MAR
# Usage: ./scripts/check_status.sh

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${MAR_API_URL:-http://localhost:8000}"
UI_URL="${MAR_UI_URL:-http://localhost:8501}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"

echo -e "${BLUE}🤖 Vérification du statut de la plateforme MAR${NC}"
echo "=================================================="

# Fonction utilitaire pour vérifier un service
check_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    echo -n "Vérification $name... "
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ ERREUR${NC}"
        return 1
    fi
}

# Fonction pour vérifier Docker
check_docker() {
    echo -n "Docker... "
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker non disponible${NC}"
        return 1
    fi
}

# Fonction pour vérifier les containers
check_containers() {
    echo -e "\n${BLUE}📦 Statut des containers:${NC}"
    
    local containers=(
        "mar-api"
        "mar-ollama" 
        "mar-ui"
        "mar-redis"
        "mar-prometheus"
        "mar-grafana"
    )
    
    for container in "${containers[@]}"; do
        echo -n "  $container... "
        if docker ps | grep -q "$container"; then
            status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "running")
            if [[ "$status" == "healthy" ]] || [[ "$status" == "running" ]]; then
                echo -e "${GREEN}✅ OK${NC}"
            else
                echo -e "${YELLOW}⚠️ $status${NC}"
            fi
        else
            echo -e "${RED}❌ Arrêté${NC}"
        fi
    done
}

# Vérifications principales
echo -e "\n${BLUE}🌐 Services web:${NC}"
check_service "API MAR" "$API_URL/health"
check_service "Interface UI" "$UI_URL/_stcore/health"  
check_service "Grafana" "$GRAFANA_URL/api/health"
check_service "Prometheus" "$PROMETHEUS_URL/-/healthy"

# Vérifications Docker
echo -e "\n${BLUE}🐳 Infrastructure:${NC}"
check_docker
check_containers

# Vérifications des endpoints API
echo -e "\n${BLUE}🔌 Endpoints API:${NC}"
check_service "API Ready" "$API_URL/ready"
check_service "API Docs" "$API_URL/docs" 200
check_service "API Metrics" "$API_URL/metrics"

# Vérifications spécialisées
echo -e "\n${BLUE}🧠 Services IA:${NC}"
check_service "Ollama" "http://localhost:11434/api/tags"

echo -e "\n${BLUE}💾 Stockage:${NC}"
check_service "Redis" "http://localhost:6379" 000  # Redis ne retourne pas de code HTTP
echo -n "Redis ping... "
if docker exec mar-redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ ERREUR${NC}"
fi

# Vérifications des données
echo -e "\n${BLUE}📊 Données et métriques:${NC}"

# Vector store stats
echo -n "Vector Store... "
if response=$(curl -s "$API_URL/api/v1/vector-store/stats" 2>/dev/null); then
    chunks=$(echo "$response" | grep -o '"total_chunks":[0-9]*' | cut -d':' -f2 || echo "0")
    docs=$(echo "$response" | grep -o '"total_documents":[0-9]*' | cut -d':' -f2 || echo "0")
    echo -e "${GREEN}✅ OK${NC} ($docs docs, $chunks chunks)"
else
    echo -e "${YELLOW}⚠️ Non accessible${NC}"
fi

# Métriques Prometheus
echo -n "Métriques... "
if curl -s "$PROMETHEUS_URL/api/v1/query?query=up" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️ Prometheus non accessible${NC}"
fi

# Résumé de santé
echo -e "\n${BLUE}📋 Résumé de santé:${NC}"

# Vérifier les logs d'erreur récents
echo -n "Logs d'erreur (dernière heure)... "
error_count=$(docker logs mar-api --since="1h" 2>&1 | grep -i error | wc -l)
if [[ "$error_count" -eq 0 ]]; then
    echo -e "${GREEN}✅ Aucune erreur${NC}"
elif [[ "$error_count" -lt 5 ]]; then
    echo -e "${YELLOW}⚠️ $error_count erreurs${NC}"
else
    echo -e "${RED}❌ $error_count erreurs${NC}"
fi

# Vérifier l'utilisation des ressources
echo -n "Utilisation CPU... "
cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" mar-api | sed 's/%//')
if (( $(echo "$cpu_usage < 80" | bc -l) )); then
    echo -e "${GREEN}✅ ${cpu_usage}%${NC}"
else
    echo -e "${YELLOW}⚠️ ${cpu_usage}%${NC}"
fi

echo -n "Utilisation mémoire... "
mem_usage=$(docker stats --no-stream --format "{{.MemPerc}}" mar-api | sed 's/%//')
if (( $(echo "$mem_usage < 80" | bc -l) )); then
    echo -e "${GREEN}✅ ${mem_usage}%${NC}"
else
    echo -e "${YELLOW}⚠️ ${mem_usage}%${NC}"
fi

# Test fonctionnel simple
echo -e "\n${BLUE}🧪 Test fonctionnel:${NC}"
echo -n "Test de recherche simple... "

test_query='{"query": "test", "max_results": 1}'
if curl -s -X POST "$API_URL/api/v1/search" \
   -H "Content-Type: application/json" \
   -d "$test_query" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️ Échec du test${NC}"
fi

# Affichage des liens utiles
echo -e "\n${BLUE}🔗 Liens utiles:${NC}"
echo -e "  📱 Interface MAR: ${YELLOW}$UI_URL${NC}"
echo -e "  🔌 API MAR: ${YELLOW}$API_URL${NC}"
echo -e "  📚 Documentation: ${YELLOW}$API_URL/docs${NC}"
echo -e "  📊 Grafana: ${YELLOW}$GRAFANA_URL${NC}"
echo -e "  🎯 Prometheus: ${YELLOW}$PROMETHEUS_URL${NC}"

# Actions recommandées
echo -e "\n${BLUE}💡 Actions recommandées:${NC}"

if [[ "$error_count" -gt 5 ]]; then
    echo -e "  ${YELLOW}⚠️ Vérifier les logs: make logs${NC}"
fi

if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    echo -e "  ${YELLOW}⚠️ CPU élevé: surveiller la charge${NC}"
fi

if (( $(echo "$mem_usage > 80" | bc -l) )); then
    echo -e "  ${YELLOW}⚠️ Mémoire élevée: redémarrer si nécessaire${NC}"
fi

echo -e "\n${GREEN}✅ Vérification terminée!${NC}"
echo "=================================================="
