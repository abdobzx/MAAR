# 🚨 COMMANDES CORRECTION IMMÉDIATE - SERVEUR UBUNTU

## PROBLÈME DÉTECTÉ
```
ERROR: Could not find a version that satisfies the requirement langchain-community==0.3.25
```

**Cause** : Version `langchain-community==0.3.25` n'existe pas (max: 0.3.24)

## ⚡ SOLUTION EXPRESS - COPIER/COLLER SUR SERVEUR

### 1. Correction immédiate du fichier requirements.fast.txt
```bash
# Sur serveur Ubuntu - dans le répertoire du projet
cd ~/AI_Deplyment_First_step/MAAR  # ou votre répertoire

# Correction directe
sed -i 's/langchain==0.3.25/langchain==0.3.24/g' requirements.fast.txt
sed -i 's/langchain-community==0.3.25/langchain-community==0.3.24/g' requirements.fast.txt

# Vérification
grep langchain requirements.fast.txt
```

### 2. Rebuild immédiat
```bash
# Nettoyage
docker-compose -f docker-compose.fast.yml down --remove-orphans
docker system prune -f

# Build corrigé
docker-compose -f docker-compose.fast.yml build --no-cache

# Déploiement
docker-compose -f docker-compose.fast.yml up -d

# Test
sleep 5 && curl http://localhost:8000/health
```

### 3. Alternative build minimal (si échec)
```bash
# Build direct minimal
docker build -t rag-api-fix -f - . << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi==0.108.0 \
    uvicorn[standard]==0.25.0 \
    "pydantic>=2.9.0,<3.0.0" \
    langchain==0.3.24 \
    langchain-community==0.3.24 \
    "langsmith>=0.1.17,<0.4.0" \
    ollama==0.5.1 \
    "httpx>=0.27.0,<0.29.0"
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Run direct
docker run -d -p 8000:8000 --name rag-api-fix rag-api-fix

# Test
curl http://localhost:8000/health
```

## ✅ VERSIONS CORRIGÉES
- ❌ `langchain==0.3.25` → ✅ `langchain==0.3.24`
- ❌ `langchain-community==0.3.25` → ✅ `langchain-community==0.3.24`
- ✅ `langsmith>=0.1.17,<0.4.0` (OK)
- ✅ `pydantic>=2.9.0,<3.0.0` (OK)

## 🎯 TEMPS ATTENDU APRÈS CORRECTION
- Build : 2-5 minutes ✅
- Deploy total : < 10 minutes ✅
