#!/usr/bin/env python3
"""
Script CLI pour l'ingestion de documents dans la plateforme MAR.

Usage:
    python scripts/ingest_documents.py --file document.pdf --metadata '{"source": "manual"}'
    python scripts/ingest_documents.py --text "Contenu à ingérer" --chunk-size 500
    python scripts/ingest_documents.py --directory ./docs --recursive
"""

import os
import sys
import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import aiofiles

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vector_store import create_vector_store
from vector_store.ingestion import DocumentIngestionPipeline

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentIngestionCLI:
    """Interface CLI pour l'ingestion de documents"""
    
    def __init__(self):
        self.vector_store = None
        self.pipeline = None
    
    async def initialize(self, store_type: str = "faiss", store_config: Dict[str, Any] = None):
        """Initialise le vector store et le pipeline d'ingestion"""
        try:
            # Configuration par défaut
            if store_config is None:
                store_config = {
                    "persist_directory": os.getenv("VECTOR_STORE_PATH", "./data/vector_store"),
                    "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
                }
            
            # Créer le vector store
            self.vector_store = await create_vector_store(store_type, store_config)
            
            # Créer le pipeline d'ingestion
            self.pipeline = DocumentIngestionPipeline(self.vector_store)
            
            logger.info(f"Vector store {store_type} initialisé")
            
        except Exception as e:
            logger.error(f"Erreur initialisation: {e}")
            raise
    
    async def ingest_file(
        self, 
        file_path: str, 
        metadata: Dict[str, Any] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Dict[str, Any]:
        """Ingère un fichier dans le vector store"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
            
            logger.info(f"Ingestion du fichier: {file_path}")
            
            # Métadonnées par défaut
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "filename": file_path.name,
                "file_path": str(file_path.absolute()),
                "file_size": file_path.stat().st_size,
                "ingestion_method": "cli"
            })
            
            # Ingérer le fichier
            result = await self.pipeline.ingest_file(
                file_path=str(file_path),
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            logger.info(f"Fichier ingéré: {result['chunks_count']} chunks créés")
            return result
            
        except Exception as e:
            logger.error(f"Erreur ingestion fichier {file_path}: {e}")
            raise
    
    async def ingest_text(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Dict[str, Any]:
        """Ingère du texte brut dans le vector store"""
        try:
            logger.info("Ingestion de texte brut")
            
            # Métadonnées par défaut
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "content_type": "text",
                "content_length": len(content),
                "ingestion_method": "cli"
            })
            
            # Ingérer le texte
            result = await self.pipeline.ingest_text(
                content=content,
                metadata=metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            logger.info(f"Texte ingéré: {result['chunks_count']} chunks créés")
            return result
            
        except Exception as e:
            logger.error(f"Erreur ingestion texte: {e}")
            raise
    
    async def ingest_directory(
        self,
        directory_path: str,
        recursive: bool = False,
        file_patterns: List[str] = None,
        metadata: Dict[str, Any] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Dict[str, Any]:
        """Ingère tous les fichiers d'un répertoire"""
        try:
            directory = Path(directory_path)
            
            if not directory.exists() or not directory.is_dir():
                raise ValueError(f"Répertoire non trouvé: {directory}")
            
            logger.info(f"Ingestion du répertoire: {directory}")
            
            # Patterns de fichiers par défaut
            if file_patterns is None:
                file_patterns = ["*.txt", "*.pdf", "*.docx", "*.md"]
            
            # Trouver les fichiers à ingérer
            files_to_ingest = []
            
            for pattern in file_patterns:
                if recursive:
                    files_to_ingest.extend(directory.rglob(pattern))
                else:
                    files_to_ingest.extend(directory.glob(pattern))
            
            if not files_to_ingest:
                logger.warning(f"Aucun fichier trouvé dans {directory} avec les patterns {file_patterns}")
                return {"ingested_files": 0, "total_chunks": 0}
            
            logger.info(f"Fichiers trouvés: {len(files_to_ingest)}")
            
            # Ingérer chaque fichier
            results = {
                "ingested_files": 0,
                "total_chunks": 0,
                "files": []
            }
            
            for file_path in files_to_ingest:
                try:
                    # Métadonnées spécifiques au fichier
                    file_metadata = metadata.copy() if metadata else {}
                    file_metadata.update({
                        "batch_ingestion": True,
                        "source_directory": str(directory)
                    })
                    
                    # Ingérer le fichier
                    result = await self.ingest_file(
                        file_path=str(file_path),
                        metadata=file_metadata,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
                    
                    results["ingested_files"] += 1
                    results["total_chunks"] += result["chunks_count"]
                    results["files"].append({
                        "file": str(file_path),
                        "chunks": result["chunks_count"]
                    })
                    
                except Exception as e:
                    logger.error(f"Erreur ingestion {file_path}: {e}")
                    continue
            
            logger.info(f"Ingestion terminée: {results['ingested_files']} fichiers, {results['total_chunks']} chunks")
            return results
            
        except Exception as e:
            logger.error(f"Erreur ingestion répertoire {directory_path}: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques du vector store"""
        try:
            if not self.vector_store:
                raise ValueError("Vector store non initialisé")
            
            stats = await self.vector_store.get_stats()
            return stats
            
        except Exception as e:
            logger.error(f"Erreur récupération stats: {e}")
            raise


async def main():
    """Fonction principale du CLI"""
    parser = argparse.ArgumentParser(
        description="Script d'ingestion de documents pour la plateforme MAR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

  # Ingérer un fichier PDF
  python scripts/ingest_documents.py --file document.pdf

  # Ingérer avec métadonnées personnalisées
  python scripts/ingest_documents.py --file document.pdf --metadata '{"author": "John Doe", "category": "research"}'

  # Ingérer du texte brut
  python scripts/ingest_documents.py --text "Contenu à ingérer directement"

  # Ingérer tous les fichiers d'un répertoire
  python scripts/ingest_documents.py --directory ./docs --recursive

  # Afficher les statistiques
  python scripts/ingest_documents.py --stats

        """
    )
    
    # Arguments d'ingestion
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", "-f", help="Chemin vers le fichier à ingérer")
    group.add_argument("--text", "-t", help="Texte brut à ingérer")
    group.add_argument("--directory", "-d", help="Répertoire à ingérer")
    group.add_argument("--stats", "-s", action="store_true", help="Afficher les statistiques")
    
    # Arguments de configuration
    parser.add_argument("--metadata", "-m", default="{}", help="Métadonnées JSON à ajouter")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Taille des chunks (défaut: 1000)")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chevauchement des chunks (défaut: 200)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Ingestion récursive (pour --directory)")
    parser.add_argument("--patterns", nargs="*", default=["*.txt", "*.pdf", "*.docx", "*.md"], 
                       help="Patterns de fichiers (défaut: *.txt *.pdf *.docx *.md)")
    
    # Arguments du vector store
    parser.add_argument("--store-type", choices=["faiss", "chroma"], default="faiss", 
                       help="Type de vector store (défaut: faiss)")
    parser.add_argument("--store-path", default="./data/vector_store", 
                       help="Chemin de stockage (défaut: ./data/vector_store)")
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2",
                       help="Modèle d'embedding (défaut: sentence-transformers/all-MiniLM-L6-v2)")
    
    # Arguments de logging
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")
    parser.add_argument("--quiet", "-q", action="store_true", help="Mode silencieux")
    
    args = parser.parse_args()
    
    # Configuration du logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # Parser les métadonnées
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError as e:
            logger.error(f"Métadonnées JSON invalides: {e}")
            sys.exit(1)
        
        # Initialiser le CLI
        cli = DocumentIngestionCLI()
        
        store_config = {
            "persist_directory": args.store_path,
            "embedding_model": args.embedding_model
        }
        
        await cli.initialize(args.store_type, store_config)
        
        # Exécuter l'action demandée
        if args.stats:
            stats = await cli.get_stats()
            print("\n=== Statistiques du Vector Store ===")
            print(f"Nombre de documents: {stats.get('total_documents', 0)}")
            print(f"Nombre de chunks: {stats.get('total_chunks', 0)}")
            print(f"Dimension des vecteurs: {stats.get('vector_dimension', 0)}")
            print(f"Taille de l'index: {stats.get('index_size_mb', 0):.2f} MB")
            
        elif args.file:
            result = await cli.ingest_file(
                file_path=args.file,
                metadata=metadata,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap
            )
            print(f"\n✅ Fichier ingéré avec succès!")
            print(f"Chunks créés: {result['chunks_count']}")
            
        elif args.text:
            result = await cli.ingest_text(
                content=args.text,
                metadata=metadata,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap
            )
            print(f"\n✅ Texte ingéré avec succès!")
            print(f"Chunks créés: {result['chunks_count']}")
            
        elif args.directory:
            result = await cli.ingest_directory(
                directory_path=args.directory,
                recursive=args.recursive,
                file_patterns=args.patterns,
                metadata=metadata,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap
            )
            print(f"\n✅ Répertoire ingéré avec succès!")
            print(f"Fichiers traités: {result['ingested_files']}")
            print(f"Chunks créés: {result['total_chunks']}")
            
            if args.verbose and result.get('files'):
                print("\nDétail par fichier:")
                for file_info in result['files']:
                    print(f"  {file_info['file']}: {file_info['chunks']} chunks")
        
        print("\n🎉 Ingestion terminée avec succès!")
        
    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
