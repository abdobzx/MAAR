#!/bin/bash
# Script pour déployer les corrections sur le serveur distant

# Afficher le processus
echo "=== Script de déploiement des corrections ==="

# 1. S'assurer que les fichiers corrigés sont bien en place
echo "1. Vérification des fichiers corrigés..."

# Vérifier dependencies.py
if grep -q "return api_permission_checker" api/auth/dependencies.py; then
    echo "Erreur: Le fichier dependencies.py contient encore du code problématique."
    exit 1
else
    echo "✓ Le fichier dependencies.py semble correct."
fi

# Vérifier prometheus.yml
if grep -q "^[^#].*retention.time\|^[^#].*retention.size" monitoring/prometheus/prometheus.yml; then
    echo "Erreur: Le fichier prometheus.yml contient encore des paramètres de rétention non commentés."
    exit 1
else
    echo "✓ Le fichier prometheus.yml semble correct."
fi

# 2. Arrêter tous les conteneurs
echo "2. Arrêt des conteneurs en cours..."
docker-compose down
echo "✓ Tous les conteneurs ont été arrêtés."

# 3. Nettoyer le cache Docker si nécessaire
echo "3. Nettoyage du cache Docker..."
docker-compose build --no-cache
echo "✓ Reconstruction des images terminée."

# 4. Démarrer les conteneurs
echo "4. Démarrage des conteneurs en cours..."
docker-compose up -d
echo "✓ Tous les conteneurs ont été démarrés."

# 5. Vérifier l'état des conteneurs
echo "5. Vérification de l'état des conteneurs..."
sleep 10  # Attendre que les conteneurs démarrent
docker-compose ps

# 6. Vérifier les logs pour s'assurer qu'il n'y a plus d'erreurs
echo "6. Vérification des logs..."
echo "=== Logs de mar-api ==="
docker logs mar-api --tail 20
echo "=== Logs de mar-prometheus ==="
docker logs mar-prometheus --tail 20

echo "=== Déploiement terminé ==="
echo "Pour un suivi continu des logs, utilisez 'docker-compose logs -f'"
