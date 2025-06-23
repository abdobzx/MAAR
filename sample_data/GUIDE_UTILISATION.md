# Guide d'utilisation de la plateforme MAR

## Vue d'ensemble

La plateforme MAR (Multi-Agent RAG) est un système avancé de traitement de documents utilisant plusieurs agents IA spécialisés pour fournir des réponses contextuelles et précises.

### Agents disponibles

1. **Retriever Agent** - Recherche vectorielle dans les documents
2. **Summarizer Agent** - Résumé des documents pertinents  
3. **Synthesizer Agent** - Synthèse et génération de réponses
4. **Critic Agent** - Validation et scoring de qualité
5. **Ranker Agent** - Classement et priorisation des résultats

## Fonctionnalités principales

### Recherche intelligente
- Recherche vectorielle haute performance avec FAISS/Chroma
- Support de multiples formats : PDF, DOCX, TXT, MD, JSON
- Chunking intelligent avec overlap pour préserver le contexte

### Traitement multi-agents
- Workflow orchestré par CrewAI
- Collaboration entre agents spécialisés
- Validation automatique de la qualité des réponses

### Observabilité complète
- Métriques Prometheus en temps réel
- Dashboards Grafana préconfiguré
- Logs centralisés avec ELK Stack
- Tracing des workflows agents

## Architecture technique

### Composants principaux
- **API FastAPI** : Interface REST avec authentification JWT
- **Service Ollama** : LLM local (Llama3, Mistral, Phi3)
- **Vector Store** : FAISS ou ChromaDB pour la recherche
- **Interface Streamlit** : UI moderne et interactive
- **Stack monitoring** : Prometheus, Grafana, ELK

### Déploiement
- **Local** : Docker Compose pour développement
- **Production** : Kubernetes avec haute disponibilité
- **CI/CD** : GitHub Actions avec tests automatisés
- **Sécurité** : JWT, rate limiting, CORS, NetworkPolicies

## Utilisation

### Installation rapide

```bash
# Cloner le projet
git clone https://github.com/your-org/mar-platform
cd mar-platform

# Installer les dépendances
make install

# Lancer la stack complète
make up
```

### Accès aux interfaces

- **Interface principale** : http://localhost:8501
- **API REST** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **Grafana** : http://localhost:3000 (admin/mar_admin_2024)
- **Prometheus** : http://localhost:9090

### Utilisation de l'API

```python
import requests

# Poster une question
response = requests.post("http://localhost:8000/api/v1/chat", 
    json={
        "query": "Comment fonctionne la recherche vectorielle ?",
        "max_documents": 5,
        "include_validation": True
    }
)

print(response.json())
```

### Ingestion de documents

```bash
# Via l'interface Streamlit (recommandé)
# Aller sur http://localhost:8501 > Documents > Upload

# Via l'API
curl -X POST "http://localhost:8000/api/v1/documents/ingest" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

## Configuration avancée

### Variables d'environnement

```bash
# Configuration LLM
OLLAMA_HOST=localhost:11434
OLLAMA_MODEL=llama3

# Configuration Vector Store  
VECTOR_STORE_TYPE=faiss  # ou chroma
VECTOR_STORE_PATH=/app/data/vector_store

# Configuration API
JWT_SECRET=your-secret-key
LOG_LEVEL=INFO
PROMETHEUS_ENABLED=true
```

### Personnalisation des agents

```python
# Dans orchestrator/crew/mar_crew.py
agent_config = {
    "retriever": {
        "max_documents": 10,
        "similarity_threshold": 0.7
    },
    "synthesizer": {
        "temperature": 0.5,
        "max_tokens": 2000
    }
}
```

## Monitoring et maintenance

### Métriques clés à surveiller

1. **Performance API**
   - Temps de réponse moyen < 3s
   - Taux d'erreur < 1%
   - Throughput requests/sec

2. **Agents MAR**
   - Latence par agent
   - Score de qualité Critic > 85%
   - Taux de succès retrieval > 95%

3. **Ressources système**
   - CPU < 80%
   - Mémoire < 80%  
   - Espace disque vector store

### Alertes automatiques

Les règles Prometheus incluent :
- API non accessible (30s)
- Temps de réponse élevé (>5s pendant 2min)
- Taux d'erreur élevé (>5% pendant 2min)
- Utilisation mémoire élevée (>2GB pendant 5min)

### Sauvegarde et restauration

```bash
# Sauvegarde automatique
make backup

# Sauvegarde manuelle du vector store
docker exec mar-api tar -czf /app/backup-$(date +%Y%m%d).tar.gz /app/data/vector_store
```

## Développement

### Structure du projet

```
mar-platform/
├── agents/          # Agents IA spécialisés
├── api/            # API FastAPI
├── orchestrator/   # Orchestrateur CrewAI  
├── vector_store/   # Module vector store
├── ui/             # Interface Streamlit
├── llm/            # Client LLM Ollama
├── k8s/            # Manifestes Kubernetes
├── monitoring/     # Configuration monitoring
└── tests/          # Tests automatisés
```

### Workflow de développement

```bash
# Installer l'environnement de dev
make install-dev

# Lancer en mode développement
make dev

# Exécuter les tests
make test

# Vérifier la qualité du code
make lint format

# Construire les images
make build
```

### Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## Troubleshooting

### Problèmes fréquents

**1. API ne démarre pas**
```bash
# Vérifier les logs
make logs-api

# Vérifier la connectivité Ollama
curl http://localhost:11434/api/tags
```

**2. Vector store vide**
```bash
# Ingérer des documents d'exemple
make ingest-sample

# Vérifier les stats
curl http://localhost:8000/api/v1/vector-store/stats
```

**3. Performance dégradée**
```bash
# Vérifier les métriques
make monitor

# Nettoyer le cache
docker exec mar-redis redis-cli FLUSHALL
```

### Support

- **Documentation** : http://docs.mar-platform.com
- **Issues GitHub** : https://github.com/your-org/mar-platform/issues
- **Discussions** : https://github.com/your-org/mar-platform/discussions
- **Email** : support@mar-platform.com

## Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

---

**🤖 Plateforme MAR - Intelligence artificielle locale et observable**
