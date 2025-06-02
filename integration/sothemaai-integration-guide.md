# Guide d'Intégration - Système RAG Multi-Agents avec SothemaAI

## Vue d'ensemble

Ce guide détaille l'intégration entre votre système RAG multi-agents et votre serveur SothemaAI pour utiliser ses services d'IA au lieu des fournisseurs externes (OpenAI, Cohere, Ollama).

## Architecture d'Intégration

```
┌─────────────────────────────────────────────────────────────────┐
│                  Système RAG Multi-Agents                       │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │ Research    │ │ Analysis    │ │ Synthesis   │ │ Reasoning   │ │
│ │ Agent       │ │ Agent       │ │ Agent       │ │ Agent       │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
│         │               │               │               │       │
│         └───────────────┼───────────────┼───────────────┘       │
│                         │               │                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │            SothemaAI Client Integration Layer              │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ HTTP/REST API
┌─────────────────────────────────────────────────────────────────┐
│                      SothemaAI Server                           │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│ │   Gateway   │ │    Auth     │ │ Inference   │ │  Frontend   │ │
│ │   Service   │ │   Service   │ │  Service    │ │   React     │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Requise

### 1. Variables d'Environnement SothemaAI

Ajoutez à votre fichier `.env` :

```env
# Configuration SothemaAI
SOTHEMAAI_BASE_URL=http://localhost:8000  # URL de votre serveur SothemaAI
SOTHEMAAI_API_KEY=your_api_key_here      # Clé API générée via l'interface SothemaAI
SOTHEMAAI_TIMEOUT=120                     # Timeout pour les requêtes (secondes)

# Désactiver les fournisseurs externes (optionnel)
USE_SOTHEMAAI_ONLY=true
OPENAI_API_KEY=                          # Laisser vide pour forcer l'utilisation de SothemaAI
COHERE_API_KEY=                          # Laisser vide pour forcer l'utilisation de SothemaAI
```

### 2. Endpoints SothemaAI Disponibles

Votre serveur SothemaAI expose les endpoints suivants :

- **Génération de texte** : `POST /api/inference/generate`
- **Embeddings** : `POST /api/inference/embed`
- **Authentification** : `POST /api/token`
- **Gestion des clés API** : `GET/POST/DELETE /api/auth/apikeys`

## Implémentation de l'Intégration

### 1. Créer le Client SothemaAI

Créez un nouveau fichier pour le client SothemaAI :
