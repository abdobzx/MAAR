# Dockerfile pour les services de base (scheduler, monitoring)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installer uniquement les dépendances essentielles
COPY requirements.base.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.base.txt

WORKDIR /app
COPY core/ ./core/
COPY database/ ./database/
COPY tasks/ ./tasks/

# Commande par défaut pour Celery Beat
CMD ["celery", "-A", "core.celery", "beat", "--loglevel=info"]
