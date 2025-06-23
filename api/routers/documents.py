"""
Router pour la gestion des documents et l'ingestion.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid
import os
import tempfile
import aiofiles

from ..main import get_platform
from ..auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentIngestionRequest(BaseModel):
    """Requête d'ingestion de document"""
    content: str = Field(..., description="Contenu du document à ingérer")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées du document")
    chunk_size: Optional[int] = Field(default=1000, description="Taille des chunks")
    chunk_overlap: Optional[int] = Field(default=200, description="Chevauchement entre chunks")


class DocumentIngestionResponse(BaseModel):
    """Réponse d'ingestion de document"""
    document_id: str = Field(..., description="ID unique du document")
    chunks_count: int = Field(..., description="Nombre de chunks créés")
    status: str = Field(..., description="Statut de l'ingestion")
    processing_time: float = Field(..., description="Temps de traitement en secondes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées du document")


class VectorStoreStats(BaseModel):
    """Statistiques du vector store"""
    total_documents: int = Field(..., description="Nombre total de documents")
    total_chunks: int = Field(..., description="Nombre total de chunks")
    vector_dimension: int = Field(..., description="Dimension des vecteurs")
    index_size_mb: float = Field(..., description="Taille de l'index en MB")
    last_update: datetime = Field(..., description="Dernière mise à jour")


class SearchRequest(BaseModel):
    """Requête de recherche dans le vector store"""
    query: str = Field(..., description="Requête de recherche")
    k: int = Field(default=5, ge=1, le=50, description="Nombre de résultats à retourner")
    threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Seuil de similarité")
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Filtres de métadonnées")


class SearchResult(BaseModel):
    """Résultat de recherche"""
    document_id: str = Field(..., description="ID du document")
    chunk_id: str = Field(..., description="ID du chunk")
    content: str = Field(..., description="Contenu du chunk")
    score: float = Field(..., description="Score de similarité")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées")


class SearchResponse(BaseModel):
    """Réponse de recherche"""
    query: str = Field(..., description="Requête originale")
    results: List[SearchResult] = Field(..., description="Résultats de la recherche")
    total_results: int = Field(..., description="Nombre total de résultats")
    processing_time: float = Field(..., description="Temps de traitement en secondes")


