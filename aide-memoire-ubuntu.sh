#!/bin/bash

# AIDE-MÉMOIRE RAPIDE - COMMANDES SERVEUR UBUNTU
echo "🚀 AIDE-MÉMOIRE RAPIDE - RAG ENTERPRISE MULTI-AGENT"
echo "===================================================="

echo ""
echo "📍 LOCALISATION"
echo "cd ~/AI_Deplyment_First_step/MAAR"
echo ""

echo "🧪 TESTS DE VALIDATION"
echo "====================="
echo "Test principal (RECOMMANDÉ):   ./test-pydantic-fix.sh"
echo "Test LangChain spécialisé:     ./test-langchain-fix.sh"  
echo "Test système complet:          ./validation-finale-complete.sh"
echo ""

echo "🚀 DÉPLOIEMENT"
echo "=============="
echo "Déploiement automatisé:        ./deploy-production.sh"
echo "Vérification services:         docker-compose ps"
echo "Test endpoint santé:           curl http://localhost:8000/health"
echo "Interface Swagger:             curl http://localhost:8000/docs"
echo ""

echo "🔧 DÉPANNAGE"
echo "============"
echo "Logs Docker:                   docker-compose logs"
echo "Rebuild complet:               docker-compose down && docker-compose up --build -d"
echo "Nettoyage Docker:              docker system prune -f"
echo "Permissions scripts:           chmod +x *.sh"
echo ""

echo "📊 VÉRIFICATIONS RAPIDES"
echo "========================"
echo "Version Docker:                docker --version"
echo "Espace disque:                 df -h"
echo "Processus Docker:              docker ps -a"
echo ""

echo "✅ CORRECTIONS APPLIQUÉES"
echo "========================="
echo "• Pydantic ≥2.9.0 (compatible ollama)"
echo "• LangSmith ≥0.1.17 (compatible langchain)"  
echo "• HTTPx ≥0.27.0 (compatible ollama)"
echo "• Docker quotes protection"
echo ""

echo "🎯 SÉQUENCE RECOMMANDÉE"
echo "======================="
echo "1. ./test-pydantic-fix.sh        # Validation (30s)"
echo "2. Si succès → ./deploy-production.sh  # Déploiement (5min)"
echo "3. docker-compose ps             # Vérification"
echo "4. curl http://localhost:8000/health   # Test final"

echo ""
echo "📞 En cas de problème, tous les logs sont conservés et la documentation complète est fournie."
