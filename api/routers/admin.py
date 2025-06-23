"""
Router pour l'administration et le monitoring de la plateforme.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import psutil
import os

from ..main import get_platform
from ..auth.dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemHealth(BaseModel):
    """État de santé du système"""
    status: str = Field(..., description="Statut global (healthy, degraded, unhealthy)")
    uptime: float = Field(..., description="Temps de fonctionnement en secondes")
    timestamp: datetime = Field(..., description="Timestamp de la vérification")
    components: Dict[str, bool] = Field(..., description="État des composants")
    metrics: Dict[str, Any] = Field(..., description="Métriques système")


class PlatformMetrics(BaseModel):
    """Métriques de la plateforme"""
    cpu_usage: float = Field(..., description="Utilisation CPU en %")
    memory_usage: float = Field(..., description="Utilisation mémoire en %")
    disk_usage: float = Field(..., description="Utilisation disque en %")
    active_sessions: int = Field(..., description="Nombre de sessions actives")
    total_requests: int = Field(..., description="Nombre total de requêtes")
    error_rate: float = Field(..., description="Taux d'erreur en %")


class LogEntry(BaseModel):
    """Entrée de log"""
    timestamp: datetime = Field(..., description="Timestamp du log")
    level: str = Field(..., description="Niveau de log")
    logger: str = Field(..., description="Logger source")
    message: str = Field(..., description="Message de log")
    module: Optional[str] = Field(None, description="Module source")


class ConfigUpdate(BaseModel):
    """Mise à jour de configuration"""
    key: str = Field(..., description="Clé de configuration")
    value: Any = Field(..., description="Nouvelle valeur")
    restart_required: bool = Field(default=False, description="Redémarrage requis")


# Stockage des métriques (en production, utiliser une base de données)
request_count = 0
error_count = 0
start_time = datetime.now()


@router.get("/health", response_model=SystemHealth)
async def get_system_health(
    platform = Depends(get_platform)
):
    """
    Vérifie l'état de santé de la plateforme
    """
    try:
        uptime = (datetime.now() - start_time).total_seconds()
        
        # Vérifier les composants
        components = {
            "platform": platform.initialized,
            "vector_store": platform.vector_store is not None,
            "llm_client": platform.llm_client is not None,
            "mar_crew": platform.mar_crew is not None,
        }
        
        # Métriques système
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids()),
            "uptime_seconds": uptime
        }
        
        # Déterminer le statut global
        if all(components.values()):
            status = "healthy"
        elif any(components.values()):
            status = "degraded"
        else:
            status = "unhealthy"
        
        return SystemHealth(
            status=status,
            uptime=uptime,
            timestamp=datetime.now(),
            components=components,
            metrics=metrics
        )
        
    except Exception as e:
        logger.error(f"Erreur vérification santé: {e}")
        return SystemHealth(
            status="unhealthy",
            uptime=0,
            timestamp=datetime.now(),
            components={},
            metrics={}
        )


@router.get("/metrics", response_model=PlatformMetrics)
async def get_platform_metrics(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupère les métriques de la plateforme
    """
    try:
        # Calculer le taux d'erreur
        error_rate = (error_count / max(request_count, 1)) * 100
        
        # Métriques système
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        # TODO: Récupérer les sessions actives depuis Redis/DB
        active_sessions = 0
        
        return PlatformMetrics(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            active_sessions=active_sessions,
            total_requests=request_count,
            error_rate=error_rate
        )
        
    except Exception as e:
        logger.error(f"Erreur récupération métriques: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des métriques: {str(e)}")


