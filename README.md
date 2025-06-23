<<<<<<< HEAD
# 🤖 Plateforme MAR (Multi-Agent RAG) 

## 🎯 Vue d'ensemble

Plateforme **industrielle, observable, sécurisée et 100% locale** combinant agents IA spécialisés, LLMs locaux, et systèmes de récupération vectorielle pour des applications RAG avancées.

**✅ Prête pour la production | 🔒 100% locale | 🚀 Auto-déployable | 📊 Observable**

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│   UI Frontend   │◄──►│   API Gateway    │◄──►│  Orchestrateur  │
│ (Streamlit/React│    │    (FastAPI)     │    │    (CrewAI)     │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │                  │    │                 │
                       │   LLM Service    │    │  Agents Pool    │
                       │    (Ollama)      │    │ Retriever/      │
                       │                  │    │ Summarizer/...  │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │                  │    │                 │
                       │  Vector Store    │    │  Observabilité  │
                       │ (FAISS/Chroma)   │    │ Prometheus/     │
                       │                  │    │ Grafana/ELK     │
                       └──────────────────┘    └─────────────────┘
=======
# 🚀 Système RAG Enterprise Multi-Agents

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.108+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.25+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Solution RAG (Retrieval-Augmented Generation) enterprise avec architecture multi-agents**

*Intelligence artificielle conversationnelle pour la gestion documentaire d'entreprise*

</div>

---

## 📋 Vue d'ensemble

Le **Système RAG Enterprise** est une plateforme complète de gestion documentaire intelligente qui utilise l'IA pour permettre aux entreprises d'interroger leurs données de manière conversationnelle. Notre architecture multi-agents assure un traitement spécialisé, une scalabilité enterprise et une sécurité renforcée.

### 🎯 Fonctionnalités clés

- 🤖 **7 Agents spécialisés** - Orchestration, ingestion, vectorisation, stockage, récupération, synthèse, feedback
- 📚 **Traitement multi-format** - PDF, DOCX, TXT, images (OCR), audio (transcription)
- 🔍 **Recherche hybride** - Vectorielle + mots-clés pour une précision optimale
- 🛡️ **Sécurité enterprise** - RBAC, chiffrement, audit complet
- 📊 **Monitoring complet** - Prometheus, Grafana, ELK Stack
- ⚡ **Performance optimisée** - Cache Redis, file d'attente Celery
- 🌐 **API REST complète** - Documentation OpenAPI intégrée

### 🏗️ Architecture

```mermaid
graph TB
    A[Client Web/API] --> B[Load Balancer]
    B --> C[FastAPI Gateway]
    
    C --> D[Agent Orchestrateur]
    D --> E[Agent Ingestion]
    D --> F[Agent Vectorisation]
    D --> G[Agent Stockage]
    D --> H[Agent Récupération]
    D --> I[Agent Synthèse]
    D --> J[Agent Feedback]
    
    E --> K[PostgreSQL]
    F --> L[Qdrant Vector DB]
    G --> M[MinIO Storage]
    H --> N[Redis Cache]
    I --> O[LLM APIs]
    J --> P[Celery Workers]
>>>>>>> origin/main
```

---

<<<<<<< HEAD
## 📁 Arborescence du Projet

```
📦 plateforme-mar/
├── 📁 agents/                      # Agents IA spécialisés
│   ├── 📁 retriever/              # Agent de récupération vectorielle
│   ├── 📁 summarizer/             # Agent de résumé
│   ├── 📁 synthesizer/            # Agent de synthèse contextualisée
│   ├── 📁 critic/                 # Agent de validation/QA
│   └── 📁 ranker/                 # Agent de classement (optionnel)
├── 📁 orchestrator/               # Orchestrateur CrewAI
│   ├── 📁 crew/                   # Définitions d'équipes
│   ├── 📁 tasks/                  # Tâches et workflows
│   └── 📁 tools/                  # Outils partagés
├── 📁 api/                        # API Gateway FastAPI
│   ├── 📁 routers/                # Endpoints par domaine
│   ├── 📁 middleware/             # Middleware custom
│   └── 📁 auth/                   # Authentification & sécurité
├── 📁 llm/                        # Service LLM local
│   ├── 📁 ollama/                 # Wrapper Ollama
│   ├── 📁 models/                 # Gestion des modèles
│   └── 📁 pooling/                # Pool de connexions
├── 📁 vector_store/               # Stockage vectoriel implémenté
│   ├── � __init__.py             # Module vector store
│   ├── 📄 models.py               # Modèles de données
│   ├── 📄 base.py                 # Interface abstraite
│   ├── 📄 faiss_store.py          # Implémentation FAISS
│   ├── � chroma_store.py         # Implémentation ChromaDB
│   └── � ingestion.py            # Système d'ingestion
├── 📁 ui/                         # Interfaces utilisateur
│   └── 📁 streamlit/              # UI Streamlit moderne
│       ├── � app.py              # Application principale
│       ├── � Dockerfile          # Image Docker UI
│       └── � requirements.txt    # Dépendances UI
├── 📁 docker/                     # Conteneurisation
│   ├── 📁 services/               # Dockerfiles par service
│   └── 📁 base/                   # Images de base
├── 📁 k8s/                        # Orchestration Kubernetes
│   ├── 📁 helm/                   # Charts Helm
│   │   ├── 📁 charts/             # Charts principaux
│   │   ├── 📁 templates/          # Templates Kubernetes
│   │   └── 📁 values/             # Valeurs par environnement
│   └── 📁 manifests/              # Manifestes YAML bruts
├── 📁 monitoring/                 # Observabilité complète
│   ├── 📁 prometheus/             # Métriques
│   │   ├── 📁 rules/              # Règles d'alerting
│   │   └── 📁 config/             # Configuration
│   ├── 📁 grafana/                # Visualisation
│   │   ├── 📁 dashboards/         # Tableaux de bord
│   │   └── 📁 datasources/        # Sources de données
│   └── 📁 elk/                    # Logs centralisés
│       ├── 📁 elasticsearch/      # Index et mapping
│       ├── 📁 logstash/           # Pipeline de traitement
│       └── 📁 kibana/             # Interface de recherche
├── 📁 ci-cd/                      # Déploiement continu
│   ├── 📁 github-actions/         # Pipelines GitHub
│   └── 📁 argocd/                 # GitOps (optionnel)
├── 📁 tests/                      # Tests automatisés
│   ├── 📁 unit/                   # Tests unitaires
│   ├── 📁 integration/            # Tests d'intégration
│   └── 📁 e2e/                    # Tests end-to-end
├── 📁 scripts/                    # Scripts utilitaires
│   ├── 📁 deployment/             # Scripts de déploiement
│   ├── 📁 maintenance/            # Scripts de maintenance
│   └── 📁 ingestion/              # Scripts d'ingestion
├── 📁 docs/                       # Documentation
│   ├── 📁 api/                    # Documentation API
│   ├── 📁 architecture/           # Architecture technique
│   └── 📁 deployment/             # Guide de déploiement
├── 📁 data/                       # Données
│   ├── 📁 documents/              # Documents sources
│   └── 📁 vectors/                # Index vectoriels
├── 📁 config/                     # Configuration
└── 📁 logs/                       # Logs locaux
```

---

## 🚀 Démarrage Rapide

### Prérequis

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Python** 3.10+
- **Node.js** 18+ (pour l'UI React)
- **Kubernetes** (Minikube/k3s pour local)

### Installation Express

```bash
# 1. Cloner le projet
git clone <repository-url>
cd plateforme-mar

# 2. Initialiser l'environnement
./scripts/deployment/init.sh

# 3. Démarrer tous les services
docker-compose up -d

# 4. Vérifier le déploiement
./scripts/deployment/health-check.sh

# 5. Accéder à l'interface
# Streamlit: http://localhost:8501
# React: http://localhost:3000
# API: http://localhost:8000/docs
# Grafana: http://localhost:3001
# Kibana: http://localhost:5601
=======
## 🚀 Démarrage rapide

### Prérequis

- **Python 3.11+**
- **Docker & Docker Compose**
- **Kubernetes 1.25+** (pour production)
- **Helm 3.8+**

### Installation locale (Développement)

1. **Cloner le repository**
   ```bash
   git clone <repository-url>
   cd MAR
   ```

2. **Configuration environnement**
   ```bash
   cp .env.example .env.development
   # Éditer .env.development avec vos clés API
   ```

3. **Lancer avec Docker Compose**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

4. **Vérifier l'installation**
   ```bash
   curl http://localhost:8000/health
   # Accéder à l'interface: http://localhost:8000/docs
   ```

### Déploiement production

Voir le [Guide de déploiement](docs/deployment-guide.md) pour les instructions complètes.

---

## 📖 Documentation

### 📚 Guides utilisateur
- [**Guide utilisateur**](docs/user-guide.md) - Interface et fonctionnalités
- [**Documentation API**](docs/api.md) - Référence des endpoints

### 🔧 Documentation technique
- [**Guide de déploiement**](docs/deployment-guide.md) - Installation et configuration
- [**Guide de production**](docs/production-deployment-guide.md) - Mise en production
- [**Maintenance opérationnelle**](docs/operational-maintenance-guide.md) - Opérations quotidiennes
- [**Plan de reprise d'activité**](docs/disaster-recovery-plan.md) - Procédures de récupération

---

## 🏗️ Architecture technique

### Composants principaux

| Composant | Description | Technologies |
|-----------|-------------|--------------|
| **API Gateway** | Interface REST FastAPI | FastAPI, Uvicorn |
| **Agents Multi-tâches** | Traitement spécialisé | CrewAI, LangChain |
| **Base vectorielle** | Stockage embeddings | Qdrant, Weaviate |
| **Base de données** | Métadonnées | PostgreSQL |
| **Cache & Queues** | Performance | Redis, Celery |
| **Stockage objet** | Documents | MinIO, S3 |
| **Monitoring** | Observabilité | Prometheus, Grafana, ELK |

### Agents spécialisés

1. **🎭 Agent Orchestrateur** - Coordination des workflows
2. **📥 Agent Ingestion** - Traitement des documents
3. **🧮 Agent Vectorisation** - Génération d'embeddings
4. **💾 Agent Stockage** - Persistance des données
5. **🔍 Agent Récupération** - Recherche contextuelle
6. **✍️ Agent Synthèse** - Génération de réponses
7. **🧠 Agent Feedback** - Apprentissage continu

---

## ⚙️ Configuration

### Variables d'environnement

Copiez `.env.example` vers `.env` et configurez :

```bash
# Application
APP_NAME=Enterprise RAG System
ENVIRONMENT=development
DEBUG=true

# APIs LLM
OPENAI_API_KEY=sk-your-openai-key
COHERE_API_KEY=your-cohere-key
ANTHROPIC_API_KEY=your-anthropic-key

# Bases de données
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=your-password
QDRANT_HOST=localhost
REDIS_URL=redis://localhost:6379
```

Voir [`.env.example`](.env.example) pour la configuration complète.

---

## 🧪 Tests

### Tests unitaires
```bash
python -m pytest tests/unit/ -v
```

### Tests d'intégration
```bash
python -m pytest tests/integration/ -v
```

### Tests de charge
```bash
cd tests/load
python -m locust -f locustfile.py --host=http://localhost:8000
>>>>>>> origin/main
```

---

<<<<<<< HEAD
## 🔧 Composants Principaux

### 🤖 Agents IA (CrewAI)

| Agent | Rôle | Responsabilités |
|-------|------|----------------|
| **Retriever** | Récupération | Index vectoriel, recherche sémantique |
| **Summarizer** | Résumé | Condensation de contenu |
| **Synthesizer** | Synthèse | Génération contextualisée |
| **Critic** | Validation | QA et vérification de cohérence |
| **Ranker** | Classement | Scoring et priorisation |

### 🧠 LLMs Supportés (Ollama)

- **LLaMA 3** (8B, 70B)
- **Mistral** (7B, 8x7B)
- **Phi-3** (3.8B, 14B)
- **Code Llama** (7B, 13B, 34B)

### 📊 Vector Stores

- **FAISS** : Recherche vectorielle haute performance
- **Chroma** : Base vectorielle avec métadonnées enrichies

### 🌐 API Gateway

- **FastAPI** avec documentation auto-générée
- **Authentification** JWT + API Keys
- **Rate Limiting** et CORS
- **Validation** automatique des schémas

---

## 📈 Observabilité

### Métriques (Prometheus + Grafana)
- 🖥️ **Système** : CPU, RAM, Disque, Réseau
- 🤖 **Agents** : Latence, succès, scores qualité
- 🧠 **LLM** : Tokens/s, temps de réponse, utilisation mémoire
- 🔍 **Vector Store** : Requêtes, index size, similarité

### Logs (ELK Stack)
- 📝 **Agents** : Exécutions, erreurs, performances
- 🌐 **API** : Requêtes, réponses, authentification
- 🧠 **LLM** : Prompts, générations, métriques
- 🔍 **Vector Store** : Recherches, indexations

### Alertes
- 🚨 **Downtime** : Services indisponibles
- ⚡ **Performance** : Latence élevée
- 💾 **Ressources** : Mémoire/CPU critique
- 🔍 **Qualité** : Scores agents dégradés

---

## 🔒 Sécurité

### Authentification
- **JWT Tokens** avec rotation automatique
- **API Keys** pour accès service-to-service
- **RBAC** : Contrôle d'accès basé sur les rôles

### Protection
- **Rate Limiting** : Protection contre le spam
- **CORS** : Configuration cross-origin
- **Validation** : Schémas Pydantic stricts
- **Secrets** : Vault ou ConfigMaps sécurisés
=======
## 📊 Monitoring

### Métriques disponibles

- **API** : Temps de réponse, taux d'erreur, throughput
- **Agents** : Performance individuelle, files d'attente
- **Infrastructure** : CPU, mémoire, stockage
- **Business** : Utilisation, satisfaction utilisateur

### Dashboards Grafana

- Dashboard système global
- Métriques par agent
- Performance API
- Alertes opérationnelles

---

## 🛡️ Sécurité

### Fonctionnalités de sécurité

- ✅ **Authentification SSO** - Keycloak, SAML, OIDC
- ✅ **Autorisation RBAC** - Permissions granulaires
- ✅ **Chiffrement** - TLS, données au repos
- ✅ **Audit complet** - Logs sécurisés
- ✅ **Network Policies** - Isolation réseau
- ✅ **Secrets Management** - Vault, K8s secrets

### Conformité

- **RGPD** - Protection des données personnelles
- **SOC 2** - Contrôles de sécurité
- **ISO 27001** - Gestion de la sécurité
>>>>>>> origin/main

---

## 🚀 Déploiement

<<<<<<< HEAD
### Local (Docker Compose)
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Production (Kubernetes)
```bash
# Via Helm
helm install mar-platform k8s/helm/charts/mar-platform

# Via manifestes
kubectl apply -k k8s/manifests/production
```

### CI/CD
```bash
# Tests automatiques
./.github/workflows/ci.yml

# Déploiement automatique
./.github/workflows/cd.yml
=======
### Environnements supportés

| Environnement | Description | Configuration |
|---------------|-------------|---------------|
| **Development** | Local avec Docker Compose | `docker-compose.dev.yml` |
| **Staging** | Pré-production Kubernetes | `values-staging.yaml` |
| **Production** | Production enterprise | `values-production.yaml` |

### Scripts de déploiement

```bash
# Déploiement staging
./scripts/deployment/deploy.sh staging v1.0.0

# Déploiement production
./scripts/deployment/deploy.sh production v1.0.0
>>>>>>> origin/main
```

---

<<<<<<< HEAD
## 🧪 Tests & Benchmarks

### Tests Automatisés
```bash
# Tests unitaires
pytest tests/unit/

# Tests d'intégration
pytest tests/integration/

# Tests end-to-end
pytest tests/e2e/
```

### Benchmarks
```bash
# Performance agents
python scripts/benchmark/agents_performance.py

# Latence LLM
python scripts/benchmark/llm_latency.py

# Précision vectorielle
python scripts/benchmark/vector_accuracy.py
```

---

## 📚 Documentation

- 📖 **[Guide Utilisateur](docs/user-guide.md)**
- 🏗️ **[Architecture Technique](docs/architecture/)**
- 🚀 **[Guide de Déploiement](docs/deployment/)**
- 🔧 **[API Documentation](docs/api/)**

---

## 🛠️ Configuration

### Variables d'Environnement

```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3:8b

# Vector Store
VECTOR_STORE_TYPE=faiss  # ou chroma
VECTOR_DIMENSION=1536

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET_KEY=your-secret-key

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3001
```

### Fichiers de Configuration

- `config/agents.yaml` : Configuration des agents
- `config/llm.yaml` : Paramètres LLM
- `config/vector-store.yaml` : Configuration vectorielle
- `config/monitoring.yaml` : Métriques et alertes

---

## 🔄 Workflow Complet

### Exemple de Requête RAG

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant API as API Gateway
    participant O as Orchestrateur
    participant R as Agent Retriever
    participant S as Agent Synthesizer
    participant L as LLM Ollama
    participant V as Vector Store

    U->>API: POST /chat {"query": "Qu'est-ce que...?"}
    API->>O: Créer tâche RAG
    O->>R: Récupérer contexte
    R->>V: Recherche vectorielle
    V-->>R: Documents similaires
    R-->>O: Contexte enrichi
    O->>S: Synthétiser réponse
    S->>L: Générer avec contexte
    L-->>S: Réponse générée
    S-->>O: Réponse finale
    O-->>API: Résultat complet
    API-->>U: Réponse formatée
```

---

## 💡 Fonctionnalités Avancées

### Auto-scaling
- **HPA** : Horizontal Pod Autoscaler pour K8s
- **Pool dynamique** : Agents à la demande
- **Load balancing** : Distribution intelligente

### Optimisations
- **Caching** : Redis pour réponses fréquentes
- **Compression** : Gzip pour transferts
- **Pooling** : Connexions réutilisables

### Extensibilité
- **Plugins** : Architecture modulaire
- **Webhooks** : Intégrations externes
- **APIs** : Standards OpenAPI 3.0

---

## 📞 Support & Contribution

### Issues & Bugs
Créer une issue avec les tags appropriés dans le repository.

### Contribution
1. Fork du repository
2. Créer une feature branch
3. Tests et documentation
4. Pull Request avec description détaillée

### Contact
- 📧 **Email** : support@mar-platform.com
- 💬 **Discord** : [Serveur communauté](https://discord.gg/mar-platform)
- 📚 **Wiki** : [Documentation complète](https://wiki.mar-platform.com)

---

## 📄 Licence

**MIT License** - Voir [LICENSE](LICENSE) pour plus de détails.

---

## 🎉 Remerciements

Merci à toutes les technologies open-source qui rendent cette plateforme possible :
- 🤖 **CrewAI** pour l'orchestration d'agents
- 🧠 **Ollama** pour les LLMs locaux
- 🔍 **FAISS/Chroma** pour la recherche vectorielle
- 📊 **Prometheus/Grafana** pour le monitoring
- 🐳 **Docker/Kubernetes** pour l'orchestration

---

**🚀 Plateforme MAR - L'avenir du RAG multi-agents est local !**
=======
## 📈 Performance

### Métriques de référence

- **Temps de réponse API** : < 200ms (P95)
- **Indexation document** : 10-50 documents/minute
- **Recherche vectorielle** : < 100ms (P95)
- **Throughput** : 1000+ requêtes/seconde
- **Disponibilité** : 99.9% SLA

### Optimisations

- Cache Redis multi-niveaux
- Index vectoriels optimisés
- Pool de connexions
- Auto-scaling Kubernetes

---

## 🛠️ Développement

### Structure du projet

```
MAR/
├── api/                 # API FastAPI
├── agents/             # Agents spécialisés
├── core/               # Configuration et utilitaires
├── database/           # Modèles et migrations
├── docs/               # Documentation
├── infrastructure/     # Kubernetes, Helm, monitoring
├── scripts/            # Scripts de déploiement
├── security/           # Authentification et autorisation
├── tasks/              # Tâches Celery
└── tests/              # Tests unitaires et intégration
```

### Contributing

1. Fork le repository
2. Créer une branche feature
3. Committer les changements
4. Pousser vers la branche
5. Créer une Pull Request

---

## 📝 Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

---

## 📞 Support

### Équipe de support

- 📧 **Email** : support@votre-entreprise.com
- 💬 **Slack** : #rag-system-support
- 📞 **Urgences** : +33 X XX XX XX XX (24/7)

### Ressources

- [**Documentation technique**](docs/) - Guides complets
- [**API Reference**](docs/api.md) - Référence des endpoints
- [**FAQ**](docs/user-guide.md#faq) - Questions fréquentes
- [**Runbooks**](docs/runbooks/) - Procédures d'incident

---

## 🔄 Roadmap

### Version 1.1 (Q1 2025)
- [ ] Support multimodal (images, graphiques)
- [ ] Agents conversationnels avancés
- [ ] Intégrations CRM/ERP
- [ ] Mobile app

### Version 1.2 (Q2 2025)
- [ ] Fine-tuning de modèles personnalisés
- [ ] Analyse de sentiment
- [ ] Workflow automation
- [ ] Multi-tenancy avancée

---

<div align="center">

**⭐ Si ce projet vous plaît, donnez-lui une étoile !**

[Documentation](docs/) • [API](docs/api.md) • [Déploiement](docs/deployment-guide.md) • [Support](docs/user-guide.md#contact-et-support)

---

*Développé avec ❤️ par l'équipe Enterprise RAG*

</div>
>>>>>>> origin/main
