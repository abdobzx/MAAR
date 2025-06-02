"""
Tâches Celery pour le traitement de documents.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union
from uuid import UUID

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from agents.ingestion.agent import IngestionAgent
from agents.vectorization.agent import VectorizationAgent
from agents.storage.agent import StorageAgent
from core.celery import celery_app
from core.exceptions import DocumentProcessingError
from core.logging import log_agent_action, log_error
from core.models import Document, DocumentStatus
from database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base class for async Celery tasks."""
    
    def run(self, *args, **kwargs):
        """Wrapper to run async functions in Celery."""
        return asyncio.run(self.async_run(*args, **kwargs))
    
    async def async_run(self, *args, **kwargs):
        """Override this method in subclasses."""
        raise NotImplementedError


@celery_app.task(bind=True, base=AsyncTask, max_retries=3)
async def process_document_task(self, document_id: str, processing_options: Optional[Dict] = None):
    """Traite un document de bout en bout."""
    
    try:
        doc_uuid = UUID(document_id)
        db_manager = DatabaseManager()
        
        async with db_manager.get_session() as session:
            # Récupérer le document
            document = await _get_document(session, doc_uuid)
            if not document:
                raise DocumentProcessingError(
                    f"Document {document_id} not found",
                    error_code="DOCUMENT_NOT_FOUND"
                )
            
            # Mise à jour du statut
            await _update_document_status(session, doc_uuid, DocumentStatus.PROCESSING)
            
            # Agents
            ingestion_agent = IngestionAgent()
            vectorization_agent = VectorizationAgent()
            storage_agent = StorageAgent()
            
            # Traitement par l'agent d'ingestion
            log_agent_action("document_processing", "starting_ingestion", {
                "document_id": document_id,
                "task_id": self.request.id
            })
            
            processed_doc = await ingestion_agent.process_document(document)
            
            # Vectorisation
            log_agent_action("document_processing", "starting_vectorization", {
                "document_id": document_id,
                "task_id": self.request.id
            })
            
            chunks = await vectorization_agent.vectorize_document(processed_doc)
            
            # Stockage
            log_agent_action("document_processing", "starting_storage", {
                "document_id": document_id,
                "chunks_count": len(chunks),
                "task_id": self.request.id
            })
            
            await storage_agent.store_document_chunks(chunks, session)
            
            # Mise à jour du statut final
            await _update_document_status(session, doc_uuid, DocumentStatus.COMPLETED)
            await session.commit()
            
            log_agent_action("document_processing", "completed", {
                "document_id": document_id,
                "chunks_created": len(chunks),
                "task_id": self.request.id
            })
            
            return {
                "status": "success",
                "document_id": document_id,
                "chunks_created": len(chunks),
                "task_id": self.request.id
            }
    
    except Exception as e:
        log_error(e, {
            "task": "process_document_task",
            "document_id": document_id,
            "task_id": self.request.id
        })
        
        # Mise à jour du statut d'erreur
        try:
            async with db_manager.get_session() as session:
                await _update_document_status(session, UUID(document_id), DocumentStatus.FAILED)
                await session.commit()
        except:
            pass
        
        # Retry logic
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60  # Exponential backoff
            raise self.retry(exc=e, countdown=countdown)
        
        raise DocumentProcessingError(
            f"Document processing failed after {self.max_retries} retries: {str(e)}",
            error_code="PROCESSING_FAILED"
        )


