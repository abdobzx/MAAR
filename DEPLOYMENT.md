# 🚀 Guide de Déploiement et d'Utilisation - Plateforme MAR

## Table des Matières

1. [Installation Rapide](#installation-rapide)
2. [Configuration](#configuration)
3. [Déploiement Local](#déploiement-local)
4. [Déploiement Docker](#déploiement-docker)
5. [Déploiement Kubernetes](#déploiement-kubernetes)
6. [Utilisation de l'API](#utilisation-de-lapi)
7. [Interface Utilisateur](#interface-utilisateur)
8. [Ingestion de Documents](#ingestion-de-documents)
9. [Monitoring et Observabilité](#monitoring-et-observabilité)
10. [Dépannage](#dépannage)
11. [Maintenance](#maintenance)

## Installation Rapide

### Prérequis

- Python 3.9+
- Docker et Docker Compose
- Git
- 8GB RAM minimum
- 20GB d'espace disque libre

### Installation en 5 minutes

```bash
# 1. Cloner le repository
git clone <repository-url>
cd mar-platform

# 2. Configuration
cp .env.example .env
# Editez .env selon vos besoins

# 3. Démarrage avec Docker
make docker-up

# 4. Vérification
curl http://localhost:8000/health
```

🎉 **Votre plateforme MAR est prête !**

- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Interface: http://localhost:8501
- Monitoring: http://localhost:3000

## Configuration

### Variables d'Environnement Essentielles

```bash
# Dans votre fichier .env

# Authentification (CHANGEZ EN PRODUCTION!)
JWT_SECRET_KEY=your-super-secret-key-here

# Vector Store
VECTOR_STORE_TYPE=faiss
VECTOR_STORE_PATH=./data/vector_store

# LLM (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_LLM_MODEL=llama2

# API
API_PORT=8000
API_HOST=0.0.0.0
```

### Configuration des Modèles LLM

```bash
# Installer et démarrer Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve

# Télécharger des modèles
ollama pull llama2          # Modèle général
ollama pull mistral         # Modèle performant
ollama pull codellama       # Modèle pour le code
```

## Déploiement Local

### Méthode 1: Python Virtuel

```bash
# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Démarrer les services
make dev-start
```

### Méthode 2: Poetry

```bash
# Installer Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Installer et démarrer
poetry install
poetry run make dev-start
```

## Déploiement Docker

### Docker Compose (Recommandé)

```bash
# Démarrage complet
docker-compose up -d

# Services individuels
docker-compose up -d api        # API seulement
docker-compose up -d ui         # Interface seulement
docker-compose up -d monitoring # Monitoring seulement

# Logs
docker-compose logs -f api
```

### Docker individuel

```bash
# Construire les images
docker build -t mar-api .
docker build -t mar-ui ./ui/streamlit

# Lancer l'API
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  mar-api

# Lancer l'UI
docker run -d -p 8501:8501 \
  -e STREAMLIT_API_URL=http://host.docker.internal:8000 \
  mar-ui
```

## Déploiement Kubernetes

### Déploiement Rapide

```bash
# Appliquer les manifestes
kubectl apply -f k8s/manifests/

# Vérifier le déploiement
kubectl get pods -n mar-platform
kubectl get services -n mar-platform

# Accès local (port-forward)
kubectl port-forward service/mar-api 8000:8000 -n mar-platform
kubectl port-forward service/mar-ui 8501:8501 -n mar-platform
```

### Configuration Helm (Production)

```bash
# Installer Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Déployer avec Helm
helm install mar-platform ./k8s/helm-chart \
  --set ingress.host=mar.yourdomain.com \
  --set api.replicas=3 \
  --set monitoring.enabled=true
```

### Configuration Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mar-ingress
spec:
  rules:
  - host: mar.yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: mar-api
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mar-ui
            port:
              number: 8501
```

## Utilisation de l'API

### Authentification

```bash
# Créer un compte utilisateur
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password"
  }'

# Se connecter
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password"
  }'

# Utiliser le token (remplacez YOUR_TOKEN)
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Ingestion de Documents

```bash
# Ingérer du texte
curl -X POST "http://localhost:8000/api/v1/documents/ingest/text" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Votre contenu ici...",
    "metadata": {"source": "manual", "category": "test"}
  }'

# Ingérer un fichier
curl -X POST "http://localhost:8000/api/v1/documents/ingest/file" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "metadata={\"author\": \"John Doe\"}"
```

### Recherche et RAG

```bash
# Recherche vectorielle
curl -X POST "http://localhost:8000/api/v1/documents/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "intelligence artificielle",
    "k": 5
  }'

# Chat RAG
curl -X POST "http://localhost:8000/api/v1/chat/simple" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explique-moi l\'intelligence artificielle",
    "context_size": 3
  }'
```

## Interface Utilisateur

### Accès Streamlit

1. Ouvrez http://localhost:8501
2. Connectez-vous avec vos identifiants
3. Utilisez les onglets pour :
   - 📤 **Ingestion** : Charger des documents
   - 💬 **Chat** : Poser des questions
   - 🔍 **Recherche** : Explorer le contenu
   - 📊 **Monitoring** : Voir les métriques

### Fonctionnalités Principales

#### Onglet Ingestion
- Upload de fichiers (PDF, DOCX, TXT, MD)
- Ingestion de texte brut
- Configuration des paramètres de chunking
- Prévisualisation des métadonnées

#### Onglet Chat
- Interface conversationnelle
- Configuration du modèle LLM
- Historique des conversations
- Export des réponses

#### Onglet Recherche
- Recherche sémantique
- Filtrage par métadonnées
- Visualisation des scores de similarité
- Navigation dans les résultats

## Ingestion de Documents

### Script CLI

```bash
# Ingérer un fichier
python scripts/ingest_documents.py --file document.pdf

# Ingérer un répertoire
python scripts/ingest_documents.py --directory ./docs --recursive

# Avec métadonnées personnalisées
python scripts/ingest_documents.py --file manual.pdf \
  --metadata '{"category": "documentation", "version": "1.0"}'

# Voir les statistiques
python scripts/ingest_documents.py --stats
```

### Formats Supportés

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Extraction de texte et OCR |
| Word | `.docx` | Formatage préservé |
| Texte | `.txt` | Encodage auto-détecté |
| Markdown | `.md` | Structure préservée |
| JSON | `.json` | Extraction de champs |
| CSV | `.csv` | Conversion en texte |

### Bonnes Pratiques

1. **Structurez vos métadonnées** :
```json
{
  "title": "Titre du document",
  "author": "Auteur",
  "category": "documentation",
  "tags": ["tag1", "tag2"],
  "version": "1.0",
  "language": "fr",
  "source": "manual_upload"
}
```

2. **Optimisez le chunking** :
- Documents courts : chunk_size=500
- Documents longs : chunk_size=1000-1500
- overlap=20% de chunk_size

3. **Organisez par lots** :
```bash
# Ingestion par catégorie
python scripts/ingest_documents.py \
  --directory ./docs/manuals \
  --metadata '{"category": "manual", "batch": "2024-01"}'
```

## Monitoring et Observabilité

### Métriques Prometheus

Accédez à http://localhost:9090 pour Prometheus.

**Métriques principales** :
- `mar_requests_total` : Nombre de requêtes
- `mar_request_duration_seconds` : Durée des requêtes  
- `mar_documents_ingested_total` : Documents ingérés
- `mar_vector_store_size` : Taille du vector store
- `mar_llm_tokens_used_total` : Tokens LLM utilisés

### Dashboards Grafana

Accédez à http://localhost:3000 (admin/admin).

**Dashboards disponibles** :
1. **API Overview** : Métriques générales de l'API
2. **Document Processing** : Ingestion et recherche
3. **LLM Performance** : Utilisation des modèles
4. **System Resources** : CPU, RAM, stockage

### Logs

```bash
# Logs en temps réel
docker-compose logs -f api

# Logs avec filtrage
docker-compose logs api | grep ERROR

# Logs JSON structurés
tail -f logs/mar_platform.json | jq '.'

# Recherche dans les logs
grep "user_id" logs/mar_platform.json | jq '.message'
```

### Alertes

Les alertes sont configurées dans `monitoring/prometheus/rules/mar_alerts.yml`.

**Alertes critiques** :
- API indisponible
- Erreur rate > 5%
- Espace disque < 10%
- Mémoire > 90%

## Dépannage

### Problèmes Courants

#### 1. Ollama non accessible

```bash
# Vérifier Ollama
curl http://localhost:11434/api/tags

# Redémarrer Ollama
pkill ollama
ollama serve

# Logs Ollama
journalctl -u ollama -f
```

#### 2. Vector Store corrompu

```bash
# Sauvegarder et recréer
mv data/vector_store data/vector_store.backup
mkdir data/vector_store

# Ré-ingérer les documents
python scripts/ingest_documents.py --directory ./backup_docs
```

#### 3. API lente

```bash
# Vérifier les ressources
docker stats

# Augmenter les workers
export API_WORKERS=4
docker-compose restart api

# Optimiser la base de données
python scripts/optimize_db.py
```

#### 4. Erreurs d'authentification

```bash
# Régénérer la clé JWT
export JWT_SECRET_KEY=$(openssl rand -base64 32)

# Nettoyer les tokens
docker-compose restart redis

# Vérifier les permissions
python scripts/check_auth.py
```

### Logs de Debug

```bash
# Mode debug complet
export LOG_LEVEL=DEBUG
export DEV_MODE=true

# Logs détaillés par composant
export VECTOR_STORE_DEBUG=true
export LLM_DEBUG=true
export AGENTS_DEBUG=true
```

### Tests de Santé

```bash
# Test complet end-to-end
python scripts/test_end_to_end.py --verbose

# Test interactif
python scripts/test_end_to_end.py --interactive

# Test de charge
python scripts/load_test.py --users=10 --duration=60
```

## Maintenance

### Sauvegardes

```bash
# Sauvegarde manuelle
make backup

# Sauvegarde programmée (crontab)
0 2 * * * cd /path/to/mar && make backup

# Restauration
make restore BACKUP_FILE=backup_20240101_020000.tar.gz
```

### Mises à jour

```bash
# Mise à jour des dépendances
pip install -r requirements.txt --upgrade

# Mise à jour des images Docker
docker-compose pull
docker-compose up -d

# Migration des données
python scripts/migrate_data.py --version=1.1.0
```

### Optimisation

```bash
# Nettoyage des logs anciens
find logs/ -name "*.log" -mtime +30 -delete

# Compression du vector store
python scripts/compress_vector_store.py

# Optimisation des index
python scripts/optimize_search_index.py
```

### Surveillance

```bash
# Script de monitoring
python scripts/health_check.py --alert-webhook=$WEBHOOK_URL

# Métriques système
python scripts/system_metrics.py --export=prometheus

# Rapport hebdomadaire
python scripts/weekly_report.py --email=$ADMIN_EMAIL
```

## Support et Contribution

### Documentation Complète

- **API** : http://localhost:8000/docs
- **Architecture** : [ARCHITECTURE.md](ARCHITECTURE.md)
- **Développement** : [DEVELOPMENT.md](DEVELOPMENT.md)

### Support

1. **Issues GitHub** : Signaler des bugs
2. **Discussions** : Questions et suggestions
3. **Wiki** : Documentation communautaire

### Contribution

```bash
# Fork et clone
git fork https://github.com/username/mar-platform
git clone https://github.com/your-username/mar-platform

# Créer une branche
git checkout -b feature/nouvelle-fonctionnalite

# Tests et commits
make test
git commit -m "feat: nouvelle fonctionnalité"

# Pull request
git push origin feature/nouvelle-fonctionnalite
```

---

## 🎉 Félicitations !

Votre plateforme MAR est maintenant opérationnelle. Pour toute question ou assistance, consultez la documentation ou contactez l'équipe de support.

**Liens utiles** :
- 📚 Documentation API : http://localhost:8000/docs
- 🖥️ Interface utilisateur : http://localhost:8501  
- 📊 Monitoring : http://localhost:3000
- 🔍 Prometheus : http://localhost:9090
