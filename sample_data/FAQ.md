# FAQ - Plateforme MAR

## Questions fréquentes sur l'utilisation de la plateforme MAR

### 🚀 Démarrage rapide

**Q: Comment démarrer rapidement la plateforme ?**

R: Utilisez les commandes suivantes :
```bash
git clone https://github.com/your-org/mar-platform
cd mar-platform
make install
make up
```

**Q: Quels sont les prérequis système ?**

R: 
- Docker & Docker Compose
- Python 3.11+
- 8GB RAM minimum (16GB recommandé)
- 20GB espace disque libre
- GPU optionnel pour les modèles LLM

### 🤖 Agents et modèles

**Q: Quels modèles LLM sont supportés ?**

R: La plateforme utilise Ollama et supporte :
- Llama3 (7B, 13B, 70B)
- Mistral (7B)
- Phi-3 (mini, small, medium)
- CodeLlama
- Tous les modèles compatibles Ollama

**Q: Comment configurer un nouveau modèle ?**

R: 
1. Télécharger le modèle : `docker exec mar-ollama ollama pull nom-du-modele`
2. Mettre à jour la configuration dans `api/config.py`
3. Redémarrer l'API

**Q: Les agents fonctionnent-ils en parallèle ?**

R: Oui, CrewAI orchestre les agents selon le workflow configuré. Certaines tâches peuvent s'exécuter en parallèle pour optimiser la performance.

### 📁 Gestion des documents

**Q: Quels formats de documents sont supportés ?**

R: 
- PDF (via PyMuPDF)
- DOCX (via python-docx)  
- TXT (encodage auto-détecté)
- Markdown (.md)
- JSON (structure plate)

**Q: Comment optimiser l'ingestion de gros volumes ?**

R:
- Utilisez l'ingestion par batch via l'API
- Configurez une taille de chunk adaptée (default: 512 tokens)
- Surveillez l'utilisation mémoire du vector store

**Q: Peut-on supprimer des documents ingérés ?**

R: Oui, via l'API REST :
```bash
DELETE /api/v1/documents/{document_id}
```
Ou via l'interface Streamlit dans la section Documents.

### 🔍 Recherche et performance

**Q: Comment améliorer la qualité des résultats ?**

R:
1. Ajustez le seuil de similarité (default: 0.7)
2. Augmentez le nombre de documents récupérés
3. Activez la validation par le Critic Agent
4. Utilisez des modèles d'embedding plus performants

**Q: FAISS vs ChromaDB, lequel choisir ?**

R:
- **FAISS** : Plus rapide, optimal pour la production
- **ChromaDB** : Plus simple, meilleures métadonnées natives
- Recommandation : FAISS pour la production, ChromaDB pour le prototypage

**Q: Comment surveiller les performances ?**

R: Utilisez les dashboards Grafana préconfigurés :
- Latence des agents
- Throughput API
- Qualité des réponses (score Critic)
- Utilisation ressources

### 🔧 Configuration et personnalisation

**Q: Comment personnaliser les prompts des agents ?**

R: Modifiez les fichiers dans `agents/*/agent.py`. Chaque agent a son prompt système configurable.

**Q: Peut-on désactiver certains agents ?**

R: Oui, dans la configuration du crew ou via l'interface utilisateur lors de la requête.

**Q: Comment configurer l'authentification ?**

R: 
1. Configurez JWT_SECRET dans les variables d'environnement
2. Activez l'auth middleware dans `api/main.py`
3. Utilisez l'endpoint `/auth/token` pour obtenir un token

### 🐳 Déploiement et infrastructure

**Q: Comment déployer en production sur Kubernetes ?**

R:
```bash
# Adapter les manifests
vim k8s/manifests/*.yaml

# Déployer
make k8s-deploy

# Vérifier
make k8s-status
```

**Q: Comment configurer la haute disponibilité ?**

R:
- API : Minimum 3 replicas avec HPA
- Vector Store : Stockage persistant avec backup
- LLM : Pool de connexions Ollama
- Base de données : Redis Cluster si nécessaire

**Q: Quelle stratégie de sauvegarde recommandez-vous ?**

R:
1. Vector Store : Sauvegarde quotidienne du PVC
2. Configuration : Versioning Git
3. Logs : Retention 30 jours minimum
4. Métriques : Retention Prometheus 30 jours

### 🔒 Sécurité

**Q: La plateforme est-elle sécurisée ?**

R: Oui, avec :
- Authentification JWT
- Rate limiting
- Validation des inputs
- NetworkPolicies Kubernetes
- Scans de sécurité automatiques

**Q: Les données restent-elles locales ?**

R: Absolument. Tous les traitements sont locaux :
- LLM local via Ollama
- Vector store local (FAISS/ChromaDB)
- Aucune donnée envoyée vers des APIs externes

### 📊 Monitoring et debugging

**Q: Comment diagnostiquer un problème de performance ?**

R:
1. Vérifiez les métriques Grafana
2. Consultez les logs : `make logs`
3. Testez chaque composant séparément
4. Utilisez l'endpoint `/health` pour le diagnostic

**Q: Que faire si l'API ne répond plus ?**

R:
```bash
# Vérifier les logs
make logs-api

# Redémarrer l'API
docker restart mar-api

# Vérifier les dépendances
curl http://localhost:11434/api/tags  # Ollama
redis-cli ping  # Redis
```

**Q: Comment activer les logs de debug ?**

R: Définissez `LOG_LEVEL=DEBUG` dans les variables d'environnement et redémarrez les services.

### 🔄 Mise à jour et maintenance

**Q: Comment mettre à jour la plateforme ?**

R:
```bash
# Récupérer les dernières versions
git pull origin main

# Mettre à jour les dépendances
make install

# Reconstruire et redémarrer
make build && make restart
```

**Q: Comment migrer vers une nouvelle version du vector store ?**

R:
1. Sauvegardez les données actuelles
2. Migrez avec le script fourni
3. Testez sur un environnement de staging
4. Déployez en production

### 💡 Cas d'usage et exemples

**Q: Quels sont les cas d'usage typiques ?**

R:
- Support client avec base de connaissances
- Analyse de documents juridiques/techniques
- Recherche dans la documentation entreprise
- Assistant de recherche académique
- Génération de rapports automatisés

**Q: Peut-on intégrer la plateforme dans une application existante ?**

R: Oui, via :
- API REST complète avec OpenAPI
- SDK Python (à venir)
- Webhooks pour notifications
- Interface embeddable

### 🆘 Support

**Q: Où obtenir de l'aide ?**

R:
- Documentation : Consultez `/docs` dans le projet
- GitHub Issues : Pour les bugs et feature requests
- Discussions : Pour les questions générales
- Email : support@mar-platform.com pour le support prioritaire

**Q: Comment contribuer au projet ?**

R:
1. Fork le repository
2. Créez une branche feature
3. Suivez les conventions de code (Black, Flake8)
4. Ajoutez des tests
5. Ouvrez une Pull Request

---

**💡 Cette FAQ sera mise à jour régulièrement. N'hésitez pas à suggérer de nouvelles questions !**
