#!/bin/bash
# Script de solution globale - corrige tous les problèmes identifiés

echo "=== SOLUTION GLOBALE MAR PLATFORM ==="
echo "Correction de tous les problèmes identifiés"
echo "Date: $(date)"
echo ""

# Rendre tous les scripts exécutables
chmod +x *.sh

# 1. Diagnostic initial
echo "1. DIAGNOSTIC INITIAL:"
echo "====================="
./diagnostic-rapide.sh
echo ""

# 2. Correction des warnings dotenv
echo "2. CORRECTION DES WARNINGS DOTENV:"
echo "=================================="
./fix-dotenv-warnings.sh
echo ""

# 3. Correction de la connexion Ollama
echo "3. CORRECTION DE LA CONNEXION OLLAMA:"
echo "====================================="
./fix-ollama-connection-definitive.sh
echo ""

# 4. Correction des modules manquants
echo "4. CORRECTION DES MODULES MANQUANTS:"
echo "===================================="
./fix-missing-module.sh
echo ""

# 5. Attente et vérification finale
echo "5. VÉRIFICATION FINALE:"
echo "======================="
echo "Attente de stabilisation (30 secondes)..."
sleep 30

echo "État final des services:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "Test final de l'API:"
if curl -s http://localhost:8008/health > /dev/null; then
    echo "✅ API MAR opérationnelle !"
    echo ""
    echo "🔗 URLs disponibles:"
    echo "   - API Health: http://localhost:8008/health"
    echo "   - API Docs: http://localhost:8008/docs"
    echo "   - Grafana: http://localhost:3000"
    echo "   - Prometheus: http://localhost:9090"
else
    echo "❌ API toujours non opérationnelle"
    echo ""
    echo "🔧 Diagnostic supplémentaire requis:"
    docker logs mar-api --tail 20
fi

echo ""
echo "6. COMMANDES UTILES:"
echo "==================="
echo "  - Voir les logs API: docker logs mar-api"
echo "  - Voir les logs Ollama: docker logs mar-ollama"
echo "  - Redémarrer l'API: docker-compose restart mar-api"
echo "  - Redémarrer tout: docker-compose restart"
echo "  - Diagnostic: ./diagnostic-rapide.sh"
echo ""

echo "=== SOLUTION GLOBALE TERMINÉE ==="

# Diagnostic final
echo ""
echo "DIAGNOSTIC FINAL:"
echo "================"
./diagnostic-rapide.sh
