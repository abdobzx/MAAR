#!/bin/bash

# 🚨 TEST COMPARAISON BUILD TEMPS - NORMAL vs FAST
# Utilisation : ./test-build-comparison.sh

set -e

echo "⏱️  COMPARAISON BUILD DOCKER - NORMAL vs FAST"
echo "================================================"

# Fonction pour mesurer le temps
measure_build() {
    local dockerfile=$1
    local compose_file=$2
    local service_name=$3
    
    echo "📍 Test build avec $dockerfile..."
    
    # Nettoyage préalable
    docker-compose -f "$compose_file" down --remove-orphans 2>/dev/null || true
    docker rmi "$service_name" 2>/dev/null || true
    docker builder prune -f >/dev/null 2>&1
    
    # Mesure du temps de build
    start_time=$(date +%s)
    
    if docker-compose -f "$compose_file" build --no-cache; then
        end_time=$(date +%s)
        build_time=$((end_time - start_time))
        echo "✅ Build réussi en ${build_time}s"
        return $build_time
    else
        echo "❌ Build échoué"
        return 9999
    fi
}

echo "📊 1. BUILD FAST (requirements.fast.txt - 38 dépendances)"
echo "--------------------------------------------------------"
time_fast=$(measure_build "Dockerfile.fast" "docker-compose.fast.yml" "rag_api_fast")

echo ""
echo "📊 2. BUILD NORMAL (requirements.staging.txt - 152 dépendances)"  
echo "---------------------------------------------------------------"
time_normal=$(measure_build "Dockerfile.staging" "docker-compose.staging.yml" "rag_api")

echo ""
echo "📊 RÉSULTATS COMPARAISON"
echo "========================"
echo "⚡ Build FAST    : ${time_fast}s (38 dépendances)"
echo "🐌 Build NORMAL : ${time_normal}s (152 dépendances)"

if [ "$time_fast" -lt "$time_normal" ]; then
    improvement=$((time_normal - time_fast))
    percentage=$(echo "scale=1; ($improvement * 100) / $time_normal" | bc -l)
    echo "🚀 AMÉLIORATION : ${improvement}s plus rapide (${percentage}% gain)"
else
    echo "⚠️  Pas d'amélioration détectée"
fi

echo ""
echo "📋 RECOMMANDATIONS :"
if [ "$time_fast" -lt 300 ]; then
    echo "✅ Build FAST acceptable (< 5 min)"
else
    echo "❌ Build FAST encore trop lent"
fi

if [ "$time_normal" -gt 600 ]; then
    echo "🚨 Build NORMAL critique (> 10 min)"
else
    echo "✅ Build NORMAL acceptable"
fi

# Nettoyage final
echo ""
echo "🧹 Nettoyage final..."
docker-compose -f docker-compose.fast.yml down 2>/dev/null || true
docker-compose -f docker-compose.staging.yml down 2>/dev/null || true
