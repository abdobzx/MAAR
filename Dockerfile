# Dockerfile principal pour l'API MAR
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="MAR Platform Team"
LABEL description="Multi-Agent RAG Platform - FastAPI Service"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création des répertoires nécessaires
RUN mkdir -p /app/data/vector_store

# Création d'un utilisateur non-root pour la sécurité
RUN adduser --disabled-password --gecos '' --uid 1000 maruser && \
    chown -R maruser:maruser /app
USER maruser

# Exposition du port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Commande de démarrage
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
