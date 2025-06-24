#!/bin/bash
# Script pour installer les dépendances manquantes supplémentaires

echo "=== Installation des dépendances manquantes supplémentaires ==="

# Liste des dépendances à vérifier et installer
DEPENDENCIES=(
  "aiofiles>=23.0.0"
  "psutil>=5.9.0"
  # Ajoutez d'autres dépendances ici si nécessaire
)

# 1. Ajout des dépendances manquantes au fichier requirements.txt
echo "1. Vérification et ajout des dépendances manquantes au fichier requirements.txt..."

# Sauvegarde du fichier requirements.txt
cp requirements.txt requirements.txt.backup.$(date +%s)
echo "✓ Sauvegarde créée: requirements.txt.backup.$(date +%s)"

# Ajouter les dépendances si elles n'existent pas déjà
for dep in "${DEPENDENCIES[@]}"; do
  package=$(echo $dep | cut -d'>=' -f1)
  if ! grep -q "$package" requirements.txt; then
    echo "$dep" >> requirements.txt
    echo "✓ Dépendance '$dep' ajoutée au fichier requirements.txt"
  else
    echo "✓ La dépendance '$package' existe déjà dans requirements.txt"
  fi
done

# 2. Analyser les imports dans le code pour détecter d'autres dépendances manquantes
echo "2. Analyse des imports dans le code source..."
IMPORTS=$(grep -r "^import " --include="*.py" . | awk '{print $2}' | sort | uniq)
FROMS=$(grep -r "^from .* import" --include="*.py" . | awk '{print $2}' | grep -v "^\\." | sort | uniq)

echo "Modules importés détectés:"
echo "$IMPORTS"
echo "$FROMS"
echo "Note: Vérifiez manuellement s'il y a d'autres modules non standard à installer."

# 3. Reconstruire et redémarrer le conteneur
echo "3. Reconstruction et redémarrage du conteneur mar-api..."
docker-compose down
docker-compose build --no-cache mar-api
docker-compose up -d

echo "✓ Le conteneur mar-api a été reconstruit et redémarré."

# Attendre que le service démarre
echo "4. Attente du démarrage du service..."
sleep 15

# Vérifier les logs
echo "5. Vérification des logs de l'API..."
docker logs mar-api --tail 30

# Vérifier l'état des conteneurs
echo "6. Vérification de l'état des conteneurs..."
docker-compose ps

echo "=== Installation des dépendances terminée ==="
echo "Si vous voyez encore des erreurs de modules manquants, ajoutez-les au script et relancez-le."