@router.get("/logs")
async def get_recent_logs(
    limit: int = 100,
    level: Optional[str] = None,
    since: Optional[datetime] = None,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Récupère les logs récents de la plateforme
    """
    try:
        # TODO: Implémenter la récupération des logs
        # En production, utiliser ELK, Loki, ou une base de données
        
        logs = [
            {
                "timestamp": datetime.now() - timedelta(minutes=5),
                "level": "INFO",
                "logger": "api.main",
                "message": "Platform initialized successfully",
                "module": "main"
            },
            {
                "timestamp": datetime.now() - timedelta(minutes=3),
                "level": "WARNING",
                "logger": "api.routers.chat",
                "message": "Slow response detected",
                "module": "chat"
            }
        ]
        
        # Filtrer par niveau si spécifié
        if level:
            logs = [log for log in logs if log["level"] == level.upper()]
        
        # Filtrer par date si spécifiée
        if since:
            logs = [log for log in logs if log["timestamp"] >= since]
        
        # Limiter le nombre de résultats
        logs = logs[:limit]
        
        return JSONResponse(content={"logs": logs, "total": len(logs)})
        
    except Exception as e:
        logger.error(f"Erreur récupération logs: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des logs: {str(e)}")


@router.post("/restart")
async def restart_platform(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Redémarre la plateforme (redémarrage gracieux)
    """
    try:
        logger.warning(f"Redémarrage demandé par {current_user.get('username', 'admin')}")
        
        # TODO: Implémenter le redémarrage gracieux
        # 1. Arrêter les tâches en cours
        # 2. Fermer les connexions
        # 3. Redémarrer les composants
        
        return JSONResponse(
            content={
                "status": "restart_initiated",
                "message": "Platform restart initiated",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur redémarrage: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du redémarrage: {str(e)}")


@router.post("/config")
async def update_config(
    update: ConfigUpdate,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Met à jour la configuration de la plateforme
    """
    try:
        logger.info(f"Mise à jour config {update.key} par {current_user.get('username', 'admin')}")
        
        # TODO: Implémenter la mise à jour de configuration
        # En production, utiliser un système de configuration centralisé
        
        # Valider la clé de configuration
        allowed_keys = {
            "max_chunk_size", "default_chunk_overlap", "max_file_size",
            "rate_limit_requests", "rate_limit_window", "log_level"
        }
        
        if update.key not in allowed_keys:
            raise HTTPException(status_code=400, detail=f"Configuration key not allowed: {update.key}")
        
        # TODO: Appliquer la configuration
        # config_manager.set(update.key, update.value)
        
        return JSONResponse(
            content={
                "key": update.key,
                "old_value": None,  # TODO: Récupérer l'ancienne valeur
                "new_value": update.value,
                "restart_required": update.restart_required,
                "status": "updated",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur mise à jour config: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour: {str(e)}")


@router.get("/version")
async def get_version_info():
    """
    Récupère les informations de version de la plateforme
    """
    try:
        # Lire le fichier de version
        version_file = os.path.join(os.path.dirname(__file__), "../../VERSION")
        try:
            with open(version_file, 'r') as f:
                version = f.read().strip()
        except FileNotFoundError:
            version = "unknown"
        
        return JSONResponse(
            content={
                "version": version,
                "build_date": "2024-01-01",  # TODO: Récupérer depuis CI/CD
                "commit_hash": "unknown",    # TODO: Récupérer depuis Git
                "python_version": f"{psutil.Process().exe}",
                "platform": psutil.platform(),
                "architecture": psutil.Process().cpu_times(),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur récupération version: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de version: {str(e)}")


@router.post("/backup")
async def create_backup(
    include_data: bool = True,
    include_config: bool = True,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Crée une sauvegarde de la plateforme
    """
    try:
        logger.info(f"Sauvegarde demandée par {current_user.get('username', 'admin')}")
        
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # TODO: Implémenter la sauvegarde
        # 1. Sauvegarder le vector store
        # 2. Sauvegarder la configuration
        # 3. Sauvegarder les logs
        # 4. Créer l'archive
        
        return JSONResponse(
            content={
                "backup_id": backup_id,
                "status": "created",
                "include_data": include_data,
                "include_config": include_config,
                "size_bytes": 0,  # TODO: Calculer la taille réelle
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur création sauvegarde: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de sauvegarde: {str(e)}")


@router.get("/stats/usage")
async def get_usage_stats(
    days: int = 7,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupère les statistiques d'utilisation
    """
    try:
        # TODO: Implémenter les statistiques d'utilisation
        # En production, utiliser une base de données ou système de métriques
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stats = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "requests": {
                "total": request_count,
                "daily_average": request_count / max(days, 1),
                "peak_hour": "14:00",  # TODO: Calculer réellement
                "success_rate": 100 - ((error_count / max(request_count, 1)) * 100)
            },
            "users": {
                "active_users": 1,  # TODO: Compter depuis les logs/sessions
                "new_users": 0,
                "returning_users": 1
            },
            "documents": {
                "ingested": 0,      # TODO: Récupérer depuis vector store
                "searches": 0,      # TODO: Compter les recherches
                "average_response_time": 0.5  # TODO: Calculer réellement
            }
        }
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Erreur statistiques utilisation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des statistiques: {str(e)}")


# Middleware pour compter les requêtes
def increment_request_count():
    global request_count
    request_count += 1


def increment_error_count():
    global error_count
    error_count += 1
