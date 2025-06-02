"""
Gestionnaire de base de données avec pool de connexions et gestion avancée.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    async_sessionmaker, 
    AsyncSession,
    AsyncEngine
)
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import text
from sqlalchemy import event
from sqlalchemy.engine.events import PoolEvents

from core.config import get_settings
from core.logging import get_logger
from core.exceptions import DatabaseError
from database.models import Base


class DatabaseManager:
    """Gestionnaire principal de base de données avec fonctionnalités enterprise."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # Configuration du moteur de base de données
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        
        # Métriques de connexion
        self.connection_metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "total_queries": 0,
            "slow_queries": 0
        }
        
        # Configuration du pool de connexions
        self.pool_config = {
            "poolclass": QueuePool,
            "pool_size": self.settings.db_pool_size,
            "max_overflow": self.settings.db_max_overflow,
            "pool_timeout": self.settings.db_pool_timeout,
            "pool_recycle": self.settings.db_pool_recycle,
            "pool_pre_ping": True
        }
    
    async def initialize(self):
        """Initialise la connexion à la base de données."""
        
        try:
            self.logger.info("Initialisation de la base de données")
            
            # Construction de l'URL de connexion
            database_url = self._build_database_url()
            
            # Création du moteur async
            self._engine = create_async_engine(
                database_url,
                echo=self.settings.environment == "development",
                echo_pool=self.settings.environment == "development",
                **self.pool_config
            )
            
            # Configuration des événements de monitoring
            self._setup_monitoring_events()
            
            # Création du factory de sessions
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Test de connexion
            await self._test_connection()
            
            # Création des tables si nécessaire
            if self.settings.auto_create_tables:
                await self._create_tables()
            
            self.logger.info("Base de données initialisée avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de la DB: {str(e)}")
            raise DatabaseError(f"Impossible d'initialiser la base de données: {str(e)}")
    
    def _build_database_url(self) -> str:
        """Construit l'URL de connexion à la base de données."""
        
        # Gestion des différents types de bases de données
        if self.settings.database_url:
            return self.settings.database_url
        
        # Construction manuelle pour PostgreSQL
        if self.settings.db_password:
            return (
                f"postgresql+asyncpg://{self.settings.db_user}:"
                f"{self.settings.db_password}@{self.settings.db_host}:"
                f"{self.settings.db_port}/{self.settings.db_name}"
            )
        else:
            return (
                f"postgresql+asyncpg://{self.settings.db_user}@"
                f"{self.settings.db_host}:{self.settings.db_port}/"
                f"{self.settings.db_name}"
            )
    
    def _setup_monitoring_events(self):
        """Configure les événements de monitoring des connexions."""
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self.connection_metrics["total_connections"] += 1
            self.connection_metrics["active_connections"] += 1
            
        @event.listens_for(self._engine.sync_engine, "close")
        def on_disconnect(dbapi_connection, connection_record):
            self.connection_metrics["active_connections"] -= 1
            
        @event.listens_for(self._engine.sync_engine, "handle_error")
        def on_error(exception_context):
            self.connection_metrics["failed_connections"] += 1
            self.logger.error(
                f"Erreur de connexion DB: {exception_context.original_exception}"
            )
    
    async def _test_connection(self):
        """Teste la connexion à la base de données."""
        
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            self.logger.info("Test de connexion DB réussi")
            
        except Exception as e:
            self.logger.error(f"Test de connexion DB échoué: {str(e)}")
            raise DatabaseError(f"Test de connexion échoué: {str(e)}")
    
    async def _create_tables(self):
        """Crée les tables de la base de données."""
        
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self.logger.info("Tables créées avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création des tables: {str(e)}")
            raise DatabaseError(f"Impossible de créer les tables: {str(e)}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Gestionnaire de contexte pour les sessions de base de données."""
        
        if not self._session_factory:
            raise DatabaseError("Base de données non initialisée")
        
        session = self._session_factory()
        start_time = datetime.utcnow()
        
        try:
            self.logger.debug("Nouvelle session DB créée")
            yield session
            
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Erreur dans la session DB: {str(e)}")
            raise
            
        finally:
            await session.close()
            
            # Calcul du temps de session
            session_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Logging des sessions lentes
            if session_time > self.settings.slow_query_threshold:
                self.connection_metrics["slow_queries"] += 1
                self.logger.warning(
                    f"Session DB lente détectée: {session_time:.2f}s"
                )
            
            self.connection_metrics["total_queries"] += 1
            self.logger.debug(f"Session DB fermée après {session_time:.2f}s")
    
    async def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Exécute une requête SQL brute."""
        
        try:
            async with self.get_session() as session:
                result = await session.execute(text(query), params or {})
                await session.commit()
                return result
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
            raise DatabaseError(f"Erreur de requête: {str(e)}")
    
    async def health_check(self) -> bool:
        """Vérifie la santé de la connexion à la base de données."""
        
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
                
        except Exception as e:
            self.logger.error(f"Health check DB échoué: {str(e)}")
            return False
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de connexion."""
        
        pool_stats = {}
        
        if self._engine and hasattr(self._engine.pool, 'size'):
            pool_stats = {
                "pool_size": self._engine.pool.size(),
                "checked_in": self._engine.pool.checkedin(),
                "checked_out": self._engine.pool.checkedout(),
                "overflow": self._engine.pool.overflow(),
                "invalidated": self._engine.pool.invalidated()
            }
        
        return {
            **self.connection_metrics,
            "pool_stats": pool_stats,
            "engine_url": str(self._engine.url) if self._engine else None
        }
    
    async def backup_database(self, backup_path: str) -> bool:
        """Effectue une sauvegarde de la base de données (PostgreSQL)."""
        
        try:
            import subprocess
            import os
            
            # Commande pg_dump
            dump_command = [
                "pg_dump",
                "-h", self.settings.db_host,
                "-p", str(self.settings.db_port),
                "-U", self.settings.db_user,
                "-d", self.settings.db_name,
                "-f", backup_path,
                "--no-password"
            ]
            
            # Configuration de l'environnement
            env = os.environ.copy()
            if self.settings.db_password:
                env["PGPASSWORD"] = self.settings.db_password
            
            # Exécution de la commande
            process = await asyncio.create_subprocess_exec(
                *dump_command,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"Sauvegarde créée avec succès: {backup_path}")
                return True
            else:
                self.logger.error(f"Erreur lors de la sauvegarde: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde: {str(e)}")
            return False
    
    async def restore_database(self, backup_path: str) -> bool:
        """Restaure une sauvegarde de la base de données."""
        
        try:
            import subprocess
            import os
            
            # Commande psql pour la restauration
            restore_command = [
                "psql",
                "-h", self.settings.db_host,
                "-p", str(self.settings.db_port),
                "-U", self.settings.db_user,
                "-d", self.settings.db_name,
                "-f", backup_path
            ]
            
            # Configuration de l'environnement
            env = os.environ.copy()
            if self.settings.db_password:
                env["PGPASSWORD"] = self.settings.db_password
            
            # Exécution de la commande
            process = await asyncio.create_subprocess_exec(
                *restore_command,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"Restauration réussie depuis: {backup_path}")
                return True
            else:
                self.logger.error(f"Erreur lors de la restauration: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la restauration: {str(e)}")
            return False
    
    async def optimize_database(self) -> Dict[str, Any]:
        """Optimise la base de données (VACUUM, ANALYZE, etc.)."""
        
        optimization_results = {}
        
        try:
            async with self.get_session() as session:
                # VACUUM pour nettoyer l'espace
                await session.execute(text("VACUUM ANALYZE"))
                optimization_results["vacuum"] = "success"
                
                # Statistiques des tables
                table_stats = await session.execute(
                    text("""
                        SELECT 
                            schemaname,
                            tablename,
                            n_tup_ins + n_tup_upd + n_tup_del as total_operations,
                            n_dead_tup as dead_tuples
                        FROM pg_stat_user_tables
                        ORDER BY total_operations DESC
                        LIMIT 10
                    """)
                )
                
                optimization_results["top_tables"] = [
                    {
                        "schema": row[0],
                        "table": row[1], 
                        "operations": row[2],
                        "dead_tuples": row[3]
                    }
                    for row in table_stats.fetchall()
                ]
                
                await session.commit()
                
                self.logger.info("Optimisation de la base de données terminée")
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'optimisation: {str(e)}")
            optimization_results["error"] = str(e)
        
        return optimization_results
    
    async def close(self):
        """Ferme toutes les connexions à la base de données."""
        
        try:
            if self._engine:
                await self._engine.dispose()
                self.logger.info("Connexions DB fermées")
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la fermeture des connexions: {str(e)}")
    
    # Méthodes pour les migrations (si nécessaire)
    async def run_migration(self, migration_script: str) -> bool:
        """Exécute un script de migration."""
        
        try:
            async with self.get_session() as session:
                await session.execute(text(migration_script))
                await session.commit()
                
                self.logger.info("Migration exécutée avec succès")
                return True
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la migration: {str(e)}")
            return False
    
    async def check_migration_status(self) -> Dict[str, Any]:
        """Vérifie le statut des migrations."""
        
        try:
            async with self.get_session() as session:
                # Vérification de l'existence de la table de migrations
                migration_table_exists = await session.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'migrations'
                        )
                    """)
                )
                
                has_migration_table = migration_table_exists.scalar()
                
                if has_migration_table:
                    # Récupération des migrations appliquées
                    applied_migrations = await session.execute(
                        text("SELECT version, applied_at FROM migrations ORDER BY applied_at DESC")
                    )
                    
                    migrations = [
                        {"version": row[0], "applied_at": row[1]}
                        for row in applied_migrations.fetchall()
                    ]
                    
                    return {
                        "has_migration_table": True,
                        "applied_migrations": migrations,
                        "latest_migration": migrations[0] if migrations else None
                    }
                else:
                    return {
                        "has_migration_table": False,
                        "applied_migrations": [],
                        "latest_migration": None
                    }
                    
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des migrations: {str(e)}")
            return {"error": str(e)}
