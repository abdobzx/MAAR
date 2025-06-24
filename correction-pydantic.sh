#!/bin/bash
# Script pour corriger les problèmes de Pydantic regex -> pattern

echo "=== Correction des problèmes de compatibilité Pydantic v2 ==="

# Vérifier si les fichiers existent
if [ ! -f "api/models/chat.py" ]; then
    echo "❌ Erreur: Le fichier api/models/chat.py n'existe pas."
    exit 1
fi

# Faire une sauvegarde du fichier
echo "1. Sauvegarde du fichier chat.py..."
cp api/models/chat.py api/models/chat.py.backup
echo "✓ Sauvegarde créée: api/models/chat.py.backup"

# Appliquer les corrections
echo "2. Application des corrections Pydantic..."

# Remplacer regex par pattern
sed -i 's/regex="/pattern="/g' api/models/chat.py
sed -i "s/regex='/pattern='/g" api/models/chat.py

echo "✓ Remplacement de 'regex' par 'pattern' terminé."

# Vérifier le résultat
if grep -q 'regex=' api/models/chat.py; then
    echo "⚠️ Attention: Il reste des occurrences de 'regex=' dans le fichier."
    grep -n 'regex=' api/models/chat.py
else
    echo "✓ Toutes les occurrences de 'regex' ont été remplacées."
fi

echo "3. Redémarrage du service API..."
docker-compose restart mar-api
echo "✓ Le service API a été redémarré."

# Attendre un peu que le service démarre
sleep 5

# Vérifier les logs
echo "4. Vérification des logs de l'API..."
docker logs mar-api --tail 20

echo "=== Correction terminée ==="
