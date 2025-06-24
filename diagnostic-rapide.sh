#!/bin/bash
# Script de diagnostic rapide pour identifier les problèmes

echo "=== DIAGNOSTIC RAPIDE MAR PLATFORM ==="
echo "Date: $(date)"
echo ""

# 1. État des conteneurs
echo "1. ÉTAT DES CONTENEURS:"
echo "========================"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 2. Connectivité réseau
echo "2. CONNECTIVITÉ RÉSEAU:"
echo "======================="
echo "Test connectivité mar-api -> ollama:"
docker exec mar-api ping -c 2 ollama 2>/dev/null && echo "✅ Ping OK" || echo "❌ Ping échoué"

echo "Test connectivité HTTP vers Ollama:"
docker exec mar-api curl -s -o /dev/null -w "%{http_code}" http://ollama:11434/api/tags 2>/dev/null | grep -q "200" && echo "✅ HTTP OK" || echo "❌ HTTP échoué"
echo ""

# 3. Variables d'environnement importantes
echo "3. VARIABLES D'ENVIRONNEMENT:"
echo "============================="
echo "Dans mar-api:"
docker exec mar-api env | grep -E "(OLLAMA|PYTHON)" | sort
echo ""

# 4. Modules Python problématiques
echo "4. MODULES PYTHON:"
echo "=================="
echo "Vérification llm.pooling:"
docker exec mar-api python3 -c "import llm.pooling; print('✅ llm.pooling OK')" 2>/dev/null || echo "❌ llm.pooling manquant"

echo "Vérification orchestrator.tasks:"
docker exec mar-api python3 -c "import orchestrator.tasks; print('✅ orchestrator.tasks OK')" 2>/dev/null || echo "❌ orchestrator.tasks manquant"
echo ""

# 5. Logs récents avec erreurs
echo "5. ERREURS RÉCENTES:"
echo "==================="
echo "Dernières erreurs dans mar-api:"
docker logs mar-api --tail 50 2>/dev/null | grep -i error | tail -5
echo ""

echo "Dernières erreurs dans mar-ollama:"
docker logs mar-ollama --tail 20 2>/dev/null | grep -i error | tail -3
echo ""

# 6. Test de santé API
echo "6. TEST DE SANTÉ API:"
echo "===================="
curl -s http://localhost:8008/health > /dev/null && echo "✅ API répond" || echo "❌ API ne répond pas"

# Test des endpoints principaux
curl -s http://localhost:8008/docs > /dev/null && echo "✅ Documentation API accessible" || echo "❌ Documentation API inaccessible"
echo ""

# 7. Espace disque et ressources
echo "7. RESSOURCES SYSTÈME:"
echo "====================="
echo "Utilisation disque:"
df -h / | tail -1

echo "Mémoire Docker:"
docker system df | grep -E "(Images|Containers|Local Volumes)"
echo ""

# 8. Fichiers de configuration
echo "8. FICHIERS DE CONFIGURATION:"
echo "============================="
echo "Fichier .env:"
[ -f .env ] && echo "✅ .env existe" || echo "❌ .env manquant"

echo "Fichier docker-compose.yml:"
[ -f docker-compose.yml ] && echo "✅ docker-compose.yml existe" || echo "❌ docker-compose.yml manquant"

echo "Fichier requirements.txt:"
[ -f requirements.txt ] && echo "✅ requirements.txt existe" || echo "❌ requirements.txt manquant"
echo ""

# 9. Recommandations
echo "9. RECOMMANDATIONS:"
echo "=================="

# Vérifier si Ollama fonctionne
if ! docker exec mar-api curl -s http://ollama:11434/api/tags > /dev/null 2>&1; then
    echo "🔧 Exécuter: ./fix-ollama-connection-definitive.sh"
fi

# Vérifier si les modules manquent
if ! docker exec mar-api python3 -c "import llm.pooling" 2>/dev/null; then
    echo "🔧 Exécuter: ./fix-missing-module.sh"
fi

# Vérifier si l'API ne répond pas
if ! curl -s http://localhost:8008/health > /dev/null; then
    echo "🔧 Vérifier: docker logs mar-api"
    echo "🔧 Redémarrer: docker-compose restart mar-api"
fi

echo ""
echo "=== FIN DU DIAGNOSTIC ==="
