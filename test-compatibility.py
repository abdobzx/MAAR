#!/usr/bin/env python3
"""
Script pour tester la compatibilité des dépendances sans installation réelle
"""

import sys
import re
import json
from pathlib import Path
import urllib.request
import urllib.parse

def get_package_info(package_name):
    """Récupère les informations d'un package depuis PyPI"""
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"⚠️  Impossible de récupérer les infos pour {package_name}: {e}")
        return None

def parse_version_constraint(constraint):
    """Parse une contrainte de version comme 'langchain>=0.3.25'"""
    match = re.match(r'^([a-zA-Z0-9_-]+)(.*)$', constraint.strip())
    if match:
        package = match.group(1)
        version_spec = match.group(2) if match.group(2) else ""
        return package, version_spec
    return constraint.strip(), ""

def check_langchain_versions(requirements_file):
    """Vérifie spécifiquement les versions de LangChain"""
    print(f"\n🔍 Analyse des versions LangChain dans {requirements_file}")
    
    if not Path(requirements_file).exists():
        print(f"❌ Fichier {requirements_file} non trouvé")
        return False
    
    langchain_packages = {}
    
    with open(requirements_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#') and 'langchain' in line.lower():
                package, version = parse_version_constraint(line)
                if package:
                    langchain_packages[package] = {
                        'version': version,
                        'line': line_num,
                        'full_line': line
                    }
    
    print(f"📦 Packages LangChain trouvés:")
    for package, info in langchain_packages.items():
        print(f"  - {package}{info['version']} (ligne {info['line']})")
    
    # Vérifications spécifiques
    issues = []
    
    # Vérifier si langchain-community et langchain sont compatibles
    if 'langchain' in langchain_packages and 'langchain-community' in langchain_packages:
        langchain_version = langchain_packages['langchain']['version']
        community_version = langchain_packages['langchain-community']['version']
        
        print(f"\n🔬 Analyse de compatibilité:")
        print(f"  langchain: {langchain_version}")
        print(f"  langchain-community: {community_version}")
        
        # Si langchain est fixé à 0.3.24 mais community nécessite >= 0.3.25
        if '==0.3.24' in langchain_version and '==0.3.24' in community_version:
            issues.append("❌ langchain-community 0.3.24 requiert langchain>=0.3.25")
        elif '==0.3.25' in langchain_version and '==0.3.24' in community_version:
            issues.append("⚠️  Versions asymétriques détectées")
        elif '==0.3.25' in langchain_version and '==0.3.25' in community_version:
            print("✅ Versions compatibles détectées")
    
    if issues:
        print(f"\n❌ Problèmes détectés:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print(f"\n✅ Aucun conflit LangChain détecté")
        return True

def check_duplicate_packages(requirements_file):
    """Vérifie les packages dupliqués"""
    print(f"\n🔍 Recherche de packages dupliqués dans {requirements_file}")
    
    if not Path(requirements_file).exists():
        print(f"❌ Fichier {requirements_file} non trouvé")
        return False
    
    packages = {}
    duplicates = []
    
    with open(requirements_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                package, version = parse_version_constraint(line)
                if package:
                    if package in packages:
                        duplicates.append({
                            'package': package,
                            'first_occurrence': packages[package],
                            'duplicate': {'line': line_num, 'version': version}
                        })
                    else:
                        packages[package] = {'line': line_num, 'version': version}
    
    if duplicates:
        print(f"❌ Packages dupliqués trouvés:")
        for dup in duplicates:
            print(f"  - {dup['package']}")
            print(f"    Première occurrence: ligne {dup['first_occurrence']['line']} ({dup['first_occurrence']['version']})")
            print(f"    Duplication: ligne {dup['duplicate']['line']} ({dup['duplicate']['version']})")
        return False
    else:
        print(f"✅ Aucun package dupliqué trouvé")
        return True

def main():
    print("🔧 Test de compatibilité des dépendances")
    print("=" * 50)
    
    requirements_files = [
        "requirements.staging.txt",
        "requirements.txt"
    ]
    
    all_good = True
    
    for req_file in requirements_files:
        if Path(req_file).exists():
            print(f"\n📋 Analyse de {req_file}")
            
            # Test des versions LangChain
            langchain_ok = check_langchain_versions(req_file)
            
            # Test des duplicatas
            duplicates_ok = check_duplicate_packages(req_file)
            
            file_ok = langchain_ok and duplicates_ok
            all_good = all_good and file_ok
            
            print(f"🏁 Résultat pour {req_file}: {'✅ OK' if file_ok else '❌ PROBLÈMES'}")
        else:
            print(f"⚠️  Fichier {req_file} non trouvé")
    
    print(f"\n{'='*50}")
    print(f"🏁 Résultat global: {'✅ TOUS LES TESTS PASSÉS' if all_good else '❌ PROBLÈMES DÉTECTÉS'}")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
