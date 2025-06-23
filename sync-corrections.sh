#!/bin/bash

# Script de synchronisation des corrections vers serveur Ubuntu
echo "🔄 Synchronisation des corrections vers serveur Ubuntu"
echo "====================================================="

# Fichiers critiques à synchroniser
FILES_TO_SYNC=(
    "test-pydantic-fix.sh"
    "validation-finale-complete.sh"
    "deploy-production.sh"
    "requirements.txt"
    "requirements.staging.txt"
    "RAPPORT-VALIDATION-FINALE.md"
    "INSTRUCTIONS-SERVEUR-UBUNTU-FINAL.md"
)

echo "📋 Fichiers à synchroniser:"
for file in "${FILES_TO_SYNC[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (manquant)"
    fi
done

echo ""
echo "🚀 Prêt pour synchronisation avec serveur Ubuntu"
echo ""
echo "📝 Commandes pour copier vers serveur:"
echo "   scp test-pydantic-fix.sh user@server:~/AI_Deplyment_First_step/MAAR/"
echo "   scp validation-finale-complete.sh user@server:~/AI_Deplyment_First_step/MAAR/"
echo "   scp requirements.txt user@server:~/AI_Deplyment_First_step/MAAR/"
echo "   scp requirements.staging.txt user@server:~/AI_Deplyment_First_step/MAAR/"
echo ""
echo "🔧 Ou utilisez rsync pour sync complète:"
echo "   rsync -av --include='*.sh' --include='requirements*.txt' --include='*.md' . user@server:~/AI_Deplyment_First_step/MAAR/"
echo ""
echo "⚡ Commande immédiate à exécuter sur serveur:"
echo "   ./test-pydantic-fix.sh"
