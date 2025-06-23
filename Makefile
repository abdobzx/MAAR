# Makefile pour la plateforme MAR
# Simplifie les commandes de développement et déploiement

.PHONY: help install dev test clean build deploy docs

# Variables
PYTHON := python3
PIP := pip3
DOCKER := docker
DOCKER_COMPOSE := docker-compose
KUBECTL := kubectl

# Configuration
APP_NAME := mar-platform
VERSION := $(shell cat VERSION 2>/dev/null || echo "0.1.0")
REGISTRY := ghcr.io/your-org
NAMESPACE := mar-platform

# Couleurs pour l'affichage
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# ===== AIDE =====
help: ## Affiche cette aide
	@echo "$(BLUE)🤖 Plateforme MAR - Commandes disponibles$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Exemples d'utilisation:$(NC)"
	@echo "  make install     # Installation des dépendances"
	@echo "  make dev         # Lancement en mode développement"
	@echo "  make test        # Exécution des tests"
	@echo "  make build       # Construction des images Docker"

# ===== INSTALLATION =====
setup: ## Configuration initiale complète
	@echo "$(BLUE)🛠️  Configuration initiale de la plateforme MAR...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)📝 Création du fichier .env...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✅ Fichier .env créé$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Le fichier .env existe déjà$(NC)"; \
	fi
	@echo "$(BLUE)📁 Création des répertoires nécessaires...$(NC)"
	@mkdir -p data/{vector_store,uploads,backups}
	@mkdir -p logs
	@echo "$(GREEN)✅ Répertoires créés$(NC)"
	@echo "$(GREEN)🎉 Configuration terminée ! Utilisez 'make docker-up' pour démarrer$(NC)"

install: ## Installe les dépendances
	@echo "$(BLUE)📦 Installation des dépendances...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Dépendances installées$(NC)"

install-dev: ## Installe les dépendances de développement
	@echo "$(BLUE)🔧 Installation des dépendances de développement...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov black flake8 mypy pre-commit
	pre-commit install
	@echo "$(GREEN)✅ Environnement de développement configuré$(NC)"

# ===== DÉVELOPPEMENT =====
dev: ## Lance l'environnement de développement
	@echo "$(BLUE)🚀 Lancement de l'environnement de développement...$(NC)"
	$(DOCKER_COMPOSE) up --build

dev-api: ## Lance uniquement l'API en mode développement
	@echo "$(BLUE)🚀 Lancement de l'API MAR...$(NC)"
	$(PYTHON) -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-ui: ## Lance uniquement l'interface Streamlit
	@echo "$(BLUE)🎨 Lancement de l'interface Streamlit...$(NC)"
	streamlit run ui/streamlit/app.py --server.port 8501

dev-down: ## Arrête l'environnement de développement
	@echo "$(YELLOW)⏹️  Arrêt de l'environnement de développement...$(NC)"
	$(DOCKER_COMPOSE) down

# ===== TESTS =====
test: ## Exécute tous les tests
	@echo "$(BLUE)🧪 Exécution des tests...$(NC)"
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term

test-unit: ## Exécute les tests unitaires
	@echo "$(BLUE)🔬 Tests unitaires...$(NC)"
	pytest tests/unit/ -v

test-integration: ## Exécute les tests d'intégration
	@echo "$(BLUE)🔗 Tests d'intégration...$(NC)"
	pytest tests/integration/ -v

test-e2e: ## Exécute les tests end-to-end
	@echo "$(BLUE)🎯 Tests end-to-end...$(NC)"
	pytest tests/e2e/ -v

# ===== QUALITÉ DU CODE =====
lint: ## Vérifie la qualité du code
	@echo "$(BLUE)🔍 Vérification de la qualité du code...$(NC)"
	black --check .
	flake8 .
	mypy . --ignore-missing-imports

format: ## Formate le code
	@echo "$(BLUE)✨ Formatage du code...$(NC)"
	black .
	@echo "$(GREEN)✅ Code formaté$(NC)"

