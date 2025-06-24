# GUIDE DE RÉSOLUTION - Problème de connexion Ollama

## Problème identifié
L'API MAR n'arrive pas à se connecter au service Ollama car elle essaie de se connecter à `localhost:11434` au lieu de `ollama:11434` (nom du service Docker).

## Solutions créées

### 1. Solution rapide
```bash
./force-fix-ollama.sh
```
Ce script corrige de force tous les fichiers et redémarre les services.

### 2. Solution complète
```bash
./solution-globale.sh
```
Ce script exécute toutes les corrections dans le bon ordre :
- Correction des warnings dotenv
- Correction de la connexion Ollama  
- Correction des modules manquants
- Diagnostic final

### 3. Solution par étapes

#### Étape 1: Diagnostic
```bash
./diagnostic-rapide.sh
```

#### Étape 2: Corriger dotenv
```bash
./fix-dotenv-warnings.sh
```

#### Étape 3: Corriger Ollama
```bash
./fix-ollama-connection-definitive.sh
```

#### Étape 4: Corriger modules
```bash
./fix-missing-module.sh
```

## Scripts disponibles

| Script | Description |
|--------|-------------|
| `solution-globale.sh` | **RECOMMANDÉ** - Solution complète automatique |
| `force-fix-ollama.sh` | Correction forcée connexion Ollama |
| `fix-ollama-connection-definitive.sh` | Correction définitive Ollama |
| `fix-dotenv-warnings.sh` | Correction warnings python-dotenv |
| `fix-missing-module.sh` | Correction modules manquants (amélioré) |
| `diagnostic-rapide.sh` | Diagnostic complet du système |

## Commandes de diagnostic

```bash
# État des conteneurs
docker ps

# Logs de l'API
docker logs mar-api

# Logs d'Ollama  
docker logs mar-ollama

# Test de connectivité réseau
docker exec mar-api ping ollama

# Test de connectivité HTTP
docker exec mar-api curl http://ollama:11434/api/tags

# Test de santé de l'API
curl http://localhost:8008/health
```

## URLs de l'application une fois corrigée

- **API Health**: http://localhost:8008/health
- **API Documentation**: http://localhost:8008/docs  
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

## Corrections appliquées

1. **Fichiers source Python** : Remplacement de `localhost:11434` par `ollama:11434`
2. **Variables d'environnement** : Ajout de `OLLAMA_HOST=ollama:11434`
3. **Docker Compose** : Configuration des dépendances et variables
4. **Dockerfile** : Ajout des variables d'environnement
5. **Fichier .env** : Nettoyage et correction du format
6. **Modules manquants** : Création de `llm.pooling` et `orchestrator.tasks`

## En cas de problème persistant

1. Vérifiez que tous les conteneurs sont en cours d'exécution
2. Assurez-vous qu'Ollama est bien démarré en premier
3. Vérifiez les logs pour identifier l'erreur spécifique
4. Redémarrez les services dans l'ordre : Ollama puis API

```bash
docker-compose restart mar-ollama
sleep 10
docker-compose restart mar-api
```

## Support

Utilisez `./diagnostic-rapide.sh` pour obtenir un rapport complet de l'état du système.
