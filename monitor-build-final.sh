#!/bin/bash
# Script de surveillance du build Docker FINAL
# Suit le processus et détecte la résolution des problèmes

echo "🚀 MONITORING BUILD DOCKER FINAL - Solution resolution-too-deep"
echo "=================================================="
echo ""

# Fonction de contrôle du build
monitor_build() {
    local start_time=$(date +%s)
    local timeout=1800  # 30 minutes timeout
    
    echo "⏱️  Démarrage du monitoring à $(date)"
    echo "🔍 Recherche des signes de progression..."
    echo ""
    
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        
        # Vérification du timeout
        if [ $elapsed -gt $timeout ]; then
            echo "⚠️  TIMEOUT atteint (30min) - Arrêt du monitoring"
            break
        fi
        
        # Vérification des processus Docker actifs
        if docker ps -q --filter "label=docker.io/library/python" > /dev/null 2>&1; then
            echo "✅ Docker build en cours... (${elapsed}s écoulées)"
        fi
        
        # Vérification de l'existence de l'image finale
        if docker images | grep -q "mar-app-final.*test"; then
            echo ""
            echo "🎉 SUCCESS! Image mar-app-final:test créée avec succès!"
            echo "⏱️  Temps total: ${elapsed} secondes"
            echo ""
            echo "📋 Détails de l'image:"
            docker images | grep "mar-app-final.*test"
            echo ""
            echo "🧪 Test rapide de l'image:"
            docker run --rm mar-app-final:test python -c "import langchain, crewai; print('✅ Packages AI importés avec succès dans le container')"
            return 0
        fi
        
        # Vérification des erreurs courantes dans les logs Docker
        if docker system df | grep -q "BUILD FAILED"; then
            echo "❌ Échec détecté dans le build Docker"
            return 1
        fi
        
        sleep 10
    done
}

# Fonction de rapport final
generate_report() {
    echo ""
    echo "📊 RAPPORT FINAL - Build Docker"
    echo "================================="
    echo ""
    
    echo "🐳 Images Docker disponibles:"
    docker images | head -10
    echo ""
    
    echo "💾 Utilisation Docker:"
    docker system df
    echo ""
    
    if docker images | grep -q "mar-app-final.*test"; then
        echo "✅ RÉSOLUTION CONFIRMÉE: Le problème 'resolution-too-deep' a été résolu!"
        echo "   • Build Docker completé avec succès"
        echo "   • Image créée: mar-app-final:test"
        echo "   • Stratégie de résolution par couches effective"
        echo ""
        echo "🔧 Prochaines étapes recommandées:"
        echo "   1. Test de fonctionnement du container"
        echo "   2. Validation des imports de packages"
        echo "   3. Test de performance et optimisation finale"
    else
        echo "⚠️  Build Docker non terminé ou en échec"
        echo "   • Vérifier les logs Docker pour diagnostiquer"
        echo "   • Possible besoin d'optimisation supplémentaire"
    fi
}

# Exécution du monitoring
monitor_build
generate_report

echo ""
echo "🏁 Monitoring terminé - $(date)"
