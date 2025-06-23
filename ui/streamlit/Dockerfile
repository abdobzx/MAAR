# Dockerfile pour l'interface Streamlit
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="MAR Platform Team"
LABEL description="Multi-Agent RAG Platform - Streamlit UI"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie et installation des dépendances
COPY ui/streamlit/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code de l'interface
COPY ui/streamlit/ ./ui/streamlit/

# Création d'un utilisateur non-root
RUN adduser --disabled-password --gecos '' --uid 1000 streamlituser && \
    chown -R streamlituser:streamlituser /app
USER streamlituser

# Exposition du port Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Commande de démarrage
CMD ["streamlit", "run", "ui/streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
