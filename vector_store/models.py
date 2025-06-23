"""
Modèles de données pour le vector store
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """Statut d'un document"""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(BaseModel):
    """
    Modèle pour un document à indexer
    """
    id: str = Field(..., description="Identifiant unique du document")
    content: str = Field(..., description="Contenu textuel du document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées du document")
    source: Optional[str] = Field(None, description="Source du document (URL, fichier, etc.)")
    title: Optional[str] = Field(None, description="Titre du document")
    author: Optional[str] = Field(None, description="Auteur du document")
    created_at: datetime = Field(default_factory=datetime.now, description="Date de création")
    updated_at: datetime = Field(default_factory=datetime.now, description="Date de modification")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="Statut du document")
    chunk_count: int = Field(default=0, description="Nombre de chunks générés")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DocumentChunk(BaseModel):
    """
    Modèle pour un chunk de document
    """
    id: str = Field(..., description="Identifiant unique du chunk")
    document_id: str = Field(..., description="ID du document parent")
    content: str = Field(..., description="Contenu du chunk")
    embedding: Optional[List[float]] = Field(None, description="Vecteur d'embedding")
    chunk_index: int = Field(..., description="Index du chunk dans le document")
    start_char: int = Field(..., description="Position de début dans le document")
    end_char: int = Field(..., description="Position de fin dans le document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées du chunk")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QueryResult(BaseModel):
    """
    Résultat d'une requête de recherche vectorielle
    """
    chunk: DocumentChunk = Field(..., description="Chunk trouvé")
    score: float = Field(..., description="Score de similarité")
    distance: float = Field(..., description="Distance vectorielle")
    rank: int = Field(..., description="Rang dans les résultats")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchQuery(BaseModel):
    """
    Modèle pour une requête de recherche
    """
    query: str = Field(..., description="Texte de la requête")
    max_results: int = Field(default=5, description="Nombre maximum de résultats")
    min_score: float = Field(default=0.0, description="Score minimum requis")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filtres de métadonnées")
    include_metadata: bool = Field(default=True, description="Inclure les métadonnées")
    
    class Config:
        validate_assignment = True


class IngestionStatus(BaseModel):
    """
    Statut d'une opération d'ingestion
    """
    job_id: str = Field(..., description="ID du job d'ingestion")
    status: DocumentStatus = Field(..., description="Statut global")
    total_documents: int = Field(default=0, description="Nombre total de documents")
    processed_documents: int = Field(default=0, description="Documents traités")
    failed_documents: int = Field(default=0, description="Documents échoués")
    start_time: datetime = Field(default_factory=datetime.now, description="Heure de début")
    end_time: Optional[datetime] = Field(None, description="Heure de fin")
    error_message: Optional[str] = Field(None, description="Message d'erreur si échec")
    
    @property
    def progress_percentage(self) -> float:
        """Calcule le pourcentage de progression"""
        if self.total_documents == 0:
            return 0.0
        return (self.processed_documents / self.total_documents) * 100
    
    @property
    def is_completed(self) -> bool:
        """Vérifie si l'ingestion est terminée"""
        return self.status in [DocumentStatus.INDEXED, DocumentStatus.FAILED]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
