#!/usr/bin/env python3
"""
Script de validation simple pour tester la syntaxe Python
sans les dépendances optionnelles.
"""

import ast
import sys
from pathlib import Path

def validate_python_syntax(file_path):
    """Valide la syntaxe Python d'un fichier."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tenter de parser le fichier
        ast.parse(content)
        print(f"✅ {file_path}: Syntaxe valide")
        return True
    except SyntaxError as e:
        print(f"❌ {file_path}: Erreur de syntaxe - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {file_path}: Erreur - {e}")
        return False

def main():
    """Valide tous les fichiers Python du projet."""
    project_root = Path(__file__).parent.parent
    python_files = []
    
    # Collecter tous les fichiers Python
    for pattern in ["**/*.py"]:
        python_files.extend(project_root.glob(pattern))
    
    # Exclure les fichiers dans venv/
    python_files = [f for f in python_files if 'venv' not in str(f)]
    
    print(f"🔍 Validation de {len(python_files)} fichiers Python...")
    print("=" * 60)
    
    valid_files = 0
    invalid_files = 0
    
    for py_file in sorted(python_files):
        if validate_python_syntax(py_file):
            valid_files += 1
        else:
            invalid_files += 1
    
    print("=" * 60)
    print(f"📊 Résultats: {valid_files} valides, {invalid_files} invalides")
    
    if invalid_files == 0:
        print("🎉 Tous les fichiers Python ont une syntaxe valide!")
        return 0
    else:
        print("🚨 Certains fichiers ont des erreurs de syntaxe.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
