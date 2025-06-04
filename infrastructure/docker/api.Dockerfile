# Dockerfile optimisé pour l'API FastAPI
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installer uniquement les dépendances API
COPY requirements.api.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.api.txt

WORKDIR /app
COPY api/ ./api/
COPY core/ ./core/
COPY database/ ./database/

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
