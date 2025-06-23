#!/bin/bash

# 🔍 VÉRIFICATION VERSIONS DISPONIBLES - LANGCHAIN
# Vérifie les versions réellement disponibles sur PyPI

echo "🔍 VÉRIFICATION VERSIONS LANGCHAIN DISPONIBLES"
echo "=============================================="

echo "📦 1. Versions LangChain disponibles (dernières):"
curl -s https://pypi.org/pypi/langchain/json | python3 -c "
import json, sys
data = json.load(sys.stdin)
releases = list(data['releases'].keys())
latest_releases = [r for r in releases if r.startswith('0.3.')][-10:]
print('Dernières versions 0.3.x:')
for release in latest_releases:
    print(f'  - {release}')
"

echo ""
echo "📦 2. Versions LangChain-Community disponibles (dernières):"
curl -s https://pypi.org/pypi/langchain-community/json | python3 -c "
import json, sys
data = json.load(sys.stdin)
releases = list(data['releases'].keys())
latest_releases = [r for r in releases if r.startswith('0.3.')][-10:]
print('Dernières versions 0.3.x:')
for release in latest_releases:
    print(f'  - {release}')
"

echo ""
echo "✅ VERSIONS RECOMMANDÉES POUR COMPATIBILITY:"
echo "langchain==0.3.24"
echo "langchain-community==0.3.24"
echo "langsmith>=0.1.17,<0.4.0"

echo ""
echo "🔧 CORRECTION À APPLIQUER:"
echo "sed -i 's/langchain==0.3.25/langchain==0.3.24/g' requirements.fast.txt"
echo "sed -i 's/langchain-community==0.3.25/langchain-community==0.3.24/g' requirements.fast.txt"
