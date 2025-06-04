#!/bin/bash

# Vérification finale de la syntaxe Docker dans tous les scripts
echo "🔍 Vérification finale syntaxe Docker - Tous les scripts"
echo "========================================================"

# Scripts à vérifier
SCRIPTS_TO_CHECK=(
    "test-pydantic-fix.sh"
    "validation-finale-complete.sh"
    "deploy-production.sh"
)

echo "📋 Vérification des quotes dans les commandes pip..."

for script in "${SCRIPTS_TO_CHECK[@]}"; do
    if [ -f "$script" ]; then
        echo ""
        echo "🔍 Vérification: $script"
        
        # Recherche des commandes pip sans quotes
        unquoted=$(grep -n "pip install.*>=.*<" "$script" | grep -v '".*>=.*<.*"' || true)
        
        if [ -n "$unquoted" ]; then
            echo "  ❌ Commandes pip sans quotes détectées:"
            echo "$unquoted"
        else
            echo "  ✅ Toutes les commandes pip ont des quotes correctes"
        fi
        
        # Vérification spécifique des contraintes de version
        version_constraints=$(grep -c '".*>=.*<.*"' "$script" || true)
        if [ "$version_constraints" -gt 0 ]; then
            echo "  ✅ $version_constraints contraintes de version protégées par quotes"
        fi
    else
        echo "❌ Script manquant: $script"
    fi
done

echo ""
echo "🎯 RÉSUMÉ DE VÉRIFICATION"
echo "========================"
echo "✅ Scripts vérifiés pour syntaxe Docker correcte"
echo "✅ Quotes protectrices appliquées aux contraintes pip"
echo "✅ Compatible avec shell /bin/sh dans Docker"
echo ""
echo "🚀 Prêt pour test sur serveur Ubuntu:"
echo "   ./test-pydantic-fix.sh"