@router.post("/ingest/text", response_model=DocumentIngestionResponse)
async def ingest_text_document(
    request: DocumentIngestionRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Ingère un document texte dans le vector store
    """
    try:
        logger.info(f"Ingestion texte demandée par {current_user.get('username', 'anonymous')}")
        
        if not platform.initialized:
            raise HTTPException(status_code=503, detail="Platform not initialized")
        
        if not platform.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        start_time = datetime.now()
        document_id = str(uuid.uuid4())
        
        # Ajouter des métadonnées par défaut
        metadata = {
            **request.metadata,
            "document_id": document_id,
            "ingested_by": current_user.get("username", "anonymous"),
            "ingested_at": datetime.now().isoformat(),
            "content_type": "text"
        }
        
        # Ingérer le document
        chunks_count = await platform.vector_store.ingest_text(
            content=request.content,
            metadata=metadata,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Document {document_id} ingéré: {chunks_count} chunks en {processing_time:.2f}s")
        
        return DocumentIngestionResponse(
            document_id=document_id,
            chunks_count=chunks_count,
            status="success",
            processing_time=processing_time,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Erreur ingestion texte: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'ingestion: {str(e)}")


@router.post("/ingest/file", response_model=DocumentIngestionResponse)
async def ingest_file_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(default="{}"),
    chunk_size: int = Form(default=1000),
    chunk_overlap: int = Form(default=200),
    background_tasks: BackgroundTasks = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Ingère un fichier document dans le vector store
    """
    try:
        logger.info(f"Ingestion fichier demandée par {current_user.get('username', 'anonymous')}: {file.filename}")
        
        if not platform.initialized:
            raise HTTPException(status_code=503, detail="Platform not initialized")
        
        if not platform.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        # Vérifier le type de fichier
        allowed_extensions = {'.txt', '.pdf', '.docx', '.md'}
        file_extension = os.path.splitext(file.filename or "")[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Type de fichier non supporté: {file_extension}. Types autorisés: {allowed_extensions}"
            )
        
        start_time = datetime.now()
        document_id = str(uuid.uuid4())
        
        # Traiter les métadonnées
        import json
        try:
            file_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            file_metadata = {}
        
        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Ajouter des métadonnées par défaut
            enhanced_metadata = {
                **file_metadata,
                "document_id": document_id,
                "filename": file.filename,
                "file_size": len(content),
                "file_type": file_extension,
                "ingested_by": current_user.get("username", "anonymous"),
                "ingested_at": datetime.now().isoformat(),
                "content_type": "file"
            }
            
            # Ingérer le fichier
            chunks_count = await platform.vector_store.ingest_file(
                file_path=temp_file_path,
                metadata=enhanced_metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Fichier {file.filename} ingéré: {chunks_count} chunks en {processing_time:.2f}s")
            
            return DocumentIngestionResponse(
                document_id=document_id,
                chunks_count=chunks_count,
                status="success",
                processing_time=processing_time,
                metadata=enhanced_metadata
            )
            
        finally:
            # Nettoyer le fichier temporaire
            os.unlink(temp_file_path)
        
    except Exception as e:
        logger.error(f"Erreur ingestion fichier: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'ingestion: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Recherche dans le vector store
    """
    try:
        logger.info(f"Recherche demandée par {current_user.get('username', 'anonymous')}: {request.query}")
        
        if not platform.initialized:
            raise HTTPException(status_code=503, detail="Platform not initialized")
        
        if not platform.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        start_time = datetime.now()
        
        # Effectuer la recherche
        results = await platform.vector_store.search(
            query=request.query,
            k=request.k,
            threshold=request.threshold,
            metadata_filter=request.metadata_filter
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Formater les résultats
        formatted_results = [
            SearchResult(
                document_id=result.get("document_id", "unknown"),
                chunk_id=result.get("chunk_id", "unknown"),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                metadata=result.get("metadata", {})
            )
            for result in results
        ]
        
        logger.info(f"Recherche '{request.query}': {len(formatted_results)} résultats en {processing_time:.2f}s")
        
        return SearchResponse(
            query=request.query,
            results=formatted_results,
            total_results=len(formatted_results),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Erreur recherche: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")


@router.get("/stats", response_model=VectorStoreStats)
async def get_vector_store_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Récupère les statistiques du vector store
    """
    try:
        logger.info(f"Statistiques demandées par {current_user.get('username', 'anonymous')}")
        
        if not platform.initialized:
            raise HTTPException(status_code=503, detail="Platform not initialized")
        
        if not platform.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        # Récupérer les statistiques
        stats = await platform.vector_store.get_stats()
        
        return VectorStoreStats(
            total_documents=stats.get("total_documents", 0),
            total_chunks=stats.get("total_chunks", 0),
            vector_dimension=stats.get("vector_dimension", 0),
            index_size_mb=stats.get("index_size_mb", 0.0),
            last_update=stats.get("last_update", datetime.now())
        )
        
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des statistiques: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Supprime un document du vector store
    """
    try:
        logger.info(f"Suppression document {document_id} demandée par {current_user.get('username', 'anonymous')}")
        
        if not platform.initialized:
            raise HTTPException(status_code=503, detail="Platform not initialized")
        
        if not platform.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        # Supprimer le document
        deleted_count = await platform.vector_store.delete_document(document_id)
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"Document {document_id} supprimé: {deleted_count} chunks")
        
        return JSONResponse(
            content={
                "document_id": document_id,
                "deleted_chunks": deleted_count,
                "status": "success"
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur suppression document: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")


@router.post("/clear")
async def clear_vector_store(
    current_user: Dict[str, Any] = Depends(get_current_user),
    platform = Depends(get_platform)
):
    """
    Vide complètement le vector store (ATTENTION: irréversible)
    """
    try:
        logger.warning(f"Vidage complet demandé par {current_user.get('username', 'anonymous')}")
        
        if not platform.initialized:
            raise HTTPException(status_code=503, detail="Platform not initialized")
        
        if not platform.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        # Vérifier les permissions (seuls les admins peuvent vider)
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin role required for this operation")
        
        # Vider le vector store
        cleared_count = await platform.vector_store.clear()
        
        logger.warning(f"Vector store vidé: {cleared_count} documents supprimés")
        
        return JSONResponse(
            content={
                "cleared_documents": cleared_count,
                "status": "success",
                "warning": "All documents have been permanently deleted"
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur vidage vector store: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du vidage: {str(e)}")
