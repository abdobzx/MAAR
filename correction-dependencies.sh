#!/bin/bash
# Script pour corriger spécifiquement le fichier dependencies.py

# Vérifier si le fichier existe
if [ ! -f "api/auth/dependencies.py" ]; then
    echo "Erreur: Le fichier api/auth/dependencies.py n'existe pas."
    exit 1
fi

# Sauvegarder le fichier original
cp api/auth/dependencies.py api/auth/dependencies.py.backup
echo "✓ Sauvegarde du fichier original créée: api/auth/dependencies.py.backup"

# Localiser et corriger le problème de "return api_permission_checker"
if grep -n "return permission_checker" api/auth/dependencies.py | grep -A 5 "return api_permission_checker"; then
    echo "Problème détecté: double return après return permission_checker"
    
    # Correction: supprimer la ligne return api_permission_checker
    sed -i '/return permission_checker/{n;/^\s*$/n;/^\s*return api_permission_checker/d;}' api/auth/dependencies.py
    
    echo "✓ Correction appliquée: Suppression de 'return api_permission_checker'"
else
    echo "✓ Le problème de double return n'a pas été détecté."
fi

# Vérifier si require_api_key_permission est défini
if ! grep -q "def require_api_key_permission" api/auth/dependencies.py; then
    echo "Problème détecté: fonction require_api_key_permission manquante"
    
    # Chercher où insérer la fonction (juste avant les instances prédéfinies)
    LINE_NUM=$(grep -n "# Instances prédéfinies des vérificateurs de rôles" api/auth/dependencies.py | cut -d':' -f1)
    
    if [ -z "$LINE_NUM" ]; then
        echo "Impossible de trouver l'emplacement d'insertion. Insertion à la fin du fichier."
        LINE_NUM=$(wc -l < api/auth/dependencies.py)
    else
        echo "La fonction sera insérée avant la ligne $LINE_NUM"
    fi
    
    # Créer un fichier temporaire avec la fonction à insérer
    cat > /tmp/api_key_function.txt << 'EOF'

def require_api_key_permission(required_permission: str):
    """
    Dependency factory pour vérifier les permissions des clés API
    
    Args:
        required_permission: Permission requise pour la clé API
        
    Returns:
        Dependency function
    """
    async def api_permission_checker(
        api_key: Dict[str, Any] = Depends(get_api_key_user)
    ):
        # Vérifier si la clé API a la permission requise
        api_key_permissions = set(api_key.get("permissions", []))
        
        if required_permission not in api_key_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission API requise: {required_permission}"
            )
        
        return api_key
    
    return api_permission_checker

EOF

    # Insérer la fonction au bon endroit
    sed -i "${LINE_NUM}r /tmp/api_key_function.txt" api/auth/dependencies.py
    echo "✓ Fonction require_api_key_permission ajoutée"
else
    echo "✓ La fonction require_api_key_permission est déjà définie."
fi

echo "Vérification finale..."
if grep -q "return api_permission_checker" api/auth/dependencies.py | grep -A 3 -B 3 "return permission_checker"; then
    echo "⚠️ Attention: Il reste peut-être encore du code problématique."
    grep -n "return api_permission_checker" api/auth/dependencies.py
else
    echo "✅ Le fichier semble correctement corrigé."
fi

echo "Correction terminée. Veuillez reconstruire et redémarrer les conteneurs Docker."
