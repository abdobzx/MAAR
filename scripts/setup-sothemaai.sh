#!/bin/bash

# Script de configuration pour l'intégration SothemaAI
# Ce script aide à configurer l'environnement pour utiliser SothemaAI

set -e

echo "🔧 Configuration de l'intégration SothemaAI"
echo "=========================================="

# Variables par défaut
SOTHEMAAI_URL="http://localhost:8000"
ENV_FILE=".env"

# Fonction pour demander une entrée utilisateur
prompt_user() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    echo -n "$prompt"
    if [ -n "$default" ]; then
        echo -n " [$default]"
    fi
    echo -n ": "
    
    read -r user_input
    if [ -z "$user_input" ] && [ -n "$default" ]; then
        user_input="$default"
    fi
    
    eval "$var_name='$user_input'"
}

# Vérifier si SothemaAI est accessible
check_sothemaai_connection() {
    echo "🔍 Vérification de la connexion à SothemaAI..."
    
    if curl -s -f "$SOTHEMAAI_URL/api/" > /dev/null 2>&1; then
        echo "✅ SothemaAI est accessible à $SOTHEMAAI_URL"
        return 0
    else
        echo "❌ Impossible de se connecter à SothemaAI à $SOTHEMAAI_URL"
        echo "   Assurez-vous que votre serveur SothemaAI est démarré."
        return 1
    fi
}

# Fonction pour obtenir une clé API
get_api_key() {
    echo ""
    echo "📋 Pour obtenir une clé API SothemaAI :"
    echo "   1. Accédez à $SOTHEMAAI_URL"
    echo "   2. Créez un compte ou connectez-vous"
    echo "   3. Allez dans la section 'API Keys'"
    echo "   4. Générez une nouvelle clé API"
    echo ""
}

