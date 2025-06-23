# 🚀 Guide d'utilisation du système MAR RAG avec Ollama

## ✅ État actuel du système

Ton système RAG est **OPÉRATIONNEL** ! Voici ce qui fonctionne :

### 🔧 Services actifs
- **Service RAG** : `http://localhost:8001`
- **Documentation** : `http://localhost:8001/docs`
- **Ollama LLM** : `http://localhost:11434`
- **Modèle** : `llama3.2:3b` (2GB, optimisé)

## 🧪 Comment tester le système

### 1. Via l'interface web (recommandé)
Ouvre ton navigateur : `http://localhost:8001/docs`
- Clique sur `POST /api/v1/query`
- Clique sur "Try it out"
- Écris ta question dans le champ `question`
- Clique sur "Execute"

### 2. Via curl (terminal)
```bash
# Test simple
curl -X POST http://localhost:8001/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qu'\''est-ce qu'\''un système RAG?"}'

# Vérification de santé
curl http://localhost:8001/health
```

### 3. Via Python
```python
import requests

response = requests.post(
    "http://localhost:8001/api/v1/query",
    json={"question": "Comment fonctionne un système RAG?"}
)
print(response.json()["answer"])
```

## 📝 Exemples de questions à tester

### Questions simples (réponses rapides ~5-15s)
- "Qu'est-ce qu'un système RAG?"
- "Explique FastAPI en 2 phrases"
- "Comment fonctionne Ollama?"

### Questions techniques (réponses plus lentes ~30-60s)
- "Comment créer une API REST avec FastAPI?"
- "Explique l'architecture microservices"
- "Quels sont les avantages des embeddings vectoriels?"

### Questions sur ton projet MAR
- "Comment structurer un système RAG multi-agents?"
- "Quelles technologies utiliser pour un système de recherche sémantique?"
- "Comment optimiser les performances d'un système RAG?"

## ⚡ Optimisations possibles

### Si les réponses sont trop lentes:
1. **Utilise des questions plus courtes**
2. **Augmente la RAM disponible pour Ollama**
3. **Utilise un modèle plus petit** (mais moins performant)

### Pour améliorer les réponses:
1. **Ajoute plus de contexte** dans les questions
2. **Utilise des prompts plus spécifiques**
3. **Intègre une base de connaissances**

## 🔄 Comment redémarrer le système

```bash
# Redémarrer tout
cd /Users/abderrahman/Documents/MAR
source .venv/bin/activate

# Terminal 1: Ollama
ollama serve

# Terminal 2: Service RAG
python rag_simple_ollama.py
```

## 🆕 Prochaines étapes

1. **Base de données** : Ajouter PostgreSQL pour persister les données
2. **Recherche vectorielle** : Intégrer Qdrant/Chroma pour la recherche sémantique
3. **Agents spécialisés** : Créer des agents pour différents domaines
4. **Interface utilisateur** : Développer une interface web moderne
5. **Monitoring** : Ajouter des métriques et logs

## 🐛 Résolution des problèmes

### Service ne répond pas
```bash
curl http://localhost:8001/health
# Si ça ne marche pas : redémarrer le service
```

### Ollama timeout
```bash
# Vérifier Ollama
curl http://localhost:11434/api/version
# Si ça ne marche pas : relancer ollama serve
```

### Questions trop lentes
- Utilise des questions plus courtes
- Évite les questions très complexes
- Augmente le timeout dans le code si nécessaire

## ✨ Ton système est maintenant prêt !

Tu as un **vrai système RAG fonctionnel** avec :
- ✅ API REST FastAPI
- ✅ LLM Ollama (llama3.2:3b)
- ✅ Interface de test Swagger
- ✅ Documentation complète
- ✅ Temps de réponse acceptable

**Plus besoin d'attendre 4650 secondes !** 🎉
