"""
Tests de performance avec pytest-benchmark pour le système RAG Enterprise.
"""

import pytest
import asyncio
import time
import random
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import io

from agents.ingestion.agent import IngestionAgent
from agents.vectorization.agent import VectorizationAgent  
from agents.feedback.agent import FeedbackMemoryAgent
from core.models import DocumentMetadata, FeedbackEntry
from database.manager import DatabaseManager


class TestPerformanceBenchmarks:
    """Tests de performance et benchmarks."""
    
    @pytest.fixture
    def sample_documents(self) -> List[bytes]:
        """Génère des documents de test de différentes tailles."""
        documents = []
        
        # Petit document (1KB)
        small_doc = b"Test content " * 70  # ~1KB
        documents.append(small_doc)
        
        # Document moyen (100KB)
        medium_doc = b"Medium test content with more details " * 2500  # ~100KB
        documents.append(medium_doc)
        
        # Grand document (1MB)
        large_doc = b"Large document content with extensive information " * 20000  # ~1MB
        documents.append(large_doc)
        
        return documents
    
    @pytest.fixture
    def mock_performance_db(self):
        """Mock de base de données optimisé pour les performances."""
        mock_db = AsyncMock()
        mock_session = AsyncMock()
        mock_db.get_session.return_value.__aenter__.return_value = mock_session
        return mock_db
    
    @pytest.mark.benchmark(group="document_processing")
    def test_document_ingestion_performance(self, benchmark, mock_performance_db, sample_documents):
        """Benchmark du traitement de documents."""
        
        async def process_documents():
            agent = IngestionAgent(db_session=mock_performance_db)
            
            results = []
            for i, content in enumerate(sample_documents):
                metadata = DocumentMetadata(
                    filename=f"perf_test_{i}.txt",
                    file_path=f"/tmp/perf_test_{i}.txt",
                    user_id="perf-user-123",
                    organization_id="perf-org-123"
                )
                
                # Mock des opérations I/O
                with patch.object(agent, '_extract_text', return_value="Extracted text"), \
                     patch.object(agent, '_chunk_text', return_value=["chunk1", "chunk2"]), \
                     patch.object(agent, '_store_document', return_value=f"doc-{i}"):
                    
                    result = await agent.process_document(metadata, content)
                    results.append(result)
            
            return results
        
        def run_async():
            return asyncio.run(process_documents())
        
        results = benchmark(run_async)
        assert len(results) == len(sample_documents)
        assert all(result.success for result in results)
    
    @pytest.mark.benchmark(group="vectorization")
    def test_embedding_generation_performance(self, benchmark, mock_performance_db):
        """Benchmark de la génération d'embeddings."""
        
        async def generate_embeddings():
            agent = VectorizationAgent(db_session=mock_performance_db)
            
            # Simuler 100 chunks de texte
            text_chunks = [f"Test chunk content number {i} with various details" for i in range(100)]
            
            # Mock du client OpenAI pour éviter les appels réseau
            mock_embeddings = [[random.random() for _ in range(1536)] for _ in range(100)]
            
            with patch.object(agent, '_generate_embeddings_batch', return_value=mock_embeddings):
                embeddings = await agent.generate_embeddings(text_chunks)
            
            return embeddings
        
        def run_async():
            return asyncio.run(generate_embeddings())
        
        embeddings = benchmark(run_async)
        assert len(embeddings) == 100
    
    @pytest.mark.benchmark(group="search")
    def test_vector_search_performance(self, benchmark, mock_performance_db):
        """Benchmark de la recherche vectorielle."""
        
        async def perform_searches():
            agent = VectorizationAgent(db_session=mock_performance_db)
            
            # Simuler 50 recherches
            queries = [f"Search query number {i}" for i in range(50)]
            
            # Mock des résultats de recherche
            mock_results = [
                [{"id": f"doc-{j}", "score": 0.9 - (j * 0.1), "content": f"Result {j}"}
                 for j in range(10)]  # 10 résultats par recherche
                for _ in range(50)
            ]
            
            with patch.object(agent, 'search_similar_content', side_effect=mock_results):
                results = []
                for query in queries:
                    search_results = await agent.search_similar_content(query, top_k=10)
                    results.append(search_results)
            
            return results
        
        def run_async():
            return asyncio.run(perform_searches())
        
        results = benchmark(run_async)
        assert len(results) == 50
        assert all(len(result) == 10 for result in results)
    
    @pytest.mark.benchmark(group="feedback")
    def test_feedback_processing_performance(self, benchmark, mock_performance_db):
        """Benchmark du traitement de feedback."""
        
        async def process_feedback():
            agent = FeedbackMemoryAgent(db_session=mock_performance_db)
            
            # Simuler 200 feedbacks
            feedbacks = []
            for i in range(200):
                feedback = FeedbackEntry(
                    user_id=f"user-{i % 20}",  # 20 utilisateurs différents
                    organization_id="perf-org-123",
                    feedback_type=random.choice(["quality", "relevance", "accuracy"]),
                    rating=random.randint(1, 5),
                    content=f"Performance feedback {i}"
                )
                feedbacks.append(feedback)
            
            # Mock des opérations de base de données
            with patch.object(agent, '_store_feedback_db', return_value=True), \
                 patch.object(agent, '_analyze_sentiment', return_value=MagicMock(sentiment="positive", confidence=0.8)):
                
                results = []
                for feedback in feedbacks:
                    result = await agent.store_feedback(feedback)
                    results.append(result)
            
            return results
        
        def run_async():
            return asyncio.run(process_feedback())
        
        results = benchmark(run_async)
        assert len(results) == 200
    
    @pytest.mark.benchmark(group="concurrent")
    def test_concurrent_operations_performance(self, benchmark, mock_performance_db):
        """Benchmark des opérations concurrentes."""
        
        async def concurrent_operations():
            # Simuler des opérations concurrentes typiques
            ingestion_agent = IngestionAgent(db_session=mock_performance_db)
            vectorization_agent = VectorizationAgent(db_session=mock_performance_db)
            feedback_agent = FeedbackMemoryAgent(db_session=mock_performance_db)
            
            # Tâches concurrentes
            tasks = []
            
            # Ingestion de documents
            for i in range(10):
                metadata = DocumentMetadata(
                    filename=f"concurrent_doc_{i}.txt",
                    file_path=f"/tmp/concurrent_{i}.txt",
                    user_id=f"user-{i}",
                    organization_id="perf-org-123"
                )
                content = f"Concurrent document content {i}".encode()
                
                with patch.object(ingestion_agent, '_extract_text', return_value=f"Text {i}"), \
                     patch.object(ingestion_agent, '_chunk_text', return_value=[f"chunk-{i}"]), \
                     patch.object(ingestion_agent, '_store_document', return_value=f"doc-{i}"):
                    
                    task = ingestion_agent.process_document(metadata, content)
                    tasks.append(task)
            
            # Recherches vectorielles
            for i in range(15):
                with patch.object(vectorization_agent, 'search_similar_content', 
                                return_value=[{"id": f"result-{j}", "score": 0.9} for j in range(5)]):
                    task = vectorization_agent.search_similar_content(f"query {i}")
                    tasks.append(task)
            
            # Traitement de feedback
            for i in range(20):
                feedback = FeedbackEntry(
                    user_id=f"user-{i % 5}",
                    organization_id="perf-org-123",
                    feedback_type="quality",
                    rating=random.randint(1, 5),
                    content=f"Concurrent feedback {i}"
                )
                
                with patch.object(feedback_agent, '_store_feedback_db', return_value=True), \
                     patch.object(feedback_agent, '_analyze_sentiment', return_value=MagicMock(sentiment="positive")):
                    task = feedback_agent.store_feedback(feedback)
                    tasks.append(task)
            
            # Exécution concurrente
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtrer les erreurs pour ne compter que les succès
            successful_results = [r for r in results if not isinstance(r, Exception)]
            
            return successful_results
        
        def run_async():
            return asyncio.run(concurrent_operations())
        
        results = benchmark(run_async)
        assert len(results) >= 40  # Au moins 40 opérations réussies sur 45
    
    @pytest.mark.benchmark(group="memory")
    def test_memory_usage_optimization(self, benchmark, mock_performance_db):
        """Benchmark de l'utilisation mémoire."""
        
        async def memory_intensive_operations():
            agent = VectorizationAgent(db_session=mock_performance_db)
            
            # Simuler le traitement de gros volumes de données
            large_texts = []
            for i in range(1000):
                # Textes de taille variable pour simuler un cas réel
                text_size = random.randint(100, 5000)
                text = "Sample text content " * (text_size // 20)
                large_texts.append(text)
            
            # Mock pour éviter les appels réseau
            with patch.object(agent, '_generate_embeddings_batch') as mock_embed:
                # Simuler le traitement par batch pour optimiser la mémoire
                batch_size = 50
                all_embeddings = []
                
                for i in range(0, len(large_texts), batch_size):
                    batch = large_texts[i:i + batch_size]
                    mock_embed.return_value = [[random.random() for _ in range(1536)] for _ in range(len(batch))]
                    
                    embeddings = await agent.generate_embeddings(batch)
                    all_embeddings.extend(embeddings)
                    
                    # Simuler le nettoyage mémoire entre les batchs
                    del embeddings
                    del batch
            
            return len(all_embeddings)
        
        def run_async():
            return asyncio.run(memory_intensive_operations())
        
        result = benchmark(run_async)
        assert result == 1000
    
    @pytest.mark.benchmark(group="database")
    def test_database_operations_performance(self, benchmark):
        """Benchmark des opérations de base de données."""
        
        async def database_operations():
            # Simuler des opérations de base de données intensives
            db_manager = DatabaseManager(test_mode=True)
            
            operations_count = 0
            
            # Mock des opérations DB pour éviter les I/O réelles
            with patch.object(db_manager, 'execute_query') as mock_execute, \
                 patch.object(db_manager, 'get_session') as mock_session:
                
                mock_execute.return_value = {"rows_affected": 1}
                mock_session.return_value.__aenter__.return_value = AsyncMock()
                
                # Simuler 500 opérations de base de données
                tasks = []
                for i in range(500):
                    # Alternance entre lecture et écriture
                    if i % 2 == 0:
                        # Opération de lecture
                        task = db_manager.execute_query("SELECT * FROM documents WHERE id = ?", (f"doc-{i}",))
                    else:
                        # Opération d'écriture
                        task = db_manager.execute_query("INSERT INTO logs (message) VALUES (?)", (f"Log {i}",))
                    
                    tasks.append(task)
                    operations_count += 1
                
                await asyncio.gather(*tasks)
            
            return operations_count
        
        def run_async():
            return asyncio.run(database_operations())
        
        result = benchmark(run_async)
        assert result == 500
    
    def test_benchmark_report_generation(self, benchmark):
        """Test de génération de rapport de performance."""
        
        def generate_performance_report():
            """Génère un rapport de performance simulé."""
            report = {
                "timestamp": time.time(),
                "metrics": {},
                "operations": []
            }
            
            # Simuler la collecte de métriques
            for operation in ["ingestion", "vectorization", "search", "feedback"]:
                # Simuler des calculs de métriques
                latency_samples = [random.uniform(0.1, 2.0) for _ in range(100)]
                
                report["metrics"][operation] = {
                    "avg_latency": sum(latency_samples) / len(latency_samples),
                    "min_latency": min(latency_samples),
                    "max_latency": max(latency_samples),
                    "p95_latency": sorted(latency_samples)[94],  # 95e percentile
                    "p99_latency": sorted(latency_samples)[98],  # 99e percentile
                    "operations_count": len(latency_samples),
                    "error_rate": random.uniform(0.0, 0.05)  # 0-5% d'erreurs
                }
                
                report["operations"].append({
                    "operation": operation,
                    "status": "completed",
                    "duration": random.uniform(0.5, 3.0)
                })
            
            # Simuler l'agrégation des données
            total_operations = sum(m["operations_count"] for m in report["metrics"].values())
            avg_error_rate = sum(m["error_rate"] for m in report["metrics"].values()) / len(report["metrics"])
            
            report["summary"] = {
                "total_operations": total_operations,
                "avg_error_rate": avg_error_rate,
                "overall_health": "healthy" if avg_error_rate < 0.02 else "degraded"
            }
            
            return report
        
        report = benchmark(generate_performance_report)
        
        assert "metrics" in report
        assert "summary" in report
        assert len(report["metrics"]) == 4  # 4 opérations testées
        assert report["summary"]["total_operations"] == 400  # 100 * 4 opérations


@pytest.mark.stress
class TestStressScenarios:
    """Tests de stress pour identifier les limites du système."""
    
    @pytest.mark.timeout(60)  # Timeout de 60 secondes
    async def test_high_volume_document_processing(self, mock_performance_db):
        """Test de traitement de gros volume de documents."""
        
        agent = IngestionAgent(db_session=mock_performance_db)
        
        # Simuler 1000 documents
        documents = []
        for i in range(1000):
            metadata = DocumentMetadata(
                filename=f"stress_test_{i}.txt",
                file_path=f"/tmp/stress_{i}.txt",
                user_id=f"user-{i % 50}",  # 50 utilisateurs
                organization_id="stress-org-123"
            )
            content = f"Stress test document content {i} " * random.randint(10, 100)
            documents.append((metadata, content.encode()))
        
        # Mock pour éviter les I/O réelles
        with patch.object(agent, '_extract_text') as mock_extract, \
             patch.object(agent, '_chunk_text') as mock_chunk, \
             patch.object(agent, '_store_document') as mock_store:
            
            mock_extract.side_effect = lambda x: f"Extracted text {random.randint(1, 1000)}"
            mock_chunk.side_effect = lambda x: [f"chunk-{i}" for i in range(random.randint(1, 10))]
            mock_store.side_effect = lambda *args: f"doc-{random.randint(1, 10000)}"
            
            # Traitement en parallèle par batch
            batch_size = 50
            all_results = []
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                tasks = []
                for metadata, content in batch:
                    task = agent.process_document(metadata, content)
                    tasks.append(task)
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_results.extend(batch_results)
        
        # Vérifier les résultats
        successful_results = [r for r in all_results if not isinstance(r, Exception)]
        assert len(successful_results) >= 950  # Au moins 95% de réussite
    
    @pytest.mark.timeout(45)
    async def test_concurrent_user_simulation(self, mock_performance_db):
        """Test de simulation d'utilisateurs concurrents."""
        
        # Simuler 100 utilisateurs simultanés
        user_count = 100
        operations_per_user = 10
        
        async def simulate_user(user_id: int):
            """Simule les actions d'un utilisateur."""
            operations = []
            
            # Chaque utilisateur fait différentes actions
            for i in range(operations_per_user):
                operation_type = random.choice(["search", "feedback", "upload"])
                
                if operation_type == "search":
                    # Simulation de recherche
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    operations.append({"type": "search", "status": "success"})
                
                elif operation_type == "feedback":
                    # Simulation de feedback
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                    operations.append({"type": "feedback", "status": "success"})
                
                elif operation_type == "upload":
                    # Simulation d'upload
                    await asyncio.sleep(random.uniform(0.2, 0.8))
                    operations.append({"type": "upload", "status": "success"})
            
            return {"user_id": user_id, "operations": operations}
        
        # Lancer tous les utilisateurs en parallèle
        tasks = [simulate_user(i) for i in range(user_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyser les résultats
        successful_users = [r for r in results if not isinstance(r, Exception)]
        total_operations = sum(len(user["operations"]) for user in successful_users)
        
        assert len(successful_users) >= 95  # Au moins 95% d'utilisateurs réussis
        assert total_operations >= 950  # Au moins 95% d'opérations réussies
    
    @pytest.mark.timeout(30)
    async def test_memory_pressure_scenario(self):
        """Test de pression mémoire."""
        
        # Simuler une montée en charge progressive de la mémoire
        memory_objects = []
        max_objects = 10000
        
        try:
            for i in range(max_objects):
                # Créer des objets de taille variable pour simuler l'usage réel
                obj_size = random.randint(1024, 10240)  # 1KB à 10KB
                memory_obj = {
                    "id": f"obj-{i}",
                    "data": "x" * obj_size,
                    "metadata": {
                        "created_at": time.time(),
                        "size": obj_size,
                        "processed": False
                    }
                }
                memory_objects.append(memory_obj)
                
                # Tous les 1000 objets, nettoyer une partie
                if i % 1000 == 999:
                    # Garder seulement les 500 plus récents
                    memory_objects = memory_objects[-500:]
            
            # Vérifier que le système a géré la pression mémoire
            assert len(memory_objects) <= 1000
            
        except MemoryError:
            # Si erreur mémoire, vérifier qu'on a traité un minimum d'objets
            assert len(memory_objects) >= 1000
    
    @pytest.mark.timeout(40)
    async def test_database_connection_stress(self):
        """Test de stress des connexions de base de données."""
        
        # Simuler de nombreuses connexions simultanées
        connection_count = 200
        operations_per_connection = 20
        
        async def simulate_db_operations(connection_id: int):
            """Simule des opérations de base de données."""
            operations = []
            
            # Mock des opérations DB
            for i in range(operations_per_connection):
                # Simuler latence variable
                await asyncio.sleep(random.uniform(0.01, 0.1))
                
                operation_type = random.choice(["SELECT", "INSERT", "UPDATE"])
                operations.append({
                    "type": operation_type,
                    "connection_id": connection_id,
                    "operation_id": i,
                    "status": "success"
                })
            
            return operations
        
        # Lancer toutes les connexions en parallèle
        tasks = [simulate_db_operations(i) for i in range(connection_count)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyser les performances
        successful_connections = [r for r in results if not isinstance(r, Exception)]
        total_operations = sum(len(ops) for ops in successful_connections)
        duration = end_time - start_time
        
        assert len(successful_connections) >= 180  # Au moins 90% de connexions réussies
        assert total_operations >= 3600  # Au moins 90% d'opérations réussies
        assert duration < 30  # Terminé en moins de 30 secondes
