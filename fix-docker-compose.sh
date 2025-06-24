#!/bin/bash
# Script pour corriger le fichier docker-compose.yml

echo "=== Correction du fichier docker-compose.yml ==="

# 1. Créer une sauvegarde du fichier actuel
cp docker-compose.yml docker-compose.yml.backup.$(date +%s)
echo "✓ Sauvegarde créée: docker-compose.yml.backup.$(date +%s)"

# 2. Créer un nouveau fichier docker-compose.yml corrigé
cat > docker-compose.yml << 'EOL'
# Docker Compose pour la plateforme MAR
# Stack local complète avec tous les services

version: '3.8'

services:
  # API Principal MAR
  mar-api:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: mar-api
    ports:
      - "8008:8000"
    environment:
      - VECTOR_STORE_TYPE=faiss
      - VECTOR_STORE_PATH=/app/data/vector_store
      - OLLAMA_HOST=ollama:11434
      - LOG_LEVEL=INFO
      - PROMETHEUS_ENABLED=true
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - ollama
      - prometheus
      - grafana
    networks:
      - mar-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Service LLM Ollama
  ollama:
    image: ollama/ollama:latest
    container_name: mar-ollama
    ports:
      - "11435:11434"
    volumes:
      - ollama_data:/root/.ollama
      - ./models:/models
    environment:
      - OLLAMA_ORIGINS=*
      - OLLAMA_HOST=0.0.0.0
    networks:
      - mar-network
    restart: unless-stopped
    # GPU support (uncomment if available)
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  # Prometheus pour la surveillance
  prometheus:
    image: prom/prometheus:latest
    container_name: mar-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    networks:
      - mar-network
    restart: unless-stopped

  # Grafana pour les tableaux de bord
  grafana:
    image: grafana/grafana:latest
    container_name: mar-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - mar-network
    restart: unless-stopped
    depends_on:
      - prometheus

  # UI Frontend (optionnel)
  mar-ui:
    build:
      context: ./ui
      dockerfile: Dockerfile.ui
    container_name: mar-ui
    ports:
      - "3001:80"
    networks:
      - mar-network
    depends_on:
      - mar-api
    restart: unless-stopped

  # Redis pour le cache et les files d'attente
  redis:
    image: redis:alpine
    container_name: mar-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - mar-network
    restart: unless-stopped
    command: redis-server --appendonly yes

  # ElasticSearch (optionnel, pour recherche avancée)
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.6.0
    container_name: mar-elasticsearch
    environment:
      - discovery.type=single-node
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ulimits:
      memlock:
        soft: -1
        hard: -1
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - mar-network
    restart: unless-stopped

# Volumes persistants
volumes:
  ollama_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
  elasticsearch_data:
    driver: local
  redis_data:
    driver: local

# Réseau dédié
networks:
  mar-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/16
EOL

echo "✓ Fichier docker-compose.yml corrigé créé avec succès"

# 3. Correction des permissions pour le répertoire de données
echo "3. Vérification des permissions pour le répertoire de données..."

# Création du répertoire s'il n'existe pas déjà
mkdir -p data/vector_store
echo "✓ Répertoire data/vector_store créé"

# Attribution des permissions complètes
chmod -R 777 data
echo "✓ Permissions 777 attribuées au répertoire data"

echo "=== Correction terminée ==="
echo "Vous pouvez maintenant reconstruire et relancer vos conteneurs avec docker-compose:"
echo "  docker-compose down"
echo "  docker-compose up -d"
