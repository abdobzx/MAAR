# Multi-stage build pour optimiser la taille de l'image
FROM python:3.11-slim as builder

# Variables d'environnement pour optimiser Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système pour la compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    postgresql-client \
    gcc \
    libc6-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt pyproject.toml ./

# Installer les dépendances Python dans un virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Mettre à jour pip et installer les dépendances
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage de production
FROM python:3.11-slim as production

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PATH="/opt/venv/bin:$PATH"

# Installer uniquement les dépendances runtime nécessaires
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copier le virtualenv depuis le stage builder
COPY --from=builder /opt/venv /opt/venv

# Créer les répertoires nécessaires
RUN mkdir -p /app/logs /app/data /app/uploads && \
    chown -R appuser:appuser /app

# Définir le répertoire de travail
WORKDIR /app

# Copier le code source
COPY --chown=appuser:appuser . .

# Créer un script d'entrée
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'set -e' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Attendre que PostgreSQL soit prêt' >> /app/entrypoint.sh && \
    echo 'until pg_isready -h ${DB_HOST:-localhost} -p ${DB_PORT:-5432} -U ${DB_USER:-postgres}; do' >> /app/entrypoint.sh && \
    echo '  echo "Waiting for PostgreSQL..."' >> /app/entrypoint.sh && \
    echo '  sleep 2' >> /app/entrypoint.sh && \
    echo 'done' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Exécuter les migrations si nécessaire' >> /app/entrypoint.sh && \
    echo 'if [ "${AUTO_MIGRATE:-false}" = "true" ]; then' >> /app/entrypoint.sh && \
    echo '  echo "Running database migrations..."' >> /app/entrypoint.sh && \
    echo '  python -c "' >> /app/entrypoint.sh && \
    echo 'import asyncio' >> /app/entrypoint.sh && \
    echo 'from database.manager import DatabaseManager' >> /app/entrypoint.sh && \
    echo 'async def migrate():' >> /app/entrypoint.sh && \
    echo '    db = DatabaseManager()' >> /app/entrypoint.sh && \
    echo '    await db.initialize()' >> /app/entrypoint.sh && \
    echo '    await db.close()' >> /app/entrypoint.sh && \
    echo 'asyncio.run(migrate())' >> /app/entrypoint.sh && \
    echo '"' >> /app/entrypoint.sh && \
    echo 'fi' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo '# Démarrer l'\''application' >> /app/entrypoint.sh && \
    echo 'exec "$@"' >> /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh && \
    chown appuser:appuser /app/entrypoint.sh

# Changer vers l'utilisateur non-root
USER appuser

# Exposer le port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Point d'entrée et commande par défaut
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