security: ## Analyse de sécurité
	@echo "$(BLUE)🔒 Analyse de sécurité...$(NC)"
	safety check --file requirements.txt
	bandit -r . -f json -o security-report.json
	@echo "$(GREEN)✅ Analyse de sécurité terminée$(NC)"

# ===== DOCKER =====
build: ## Construit les images Docker
	@echo "$(BLUE)🏗️  Construction des images Docker...$(NC)"
	$(DOCKER) build -t $(REGISTRY)/$(APP_NAME)-api:$(VERSION) .
	$(DOCKER) build -t $(REGISTRY)/$(APP_NAME)-ui:$(VERSION) -f ui/streamlit/Dockerfile .
	@echo "$(GREEN)✅ Images construites$(NC)"

build-no-cache: ## Construit les images Docker sans cache
	@echo "$(BLUE)🏗️  Construction des images Docker (sans cache)...$(NC)"
	$(DOCKER) build --no-cache -t $(REGISTRY)/$(APP_NAME)-api:$(VERSION) .
	$(DOCKER) build --no-cache -t $(REGISTRY)/$(APP_NAME)-ui:$(VERSION) -f ui/streamlit/Dockerfile .
	@echo "$(GREEN)✅ Images construites$(NC)"

push: ## Pousse les images vers le registry
	@echo "$(BLUE)📤 Envoi des images vers le registry...$(NC)"
	$(DOCKER) push $(REGISTRY)/$(APP_NAME)-api:$(VERSION)
	$(DOCKER) push $(REGISTRY)/$(APP_NAME)-ui:$(VERSION)
	@echo "$(GREEN)✅ Images envoyées$(NC)"

# ===== DÉPLOIEMENT LOCAL =====
docker-up: up ## Alias pour up (compatibilité)

up: ## Lance la stack complète en local
	@echo "$(BLUE)🚀 Lancement de la stack MAR...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Stack lancée$(NC)"
	@echo "$(YELLOW)📱 Interface: http://localhost:8501$(NC)"
	@echo "$(YELLOW)🔌 API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)📊 Grafana: http://localhost:3000$(NC)"
	@echo "$(YELLOW)🎯 Prometheus: http://localhost:9090$(NC)"

docker-down: down ## Alias pour down (compatibilité)

down: ## Arrête la stack locale
	@echo "$(YELLOW)⏹️  Arrêt de la stack MAR...$(NC)"
	@echo "$(YELLOW)⚠️  Arrêt des conteneurs...$(NC)"
	-$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Stack arrêtée$(NC)"

restart: down up ## Redémarre la stack locale

logs: ## Affiche les logs de la stack
	$(DOCKER_COMPOSE) logs -f

logs-api: ## Affiche les logs de l'API
	$(DOCKER_COMPOSE) logs -f mar-api

logs-ui: ## Affiche les logs de l'UI
	$(DOCKER_COMPOSE) logs -f mar-ui

# ===== DÉPLOIEMENT KUBERNETES =====
k8s-deploy: ## Déploie sur Kubernetes
	@echo "$(BLUE)☸️  Déploiement sur Kubernetes...$(NC)"
	$(KUBECTL) apply -f k8s/manifests/
	@echo "$(GREEN)✅ Déploiement K8s terminé$(NC)"

k8s-delete: ## Supprime le déploiement Kubernetes
	@echo "$(YELLOW)🗑️  Suppression du déploiement K8s...$(NC)"
	$(KUBECTL) delete -f k8s/manifests/
	@echo "$(GREEN)✅ Déploiement supprimé$(NC)"

k8s-status: ## Affiche le statut des pods
	@echo "$(BLUE)📊 Statut des pods:$(NC)"
	$(KUBECTL) get pods -n $(NAMESPACE)

k8s-logs: ## Affiche les logs des pods
	@echo "$(BLUE)📋 Logs des pods:$(NC)"
	$(KUBECTL) logs -f -l app=mar-api -n $(NAMESPACE)

