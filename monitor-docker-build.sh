#!/bin/bash

echo "🔍 Monitoring Docker build - Detection du problème 'resolution-too-deep'..."
echo "Démarré à $(date)"
echo "============================================"

BUILD_LOG="docker-build-final.log"
RESOLUTION_DEEP_DETECTED=0
BUILD_SUCCESS=0

# Fonction pour analyser les logs
analyze_logs() {
    if [ -f "$BUILD_LOG" ]; then
        # Chercher le problème resolution-too-deep
        if grep -q "resolution-too-deep\|ResolutionTooDeep\|maximum recursion depth" "$BUILD_LOG"; then
            echo "❌ PROBLÈME DÉTECTÉ: resolution-too-deep trouvé dans les logs!"
            RESOLUTION_DEEP_DETECTED=1
            echo "Dernières lignes avec le problème:"
            grep -n -A 5 -B 5 "resolution-too-deep\|ResolutionTooDeep\|maximum recursion depth" "$BUILD_LOG" | tail -20
        fi
        
        # Chercher les signes de succès
        if grep -q "Successfully built\|Successfully tagged" "$BUILD_LOG"; then
            echo "✅ BUILD RÉUSSI: Image construite avec succès!"
            BUILD_SUCCESS=1
        fi
        
        # Afficher les erreurs pip
        if grep -q "ERROR:\|FAILED:\|Could not find" "$BUILD_LOG"; then
            echo "⚠️  Erreurs pip détectées:"
            grep -n "ERROR:\|FAILED:\|Could not find" "$BUILD_LOG" | tail -10
        fi
        
        # Afficher le statut général
        echo ""
        echo "📊 STATUT ACTUEL:"
        echo "- Taille du log: $(wc -l < "$BUILD_LOG") lignes"
        echo "- Resolution-too-deep détecté: $([ $RESOLUTION_DEEP_DETECTED -eq 1 ] && echo "OUI" || echo "NON")"
        echo "- Build terminé avec succès: $([ $BUILD_SUCCESS -eq 1 ] && echo "OUI" || echo "NON")"
        
        # Dernières lignes du build
        echo ""
        echo "📝 Dernières lignes du build:"
        tail -10 "$BUILD_LOG"
    else
        echo "⏳ Fichier de log non encore créé..."
    fi
}

# Monitoring en continu
while true; do
    clear
    echo "🔍 Monitoring Docker build - $(date)"
    echo "============================================"
    
    analyze_logs
    
    # Arrêter si build terminé (succès ou échec)
    if [ $BUILD_SUCCESS -eq 1 ] || [ $RESOLUTION_DEEP_DETECTED -eq 1 ]; then
        echo ""
        echo "🏁 MONITORING TERMINÉ"
        if [ $BUILD_SUCCESS -eq 1 ]; then
            echo "✅ Le build s'est terminé avec SUCCÈS!"
            echo "✅ Le problème 'resolution-too-deep' semble RÉSOLU!"
        elif [ $RESOLUTION_DEEP_DETECTED -eq 1 ]; then
            echo "❌ Le problème 'resolution-too-deep' est toujours présent."
            echo "❌ Il faut continuer l'itération sur le Dockerfile.final"
        fi
        break
    fi
    
    # Vérifier si le processus Docker build est encore actif
    if ! pgrep -f "docker build" > /dev/null; then
        echo ""
        echo "⚠️  Le processus Docker build ne semble plus actif."
        echo "Vérification finale des logs..."
        analyze_logs
        break
    fi
    
    sleep 15
done

echo ""
echo "📋 RAPPORT FINAL:"
echo "- Resolution-too-deep détecté: $([ $RESOLUTION_DEEP_DETECTED -eq 1 ] && echo "OUI" || echo "NON")"
echo "- Build réussi: $([ $BUILD_SUCCESS -eq 1 ] && echo "OUI" || echo "NON")"
echo "- Log complet disponible dans: $BUILD_LOG"
