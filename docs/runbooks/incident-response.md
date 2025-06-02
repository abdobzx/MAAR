# Runbook - Gestion des Incidents

## Classification des Incidents

### P1 - Critique (Résolution < 1h)
- Service complètement indisponible
- Perte de données
- Faille de sécurité active
- Performance dégradée > 50%

### P2 - Majeur (Résolution < 4h)
- Fonctionnalité majeure indisponible
- Performance dégradée 20-50%
- Erreurs intermittentes fréquentes

### P3 - Mineur (Résolution < 24h)
- Fonctionnalité mineure indisponible
- Performance dégradée < 20%
- Problèmes cosmétiques

## Procédure de Réponse aux Incidents

### 1. Détection et Alerte

```bash
# Vérification rapide de l'état du système
kubectl get pods -n rag-production
kubectl get services -n rag-production

# Test de santé de l'API
curl -f https://api.rag-system.com/health || echo "API DOWN"

# Vérification des métriques critiques
curl -s "http://prometheus:9090/api/v1/query?query=up{job='rag-api'}" | jq '.data.result[0].value[1]'
```

### 2. Escalade et Communication

#### Canal de Communication
- **Slack** : #rag-incidents
- **Email** : incidents@company.com
- **Téléphone** : Astreinte 24/7

#### Template de Communication
```
🚨 INCIDENT - P[1-3] - [Titre]

📅 Détecté: [Date/Heure]
🎯 Impact: [Description de l'impact]
👥 Affectés: [Nombre d'utilisateurs/services]
🔧 Actions: [Actions en cours]
⏱️ ETA: [Estimation de résolution]

Status page: https://status.rag-system.com
```

### 3. Investigation

#### Logs d'Application
```bash
# Logs de l'API principal
kubectl logs -f deployment/rag-api -n rag-production --tail=100

# Logs des agents Celery
kubectl logs -f deployment/rag-celery -n rag-production --tail=100

# Logs agrégés dans Kibana
# Accéder à https://kibana.company.com
# Query: service:"rag-api" AND level:ERROR AND @timestamp:[now-1h TO now]
```

#### Métriques de Performance
```bash
# CPU et Mémoire
kubectl top pods -n rag-production

# Métriques business dans Grafana
# Dashboard: "RAG System - Overview"
# Vérifier: Request Rate, Response Time, Error Rate

# Base de données
kubectl exec -it deployment/postgres -n rag-production -- psql -U postgres -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"
```

### 4. Actions de Mitigation

#### Redémarrage des Services
```bash
# Redémarrage rolling de l'API
kubectl rollout restart deployment/rag-api -n rag-production

# Redémarrage des workers Celery
kubectl rollout restart deployment/rag-celery -n rag-production

# Vérification du redémarrage
kubectl rollout status deployment/rag-api -n rag-production
```

#### Scaling d'Urgence
```bash
# Augmentation temporaire des ressources
kubectl patch deployment rag-api -n rag-production -p '{"spec":{"replicas":6}}'
kubectl patch deployment rag-celery -n rag-production -p '{"spec":{"replicas":4}}'

# Augmentation des limites de ressources
kubectl patch deployment rag-api -n rag-production -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "rag-api",
          "resources": {
            "limits": {"memory": "4Gi", "cpu": "2000m"},
            "requests": {"memory": "2Gi", "cpu": "1000m"}
          }
        }]
      }
    }
  }
}'
```

#### Mode Dégradé
```bash
# Activation du mode lecture seule
kubectl patch configmap rag-config -n rag-production --patch '{"data":{"READ_ONLY_MODE":"true"}}'

# Désactivation de fonctionnalités non critiques
kubectl patch configmap rag-config -n rag-production --patch '{"data":{"DISABLE_ANALYTICS":"true"}}'

# Redirection vers service de backup
kubectl patch ingress rag-ingress -n rag-production --patch '{
  "spec": {
    "rules": [{
      "host": "api.rag-system.com",
      "http": {
        "paths": [{
          "path": "/",
          "pathType": "Prefix",
          "backend": {
            "service": {
              "name": "rag-backup-service",
              "port": {"number": 8000}
            }
          }
        }]
      }
    }]
  }
}'
```

### 5. Résolution et Suivi

#### Checklist de Résolution
- [ ] Problème identifié et corrigé
- [ ] Services fonctionnels vérifiés
- [ ] Performance normale restaurée
- [ ] Tests de régression passés
- [ ] Monitoring vert sur 15 minutes
- [ ] Communication de résolution envoyée

#### Post-Mortem
```markdown
# Post-Mortem Incident #[ID]

## Résumé
**Date**: [Date]
**Durée**: [X] minutes
**Impact**: [Description]

## Timeline
- [HH:MM] Détection
- [HH:MM] Escalade
- [HH:MM] Investigation
- [HH:MM] Mitigation
- [HH:MM] Résolution

## Root Cause
[Description détaillée]

## Actions Correctives
1. [Action immédiate]
2. [Action à court terme]
3. [Action à long terme]

## Lessons Learned
[Points d'amélioration]
```

## Contacts d'Urgence

### Équipe Technique
- **DevOps Lead**: +33 X XX XX XX XX
- **SRE On-Call**: +33 X XX XX XX XX  
- **Security Team**: security@company.com

### Management
- **CTO**: cto@company.com
- **VP Engineering**: vp-eng@company.com

### Vendors
- **Cloud Provider**: [Numéro support]
- **Database Provider**: [Numéro support]
- **CDN Provider**: [Numéro support]