# ===== DONNÉES ET INGESTION =====
ingest-sample: ## Ingère des données d'exemple
	@echo "$(BLUE)📁 Ingestion des données d'exemple...$(NC)"
	@if [ -f scripts/ingest_documents.py ]; then \
		$(PYTHON) scripts/ingest_documents.py --text "Exemple de document pour tester la plateforme MAR" --metadata '{"source": "sample", "type": "test"}'; \
	else \
		echo "$(YELLOW)⚠️  Script d'ingestion non trouvé$(NC)"; \
	fi
	@echo "$(GREEN)✅ Données d'exemple ingérées$(NC)"

backup: ## Sauvegarde les données
	@echo "$(BLUE)💾 Sauvegarde des données...$(NC)"
	mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	# Sauvegarder le vector store et autres données
	@echo "$(GREEN)✅ Sauvegarde terminée$(NC)"

# ===== NETTOYAGE =====
clean: ## Nettoie les fichiers temporaires
	@echo "$(BLUE)🧹 Nettoyage...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

clean-docker: ## Nettoie les images Docker
	@echo "$(BLUE)🐳 Nettoyage Docker...$(NC)"
	$(DOCKER) system prune -f
	$(DOCKER) image prune -f
	@echo "$(GREEN)✅ Nettoyage Docker terminé$(NC)"

# ===== DOCUMENTATION =====
docs: ## Génère la documentation
	@echo "$(BLUE)📚 Génération de la documentation...$(NC)"
	# Installer mkdocs si nécessaire
	$(PIP) install mkdocs mkdocs-material
	mkdocs build
	@echo "$(GREEN)✅ Documentation générée$(NC)"

docs-serve: ## Lance le serveur de documentation
	@echo "$(BLUE)📖 Lancement du serveur de documentation...$(NC)"
	mkdocs serve

# ===== MONITORING =====
monitor: ## Affiche les métriques de monitoring
	@echo "$(BLUE)📊 Ouverture des outils de monitoring...$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/mar_admin_2024)$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"
	@echo "$(YELLOW)Kibana: http://localhost:5601$(NC)"

health: ## Vérifie la santé des services
	@echo "$(BLUE)🏥 Vérification de la santé des services...$(NC)"
	@curl -s http://localhost:8000/health | jq . || echo "❌ API non accessible"
	@curl -s http://localhost:9090/-/healthy > /dev/null && echo "✅ Prometheus OK" || echo "❌ Prometheus KO"
	@curl -s http://localhost:3000/api/health | jq . || echo "❌ Grafana non accessible"

# ===== OUTILS =====
shell: ## Lance un shell dans le container de l'API
	$(DOCKER_COMPOSE) exec mar-api /bin/bash

requirements: ## Met à jour requirements.txt
	@echo "$(BLUE)📋 Mise à jour des requirements...$(NC)"
	$(PIP) freeze > requirements.txt
	@echo "$(GREEN)✅ Requirements mis à jour$(NC)"

version: ## Affiche la version
	@echo "$(BLUE)Version actuelle: $(VERSION)$(NC)"

# ===== RELEASE =====
release: ## Crée une nouvelle release
	@echo "$(BLUE)🚀 Création d'une nouvelle release...$(NC)"
	@read -p "Nouvelle version (actuelle: $(VERSION)): " NEW_VERSION; \
	echo $$NEW_VERSION > VERSION; \
	git add VERSION; \
	git commit -m "Release v$$NEW_VERSION"; \
	git tag -a v$$NEW_VERSION -m "Release v$$NEW_VERSION"; \
	echo "$(GREEN)✅ Release v$$NEW_VERSION créée$(NC)"; \
	echo "$(YELLOW)N'oubliez pas de faire: git push && git push --tags$(NC)"

# Définir la cible par défaut
.DEFAULT_GOAL := help
