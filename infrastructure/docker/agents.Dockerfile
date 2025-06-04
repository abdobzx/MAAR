# Dockerfile optimisé pour les agents de traitement
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installer les dépendances pour le traitement des documents
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python pour le processing
COPY requirements.processing.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.processing.txt

WORKDIR /app
COPY agents/ ./agents/
COPY core/ ./core/
COPY database/ ./database/

# Peut être utilisé pour différents agents avec des commandes différentes
CMD ["celery", "-A", "core.celery", "worker", "--loglevel=info"]