# Fonction pour tester la clé API
test_api_key() {
    local api_key="$1"
    local url="$2"
    
    echo "🧪 Test de la clé API..."
    
    response=$(curl -s -w "%{http_code}" -o /tmp/sothemaai_test.json \
        -X POST "$url/api/inference/generate" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $api_key" \
        -d '{"text_input": "Test", "max_length": 10}' 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo "✅ Clé API valide et fonctionnelle"
        return 0
    elif [ "$response" = "401" ]; then
        echo "❌ Clé API invalide ou expirée"
        return 1
    elif [ "$response" = "403" ]; then
        echo "❌ Accès refusé - vérifiez vos permissions"
        return 1
    else
        echo "⚠️  Réponse inattendue du serveur (code: $response)"
        return 1
    fi
}

# Configuration interactive
echo "Ce script va vous aider à configurer l'intégration SothemaAI."
echo ""

# Demander l'URL du serveur SothemaAI
prompt_user "URL du serveur SothemaAI" "$SOTHEMAAI_URL" "SOTHEMAAI_URL"

# Vérifier la connexion
if ! check_sothemaai_connection; then
    echo ""
    echo "❌ Impossible de continuer sans connexion à SothemaAI."
    echo "   Vérifiez que votre serveur SothemaAI est démarré et accessible."
    exit 1
fi

# Demander la clé API
echo ""
get_api_key
prompt_user "Clé API SothemaAI" "" "SOTHEMAAI_API_KEY"

if [ -z "$SOTHEMAAI_API_KEY" ]; then
    echo "❌ Une clé API est requise pour continuer."
    exit 1
fi

# Tester la clé API
if ! test_api_key "$SOTHEMAAI_API_KEY" "$SOTHEMAAI_URL"; then
    echo "❌ La clé API n'est pas valide. Veuillez vérifier et réessayer."
    exit 1
fi

# Demander les autres paramètres
prompt_user "Timeout pour les requêtes (secondes)" "120" "SOTHEMAAI_TIMEOUT"
prompt_user "Utiliser SothemaAI uniquement (désactive les autres fournisseurs)" "true" "USE_SOTHEMAAI_ONLY"

# Créer ou mettre à jour le fichier .env
echo ""
echo "📝 Mise à jour du fichier $ENV_FILE..."

# Sauvegarder l'ancien fichier .env s'il existe
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "   Sauvegarde créée: ${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Fonction pour mettre à jour ou ajouter une variable dans .env
update_env_var() {
    local var_name="$1"
    local var_value="$2"
    local env_file="$3"
    
    if grep -q "^${var_name}=" "$env_file" 2>/dev/null; then
        # Variable existe, la mettre à jour
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^${var_name}=.*|${var_name}=${var_value}|" "$env_file"
        else
            # Linux
            sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" "$env_file"
        fi
    else
        # Variable n'existe pas, l'ajouter
        echo "${var_name}=${var_value}" >> "$env_file"
    fi
}

# Créer le fichier .env s'il n'existe pas
touch "$ENV_FILE"

# Ajouter un commentaire de section
if ! grep -q "# Configuration SothemaAI" "$ENV_FILE"; then
    echo "" >> "$ENV_FILE"
    echo "# Configuration SothemaAI" >> "$ENV_FILE"
fi

# Mettre à jour les variables
update_env_var "SOTHEMAAI_BASE_URL" "$SOTHEMAAI_URL" "$ENV_FILE"
update_env_var "SOTHEMAAI_API_KEY" "$SOTHEMAAI_API_KEY" "$ENV_FILE"
update_env_var "SOTHEMAAI_TIMEOUT" "$SOTHEMAAI_TIMEOUT" "$ENV_FILE"
update_env_var "USE_SOTHEMAAI_ONLY" "$USE_SOTHEMAAI_ONLY" "$ENV_FILE"

# Si utilisation exclusive de SothemaAI, désactiver les autres fournisseurs
if [ "$USE_SOTHEMAAI_ONLY" = "true" ]; then
    update_env_var "OPENAI_API_KEY" "" "$ENV_FILE"
    update_env_var "COHERE_API_KEY" "" "$ENV_FILE"
    update_env_var "OLLAMA_BASE_URL" "" "$ENV_FILE"
fi

echo "✅ Fichier $ENV_FILE mis à jour avec succès"

# Test final de l'intégration
echo ""
echo "🧪 Test final de l'intégration..."

# Créer un script de test Python temporaire
cat > /tmp/test_sothemaai_integration.py << 'EOF'
import asyncio
import os
import sys

# Ajouter le répertoire racine au path
sys.path.insert(0, '/Users/abderrahman/Documents/MAR')

async def test_integration():
    try:
        from core.providers.sothemaai_client import create_sothemaai_client
        
        print("🔄 Test de l'intégration SothemaAI...")
        
        async with create_sothemaai_client() as client:
            # Test de génération
            response = await client.generate_text(
                "Bonjour, comment allez-vous ?", 
                max_length=50
            )
            print(f"✅ Génération réussie: {response[:100]}...")
            
            # Test d'embeddings
            embeddings = await client.generate_embeddings([
                "Test d'embedding",
                "Autre test"
            ])
            print(f"✅ Embeddings générés: {len(embeddings)} vecteurs")
            
        print("🎉 Intégration SothemaAI configurée avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

if __name__ == "__main__":
    # Charger les variables d'environnement
    import dotenv
    dotenv.load_dotenv()
    
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
EOF

# Exécuter le test
if python3 /tmp/test_sothemaai_integration.py; then
    echo ""
    echo "🎉 Configuration terminée avec succès !"
    echo ""
    echo "📋 Résumé de la configuration :"
    echo "   • URL SothemaAI : $SOTHEMAAI_URL"
    echo "   • Clé API : ${SOTHEMAAI_API_KEY:0:8}..."
    echo "   • Timeout : ${SOTHEMAAI_TIMEOUT}s"
    echo "   • Mode exclusif : $USE_SOTHEMAAI_ONLY"
    echo ""
    echo "🚀 Vous pouvez maintenant utiliser SothemaAI dans votre système RAG !"
    echo "   Pour démarrer le système : ./quick-start.sh"
else
    echo ""
    echo "❌ Le test d'intégration a échoué."
    echo "   Vérifiez les logs ci-dessus pour plus de détails."
    exit 1
fi

# Nettoyer le fichier de test temporaire
rm -f /tmp/test_sothemaai_integration.py /tmp/sothemaai_test.json
