#!/bin/bash
# Script pour vérifier que le déploiement est correct et redémarrer les services

echo "=== Vérification du déploiement ==="

# Vérifier le fichier dependencies.py
echo "1. Vérification du fichier dependencies.py..."
if grep -q "return api_permission_checker" api/auth/dependencies.py | grep -A 3 -B 3 "return permission_checker"; then
    echo "⚠️ ERREUR: Le fichier dependencies.py contient encore une ligne orpheline 'return api_permission_checker'."
    echo "   Veuillez vous assurer que les changements ont bien été poussés."
    exit 1
fi

if ! grep -q "def require_api_key_permission" api/auth/dependencies.py; then
    echo "⚠️ ERREUR: La fonction require_api_key_permission est manquante dans dependencies.py."
    echo "   Veuillez vous assurer que les changements ont bien été poussés."
    exit 1
fi

echo "✓ Le fichier dependencies.py est correctement configuré."

# Vérifier le fichier prometheus.yml
echo "2. Vérification du fichier prometheus.yml..."
if grep -q "^[^#].*retention.time\|^[^#].*retention.size" monitoring/prometheus/prometheus.yml; then
    echo "⚠️ ERREUR: Le fichier prometheus.yml contient des paramètres de rétention non commentés."
    echo "   Veuillez vous assurer que les changements ont bien été poussés."
    exit 1
fi

echo "✓ Le fichier prometheus.yml est correctement configuré."

# Redémarrer les conteneurs
echo "3. Redémarrage des conteneurs..."
docker-compose down
echo "✓ Tous les conteneurs ont été arrêtés."

# Reconstruire sans utiliser le cache
echo "4. Reconstruction des images..."
docker-compose build --no-cache
echo "✓ Les images ont été reconstruites."

# Redémarrer les conteneurs
echo "5. Démarrage des conteneurs..."
docker-compose up -d
echo "✓ Les conteneurs ont été démarrés."

# Attendre que les services démarrent
echo "6. Attente du démarrage des services..."
sleep 10

# Vérifier l'état des conteneurs
echo "7. Vérification de l'état des conteneurs..."
docker-compose ps

# Vérifier les logs pour confirmer qu'il n'y a plus d'erreurs
echo "8. Vérification des logs..."
echo "=== Logs de mar-api ==="
docker logs mar-api --tail 20
echo "=== Logs de mar-prometheus ==="
docker logs mar-prometheus --tail 20

echo "=== Vérification terminée ==="
echo "Si vous voyez encore des erreurs, veuillez relancer le script après quelques instants,"
echo "car certains services peuvent prendre plus de temps à démarrer correctement."
