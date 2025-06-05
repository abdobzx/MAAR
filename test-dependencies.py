#!/usr/bin/env python3
"""
Script pour tester la résolution des dépendances avant Docker build
"""

import subprocess
import sys
import tempfile
import os

def test_dependencies(requirements_file):
    """Test de résolution des dépendances sans installation"""
    
    print(f"🔍 Test des dépendances dans {requirements_file}")
    
    # Créer un environnement virtuel temporaire
    with tempfile.TemporaryDirectory() as tmp_dir:
        venv_path = os.path.join(tmp_dir, "test_env")
        
        # Créer l'environnement virtuel
        print("📦 Création de l'environnement virtuel temporaire...")
        result = subprocess.run([
            sys.executable, "-m", "venv", venv_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Erreur lors de la création du venv: {result.stderr}")
            return False
        
        # Déterminer le chemin vers pip dans le venv
        if sys.platform == "win32":
            pip_path = os.path.join(venv_path, "Scripts", "pip")
        else:
            pip_path = os.path.join(venv_path, "bin", "pip")
        
        # Mettre à jour pip
        print("⬆️ Mise à jour de pip...")
        subprocess.run([
            pip_path, "install", "--upgrade", "pip", "setuptools", "wheel"
        ], capture_output=True, text=True)
        
        # Test dry-run de l'installation
        print("🧪 Test de résolution des dépendances (dry-run)...")
        result = subprocess.run([
            pip_path, "install", "--dry-run", "-r", requirements_file
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Test de dépendances réussi !")
            print("📋 Packages qui seraient installés:")
            for line in result.stdout.split('\n'):
                if 'Would install' in line:
                    print(f"   {line}")
            return True
        else:
            print("❌ Conflit de dépendances détecté !")
            print("🔍 Détails de l'erreur:")
            print(result.stderr)
            return False

def main():
    requirements_files = [
        "requirements.staging.txt",
        "requirements.txt"
    ]
    
    success = True
    for req_file in requirements_files:
        if os.path.exists(req_file):
            if not test_dependencies(req_file):
                success = False
            print("-" * 50)
        else:
            print(f"⚠️ Fichier {req_file} non trouvé")
    
    if success:
        print("🎉 Tous les tests de dépendances ont réussi !")
        return 0
    else:
        print("💥 Des conflits de dépendances ont été détectés")
        return 1

if __name__ == "__main__":
    sys.exit(main())
