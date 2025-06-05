#!/usr/bin/env python3
"""
Script pour diagnostiquer le problème "resolution-too-deep"
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path

def test_requirement_subset(requirements, name):
    """Test un sous-ensemble de requirements"""
    print(f"\n🧪 Test de {name}:")
    print("=" * 50)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for req in requirements:
            f.write(f"{req}\n")
        temp_file = f.name
    
    try:
        # Test avec pip install --dry-run
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "--dry-run", "--no-deps", "-r", temp_file
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ {name}: OK")
            return True
        else:
            print(f"❌ {name}: ERREUR")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {name}: TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {name}: EXCEPTION - {e}")
        return False
    finally:
        os.unlink(temp_file)

def identify_problematic_packages():
    """Identifie les packages problématiques"""
    
    # Packages de base
    core_packages = [
        "fastapi>=0.108.0",
        "uvicorn[standard]>=0.25.0", 
        "pydantic>=2.9.0,<3.0.0"
    ]
    
    # Packages AI
    ai_packages = [
        "langchain>=0.3.25",
        "langchain-community>=0.3.23",
        "crewai>=0.11.2"
    ]
    
    # Packages ML/torch
    ml_packages = [
        "torch>=2.1.0,<3.0.0",
        "transformers>=4.36.0",
        "sentence-transformers>=2.2.2"
    ]
    
    # Packages de base de données
    db_packages = [
        "qdrant-client>=1.7.1,<1.15.0",
        "weaviate-client>=3.25.0,<4.0.0",
        "elasticsearch>=8.11.0,<9.0.0"
    ]
    
    # Test de chaque groupe
    tests = [
        (core_packages, "Core Framework"),
        (ai_packages, "AI Packages"),
        (ml_packages, "ML/Torch Packages"),
        (db_packages, "Database Packages")
    ]
    
    results = {}
    for packages, name in tests:
        results[name] = test_requirement_subset(packages, name)
    
    return results

def test_individual_packages():
    """Test des packages individuels problématiques"""
    
    problematic = [
        "torch>=2.1.0,<3.0.0",
        "kubernetes==28.1.0", 
        "crewai>=0.11.2",
        "langchain==0.3.25",
        "transformers>=4.36.0"
    ]
    
    print(f"\n🔍 Test des packages individuels:")
    print("=" * 50)
    
    for package in problematic:
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "--dry-run", "--no-deps", package
            ], capture_output=True, text=True, timeout=30)
            
            status = "✅ OK" if result.returncode == 0 else "❌ ERREUR"
            print(f"{status} {package}")
            
            if result.returncode != 0:
                print(f"   Erreur: {result.stderr.strip()}")
                
        except Exception as e:
            print(f"💥 {package}: Exception - {e}")

def analyze_dependency_conflicts():
    """Analyse les conflits de dépendances spécifiques"""
    
    print(f"\n🔬 Analyse des conflits spécifiques:")
    print("=" * 50)
    
    # Test de compatibilité langchain
    langchain_combo = [
        "langchain>=0.3.25",
        "langchain-community>=0.3.23", 
        "langsmith>=0.1.17,<0.4.0"
    ]
    
    test_requirement_subset(langchain_combo, "LangChain Combo")
    
    # Test de compatibilité torch
    torch_combo = [
        "torch>=2.1.0,<3.0.0",
        "transformers>=4.36.0",
        "sentence-transformers>=2.2.2"
    ]
    
    test_requirement_subset(torch_combo, "Torch Combo")

def main():
    print("🔧 Diagnostic du problème 'resolution-too-deep'")
    print("=" * 60)
    
    # Test des groupes de packages
    group_results = identify_problematic_packages()
    
    # Test des packages individuels
    test_individual_packages()
    
    # Analyse des conflits
    analyze_dependency_conflicts()
    
    # Résumé
    print(f"\n📊 RÉSUMÉ:")
    print("=" * 50)
    
    for group, success in group_results.items():
        status = "✅ OK" if success else "❌ PROBLÈME"
        print(f"{status} {group}")
    
    print(f"\n💡 RECOMMANDATIONS:")
    print("- Utiliser des bornes inférieures seulement (>=) pour plus de flexibilité")
    print("- Éviter les versions exactes (==) sauf pour les packages critiques")
    print("- Installer en plusieurs phases (core → AI → ML)")
    print("- Laisser pip résoudre automatiquement les versions compatibles")

if __name__ == "__main__":
    main()