@celery_app.task(bind=True, base=AsyncTask)
async def batch_process_documents_task(self, document_ids: List[str], processing_options: Optional[Dict] = None):
    """Traite plusieurs documents en parallèle."""
    
    try:
        results = []
        
        # Traitement en parallèle avec limite de concurrence
        semaphore = asyncio.Semaphore(4)  # Limite à 4 documents simultanés
        
        async def process_single(doc_id: str):
            async with semaphore:
                task_result = await process_document_task.apply_async(
                    args=[doc_id, processing_options]
                ).get()
                return task_result
        
        # Exécution parallèle
        tasks = [process_single(doc_id) for doc_id in document_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyser les résultats
        successful = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
        failed = [r for r in results if isinstance(r, Exception)]
        
        log_agent_action("batch_processing", "completed", {
            "total_documents": len(document_ids),
            "successful": len(successful),
            "failed": len(failed),
            "task_id": self.request.id
        })
        
        return {
            "status": "completed",
            "total_documents": len(document_ids),
            "successful": len(successful),
            "failed": len(failed),
            "results": results,
            "task_id": self.request.id
        }
    
    except Exception as e:
        log_error(e, {
            "task": "batch_process_documents_task",
            "document_count": len(document_ids),
            "task_id": self.request.id
        })
        raise


@celery_app.task(bind=True, base=AsyncTask)
async def reprocess_failed_documents_task(self, max_documents: int = 50):
    """Retraite les documents en échec."""
    
    try:
        db_manager = DatabaseManager()
        
        async with db_manager.get_session() as session:
            # Récupérer les documents en échec
            failed_docs = await _get_failed_documents(session, max_documents)
            
            if not failed_docs:
                return {
                    "status": "completed",
                    "message": "No failed documents to reprocess",
                    "task_id": self.request.id
                }
            
            # Relancer le traitement
            document_ids = [str(doc.id) for doc in failed_docs]
            
            # Réinitialiser le statut
            for doc in failed_docs:
                await _update_document_status(session, doc.id, DocumentStatus.PENDING)
            await session.commit()
            
            # Lancer le traitement par batch
            result = await batch_process_documents_task.apply_async(
                args=[document_ids]
            ).get()
            
            log_agent_action("reprocessing", "completed", {
                "documents_reprocessed": len(document_ids),
                "task_id": self.request.id
            })
            
            return result
    
    except Exception as e:
        log_error(e, {
            "task": "reprocess_failed_documents_task",
            "task_id": self.request.id
        })
        raise


@celery_app.task(bind=True, base=AsyncTask)
async def update_document_embeddings_task(self, document_id: str, new_model: str):
    """Met à jour les embeddings d'un document avec un nouveau modèle."""
    
    try:
        doc_uuid = UUID(document_id)
        db_manager = DatabaseManager()
        
        async with db_manager.get_session() as session:
            # Récupérer le document et ses chunks
            document = await _get_document(session, doc_uuid)
            chunks = await _get_document_chunks(session, doc_uuid)
            
            if not document or not chunks:
                raise DocumentProcessingError(
                    f"Document or chunks not found for {document_id}",
                    error_code="DOCUMENT_NOT_FOUND"
                )
            
            # Vectorisation avec le nouveau modèle
            vectorization_agent = VectorizationAgent()
            storage_agent = StorageAgent()
            
            # Régénérer les embeddings
            updated_chunks = []
            for chunk in chunks:
                # Utiliser le nouveau modèle pour l'embedding
                new_embedding = await vectorization_agent._generate_embedding(
                    chunk.content, 
                    model_name=new_model
                )
                
                chunk.embedding = new_embedding
                chunk.metadata["embedding_model"] = new_model
                updated_chunks.append(chunk)
            
            # Mettre à jour le stockage
            await storage_agent.update_document_chunks(updated_chunks, session)
            await session.commit()
            
            log_agent_action("embedding_update", "completed", {
                "document_id": document_id,
                "new_model": new_model,
                "chunks_updated": len(updated_chunks),
                "task_id": self.request.id
            })
            
            return {
                "status": "success",
                "document_id": document_id,
                "new_model": new_model,
                "chunks_updated": len(updated_chunks),
                "task_id": self.request.id
            }
    
    except Exception as e:
        log_error(e, {
            "task": "update_document_embeddings_task",
            "document_id": document_id,
            "task_id": self.request.id
        })
        raise


# Fonctions utilitaires
async def _get_document(session: AsyncSession, document_id: UUID) -> Optional[Document]:
    """Récupère un document par son ID."""
    # Implémentation avec SQLAlchemy
    pass


async def _get_document_chunks(session: AsyncSession, document_id: UUID) -> List:
    """Récupère les chunks d'un document."""
    # Implémentation avec SQLAlchemy
    pass


async def _get_failed_documents(session: AsyncSession, limit: int) -> List:
    """Récupère les documents en échec."""
    # Implémentation avec SQLAlchemy
    pass


async def _update_document_status(session: AsyncSession, document_id: UUID, status: DocumentStatus):
    """Met à jour le statut d'un document."""
    # Implémentation avec SQLAlchemy
    pass
