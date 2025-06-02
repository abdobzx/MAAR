"""
Tests de charge avec Locust pour le système RAG Enterprise.
"""

import random
import time
import json
import io
from locust import HttpUser, task, between
from faker import Faker

fake = Faker('fr_FR')


class RAGSystemUser(HttpUser):
    """Utilisateur simulé pour les tests de charge."""
    
    wait_time = between(1, 3)  # Attente entre les requêtes
    
    def on_start(self):
        """Initialisation de l'utilisateur."""
        self.auth_token = self._authenticate()
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        self.document_ids = []
    
    def _authenticate(self) -> str:
        """Authentification de l'utilisateur."""
        auth_data = {
            "username": fake.user_name(),
            "password": "test_password_123",
            "organization_id": "load-test-org"
        }
        
        with self.client.post("/api/v1/auth/login", json=auth_data, catch_response=True) as response:
            if response.status_code == 200:
                return response.json().get("access_token", "test-token")
            else:
                response.failure(f"Échec d'authentification: {response.status_code}")
                return "test-token"
    
    @task(10)
    def health_check(self):
        """Test du endpoint de santé - fréquent."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def upload_document(self):
        """Test d'upload de documents."""
        # Générer un contenu de document simulé
        document_content = fake.text(max_nb_chars=2000)
        filename = f"test_document_{random.randint(1000, 9999)}.txt"
        
        files = {
            'file': (filename, io.StringIO(document_content), 'text/plain')
        }
        
        data = {
            'metadata': json.dumps({
                'title': fake.sentence(),
                'description': fake.text(max_nb_chars=200),
                'category': random.choice(['policy', 'procedure', 'faq', 'manual'])
            })
        }
        
        with self.client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {self.auth_token}"},
            catch_response=True
        ) as response:
            if response.status_code == 201:
                result = response.json()
                document_id = result.get("document_id")
                if document_id:
                    self.document_ids.append(document_id)
                response.success()
            else:
                response.failure(f"Upload failed: {response.status_code}")
    
    @task(20)
    def query_chat(self):
        """Test de requêtes chat - très fréquent."""
        queries = [
            "Quelle est la politique de télétravail?",
            "Comment faire une demande de congés?",
            "Quels sont les avantages sociaux?",
            "Comment contacter le support technique?",
            "Où trouver les procédures RH?",
            "Quelles sont les heures d'ouverture?",
            "Comment accéder au VPN?",
            "Politique de sécurité informatique",
            "Procédure d'urgence",
            "Formation obligatoire"
        ]
        
        query_data = {
            "query": random.choice(queries),
            "context": {
                "session_id": f"load-test-{random.randint(1000, 9999)}",
                "timestamp": time.time()
            },
            "preferences": {
                "response_length": random.choice(["concise", "detailed"]),
                "language": "fr"
            }
        }
        
        with self.client.post(
            "/api/v1/chat/query",
            json=query_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("success") and result.get("response"):
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Query failed: {response.status_code}")
    
    @task(8)
    def search_documents(self):
        """Test de recherche de documents."""
        search_terms = [
            "politique",
            "procédure",
            "congés",
            "télétravail",
            "sécurité",
            "formation",
            "support",
            "RH",
            "informatique",
            "urgence"
        ]
        
        search_data = {
            "query": random.choice(search_terms),
            "filters": {
                "category": random.choice(["policy", "procedure", "faq", None]),
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                }
            },
            "limit": random.randint(5, 20)
        }
        
        with self.client.post(
            "/api/v1/search",
            json=search_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("success") and "results" in result:
                    response.success()
                else:
                    response.failure("Invalid search response")
            else:
                response.failure(f"Search failed: {response.status_code}")
    
    @task(3)
    def submit_feedback(self):
        """Test de soumission de feedback."""
        feedback_types = ["quality", "relevance", "accuracy", "helpfulness"]
        
        feedback_data = {
            "feedback_type": random.choice(feedback_types),
            "rating": random.randint(1, 5),
            "content": fake.text(max_nb_chars=300),
            "context": {
                "query": fake.sentence(),
                "response_id": f"resp-{random.randint(1000, 9999)}",
                "session_id": f"session-{random.randint(1000, 9999)}"
            }
        }
        
        with self.client.post(
            "/api/v1/feedback",
            json=feedback_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Feedback failed: {response.status_code}")
    
    @task(2)
    def get_analytics(self):
        """Test de récupération d'analytics."""
        with self.client.get(
            "/api/v1/analytics/summary",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("success") and "analytics" in result:
                    response.success()
                else:
                    response.failure("Invalid analytics response")
            else:
                response.failure(f"Analytics failed: {response.status_code}")
    
    @task(1)
    def streaming_chat(self):
        """Test de chat en streaming."""
        query_data = {
            "query": fake.question(),
            "stream": True,
            "context": {
                "session_id": f"stream-{random.randint(1000, 9999)}"
            }
        }
        
        with self.client.post(
            "/api/v1/chat/stream",
            json=query_data,
            headers=self.headers,
            catch_response=True,
            stream=True
        ) as response:
            if response.status_code == 200:
                # Simuler la lecture du stream
                chunk_count = 0
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        chunk_count += 1
                        if chunk_count > 10:  # Limiter pour éviter les timeouts
                            break
                
                if chunk_count > 0:
                    response.success()
                else:
                    response.failure("No streaming data received")
            else:
                response.failure(f"Streaming failed: {response.status_code}")


class AdminUser(HttpUser):
    """Utilisateur administrateur pour les tests de charge."""
    
    wait_time = between(3, 8)  # Plus d'attente pour les opérations admin
    weight = 1  # Moins d'utilisateurs admin
    
    def on_start(self):
        """Initialisation de l'utilisateur admin."""
        self.auth_token = self._authenticate_admin()
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    def _authenticate_admin(self) -> str:
        """Authentification admin."""
        auth_data = {
            "username": "admin_load_test",
            "password": "admin_password_123",
            "organization_id": "load-test-org",
            "role": "admin"
        }
        
        with self.client.post("/api/v1/auth/login", json=auth_data, catch_response=True) as response:
            if response.status_code == 200:
                return response.json().get("access_token", "admin-token")
            else:
                return "admin-token"
    
    @task(5)
    def get_system_metrics(self):
        """Test de récupération des métriques système."""
        with self.client.get(
            "/api/v1/admin/metrics",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")
    
    @task(3)
    def manage_users(self):
        """Test de gestion des utilisateurs."""
        # Simuler la création d'un utilisateur
        user_data = {
            "email": fake.email(),
            "username": fake.user_name(),
            "role": random.choice(["user", "moderator"]),
            "organization_id": "load-test-org"
        }
        
        with self.client.post(
            "/api/v1/admin/users",
            json=user_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [201, 409]:  # 409 = utilisateur déjà existant
                response.success()
            else:
                response.failure(f"User management failed: {response.status_code}")
    
    @task(2)
    def batch_operations(self):
        """Test d'opérations en lot."""
        operation_data = {
            "operation": "reindex_documents",
            "filters": {
                "organization_id": "load-test-org",
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                }
            }
        }
        
        with self.client.post(
            "/api/v1/admin/batch",
            json=operation_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 202:  # Opération acceptée
                response.success()
            else:
                response.failure(f"Batch operation failed: {response.status_code}")


class HighVolumeUser(HttpUser):
    """Utilisateur haute fréquence pour tests de stress."""
    
    wait_time = between(0.1, 0.5)  # Très rapide
    weight = 2  # Plus d'utilisateurs haute fréquence
    
    def on_start(self):
        """Initialisation rapide."""
        self.auth_token = "high-volume-token"
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    @task(30)
    def rapid_queries(self):
        """Requêtes rapides et fréquentes."""
        quick_queries = [
            "FAQ",
            "Contact",
            "Support",
            "Aide",
            "Info",
            "Horaires",
            "Accès",
            "Login",
            "Mot de passe",
            "Reset"
        ]
        
        query_data = {
            "query": random.choice(quick_queries),
            "quick_mode": True
        }
        
        with self.client.post(
            "/api/v1/chat/quick",
            json=query_data,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Quick query failed: {response.status_code}")
    
    @task(10)
    def cache_test(self):
        """Test des performances de cache."""
        cache_key = random.choice([
            "popular_query_1",
            "popular_query_2", 
            "popular_query_3",
            "popular_query_4",
            "popular_query_5"
        ])
        
        with self.client.get(
            f"/api/v1/cache/{cache_key}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:  # 404 = pas en cache
                response.success()
            else:
                response.failure(f"Cache test failed: {response.status_code}")
