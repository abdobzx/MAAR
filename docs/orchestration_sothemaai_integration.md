# OrchestrationAgent SothemaAI Integration

## Vue d'ensemble

L'agent d'orchestration a été mis à jour pour intégrer de manière transparente le système de fournisseurs AI, avec un support prioritaire pour SothemaAI. Cette intégration maintient la compatibilité avec CrewAI et LangGraph tout en ajoutant une gestion avancée des fournisseurs LLM.

## Fonctionnalités ajoutées

### 1. Gestion des fournisseurs AI
- **AIProviderManager intégré** : L'agent utilise maintenant le gestionnaire centralisé de fournisseurs
- **Configuration SothemaAI** : Méthode `_setup_sothemaai_provider()` pour configurer automatiquement SothemaAI
- **Sélection de fournisseur prioritaire** : Méthode `_get_primary_provider()` avec logique de priorité

### 2. Système de priorité des fournisseurs
```
1. SothemaAI (si USE_SOTHEMAAI_ONLY=True et disponible)
2. SothemaAI (priorité par défaut)
3. Ollama
4. Cohere  
5. OpenAI
```

### 3. Orchestration avec fallback
- **Méthode `orchestrate_response_with_fallback()`** : Orchestration avec basculement automatique entre providers
- **Retry avec exponential backoff** : Tentatives multiples avec délai croissant
- **Métadonnées de provider** : Tracking du provider utilisé pour chaque requête

### 4. Intégration des nœuds de workflow
- **Nœud de synthèse** : Intégration directe avec l'agent de synthèse configuré
- **Nœud de vectorisation** : Intégration avec l'agent de vectorisation et ses providers
- **Gestion d'erreurs** : Fallback gracieux en cas d'échec des agents

## Structure du code

### Configuration des agents CrewAI
```python
def _setup_crew_agents(self):
    primary_provider = self._get_primary_provider()
    
    self.coordinator_agent = Agent(
        role="Workflow Coordinator",
        # ... autres paramètres ...
        llm=primary_provider if primary_provider else None
    )
```

### Nœud de synthèse intégré
```python
async def _synthesis_node(self, state: WorkflowState) -> WorkflowState:
    from agents.synthesis.agent import SynthesisAgent
    
    synthesis_agent = SynthesisAgent()
    response = await synthesis_agent.generate_response(query_request)
    
    # Mise à jour de l'état avec les résultats
    state.synthesis_result = response.response
    state.metadata["synthesis_provider"] = provider_info
```

### Orchestration avec fallback
```python
async def orchestrate_response_with_fallback(
    self, 
    request: OrchestrationRequest,
    max_retries: int = 3
) -> OrchestrationResponse:
    fallback_providers = ["sothemaai", "ollama", "cohere", "openai"]
    
    for attempt in range(max_retries):
        provider_name = fallback_providers[attempt % len(fallback_providers)]
        # Logique de retry avec provider spécifique
```

## Configuration

### Variables d'environnement requises
```bash
# SothemaAI
SOTHEMAAI_BASE_URL=http://localhost:8000
SOTHEMAAI_API_KEY=your-api-key

# Mode SothemaAI uniquement (optionnel)
USE_SOTHEMAAI_ONLY=true
```

### Configuration dans settings
```python
class LLMSettings(BaseSettings):
    sothemaai_base_url: Optional[str] = Field(None, env="SOTHEMAAI_BASE_URL")
    sothemaai_api_key: Optional[str] = Field(None, env="SOTHEMAAI_API_KEY")
    sothemaai_timeout: int = Field(30, env="SOTHEMAAI_TIMEOUT")
```

## Utilisation

### Orchestration standard
```python
orchestration_agent = OrchestrationAgent()

request = OrchestrationRequest(
    workflow_type=WorkflowType.SIMPLE_QA,
    query=search_query,
    user_id="user-123",
    organization_id="org-456"
)

response = await orchestration_agent.orchestrate_workflow(request)
```

### Orchestration avec fallback
```python
# Avec retry automatique sur différents providers
response = await orchestration_agent.orchestrate_response_with_fallback(
    request=request,
    max_retries=3
)

# Vérifier quel provider a été utilisé
used_provider = response.metadata.get("primary_provider")
```

## Monitoring et observabilité

### Métadonnées ajoutées
- `synthesis_provider` : Provider utilisé pour la synthèse
- `vectorization_provider` : Provider utilisé pour la vectorisation
- `primary_provider` : Provider principal utilisé pour l'orchestration
- `attempt_number` : Numéro de tentative en cas de fallback

### Logs structurés
```python
self.logger.info(
    f"Orchestration successful with provider: {provider_name}",
    extra={"workflow_id": workflow_id}
)
```

## Gestion d'erreurs

### Fallback gracieux
- **Provider indisponible** : Basculement automatique vers le provider suivant
- **Erreurs d'agent** : Logging des erreurs avec continuation du workflow
- **Échec total** : Réponse d'erreur structurée avec détails de debugging

### Codes d'erreur
- `OrchestrationError` : Erreur générale d'orchestration
- `ValidationError` : Erreur de validation des entrées
- Erreurs spécifiques aux agents (LLMError, etc.)

## Tests et validation

### Script de test intégré
```bash
python tests/test_orchestration_sothemaai_integration.py
```

### Script de validation
```bash
python validate_orchestration_integration.py
```

### Tests couverts
- Configuration des fournisseurs SothemaAI
- Logique de priorité des providers
- Intégration des nœuds de workflow
- Gestion d'erreurs et fallback
- Structure des requêtes d'orchestration

## Compatibilité

### Rétrocompatibilité
- **100% compatible** avec l'API existante
- **Dégradation gracieuse** si SothemaAI n'est pas disponible
- **Support des providers existants** (OpenAI, Cohere, Ollama)

### Dépendances
- `crewai` : Pour la coordination des agents
- `langgraph` : Pour l'orchestration des workflows
- `core.providers` : Système de gestion des fournisseurs AI

## Prochaines étapes

1. **Tests d'intégration complets** avec environnement SothemaAI réel
2. **Optimisation des performances** pour les workflows complexes
3. **Monitoring avancé** avec métriques de performance par provider
4. **Documentation API** pour les nouveaux endpoints
5. **Déploiement** avec configuration production

## Résumé des changements

| Fichier | Changements |
|---------|-------------|
| `agents/orchestration/agent.py` | Intégration complète AIProviderManager + SothemaAI |
| `tests/test_orchestration_sothemaai_integration.py` | Tests d'intégration complets |
| `validate_orchestration_integration.py` | Script de validation |

L'intégration maintient l'architecture existante tout en ajoutant une couche robuste de gestion des fournisseurs AI avec SothemaAI comme option prioritaire.
