# INSTRUCTIONS DE TEST DOCKER SUR SERVEUR

## 🎯 OBJECTIF
Valider que toutes les dépendances sont compatibles et que le système peut être déployé en production.

## 📋 ÉTAPES À SUIVRE

### 1. Transfert des Fichiers
Transférez ces fichiers sur votre serveur avec Docker :
```bash
# Fichiers essentiels à transférer:
- test-docker-server.sh          # Test complet
- test-docker-quick.sh           # Test rapide  
- requirements.docker.txt        # Requirements Docker optimisés
- requirements.python313.txt     # Requirements Python 3.13
- docker-compose.staging.yml     # Configuration staging
- Dockerfile.staging             # Dockerfile optimisé
- api/main.py                   # API principale
- core/                         # Modules core
```

### 2. Test Rapide (2-3 minutes)
Sur le serveur, exécutez d'abord le test rapide :
```bash
chmod +x test-docker-quick.sh
./test-docker-quick.sh
```

**RÉSULTAT ATTENDU :**
```
✅ Build réussi avec requirements.python313.txt
✅ ollama: OK
✅ httpx: 0.28.x
✅ Compatibilité confirmée
```

### 3. Test Complet (10-15 minutes)
Si le test rapide réussit, lancez le test complet :
```bash
chmod +x test-docker-server.sh
./test-docker-server.sh
```

**RÉSULTAT ATTENDU :**
```
✅ Docker version: ...
✅ Image de test construite avec succès
✅ ollama version: imported
✅ httpx version: 0.28.x
✅ FastAPI version: 0.108.0
✅ Qdrant client version: 1.14.x
✅ Tous les imports critiques réussis
✅ Syntaxe docker-compose valide
✅ Construction docker-compose réussie
✅ Services démarrés
🎉 VALIDATION TERMINÉE AVEC SUCCÈS!
```

### 4. En Cas d'Erreur
Si vous rencontrez des erreurs, envoyez-moi :

**A. Log du test rapide :**
```bash
./test-docker-quick.sh 2>&1 | tee test-quick.log
# Envoyez-moi le contenu de test-quick.log
```

**B. Log du test complet :**
```bash
./test-docker-server.sh 2>&1 | tee test-complete.log  
# Envoyez-moi le contenu de test-complete.log
```

**C. Informations système :**
```bash
docker --version
docker compose version
python3 --version
cat /etc/os-release
```

## 🚨 POINTS CRITIQUES À VÉRIFIER

1. **Compatibilité httpx/ollama** - C'était le problème principal
2. **Construction image Docker** - Doit réussir sans erreur
3. **Démarrage services** - Tous les conteneurs doivent démarrer
4. **API disponible** - L'endpoint /health doit répondre

## 📊 FEEDBACK DEMANDÉ

Envoyez-moi le résultat de cette commande :
```bash
echo "=== RÉSUMÉ DES TESTS ==="
echo "Test rapide: $(./test-docker-quick.sh > /dev/null 2>&1 && echo 'RÉUSSI' || echo 'ÉCHEC')"
echo "Test complet: $(./test-docker-server.sh > /dev/null 2>&1 && echo 'RÉUSSI' || echo 'ÉCHEC')"
echo "Docker version: $(docker --version)"
echo "Système: $(cat /etc/os-release | grep PRETTY_NAME)"
```

## ✅ SI TOUT FONCTIONNE

Le système sera prêt pour :
- Déploiement en production
- Utilisation avec docker-compose.staging.yml
- Scaling horizontal
- Intégration CI/CD

## ❌ SI IL Y A DES ERREURS

Je pourrai ajuster spécifiquement les requirements et la configuration Docker selon votre feedback.
