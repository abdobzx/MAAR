#!/usr/bin/env python3
"""
Simple integration test for the RAG Multi-Agent system.
Focuses on structure, classes and basic integration.
"""

import sys
import os
import importlib.util
from pathlib import Path

def test_file_structure():
    """Test project file structure."""
    print("=== File Structure Test ===")
    
    required_paths = [
        "agents/ingestion/agent.py",
        "agents/vectorization/agent.py", 
        "agents/storage/agent.py",
        "agents/retrieval/agent.py",
        "agents/synthesis/agent.py",
        "agents/orchestration/agent.py",
        "agents/feedback/agent.py",
        "api/main.py",
        "api/main_simple.py",
        "core/config.py",
        "core/models.py",
        "core/exceptions.py",
        "core/logging.py",
        "core/providers/__init__.py",
        "database/manager.py",
        "database/models.py"
    ]
    
    missing_files = []
    for path in required_paths:
        if not Path(path).exists():
            missing_files.append(path)
            print(f"❌ Missing file: {path}")
        else:
            print(f"✅ File present: {path}")
    
    if missing_files:
        print(f"\n⚠️  {len(missing_files)} missing files")
        return False
    else:
        print(f"\n✅ All {len(required_paths)} required files are present")
        return True


def test_module_syntax():
    """Test Python module syntax."""
    print("=== Module Syntax Test ===")
    
    modules_to_test = [
        "core/config.py",
        "core/models.py", 
        "core/exceptions.py",
        "core/logging.py",
        "agents/synthesis/agent.py",
        "agents/orchestration/agent.py",
        "agents/retrieval/agent.py"
    ]
    
    syntax_errors = []
    for module_path in modules_to_test:
        try:
            # Test compilation
            with open(module_path, 'r', encoding='utf-8') as f:
                source = f.read()
            compile(source, module_path, 'exec')
            print(f"✅ Valid syntax: {module_path}")
            
        except SyntaxError as e:
            syntax_errors.append(f"{module_path}: {e}")
            print(f"❌ Syntax error: {module_path} - {e}")
        except Exception as e:
            syntax_errors.append(f"{module_path}: {e}")
            print(f"⚠️  Warning: {module_path} - {e}")
    
    if syntax_errors:
        print(f"\n⚠️  {len(syntax_errors)} syntax errors detected")
        return False
    else:
        print(f"\n✅ All modules have valid syntax")
        return True


def test_agent_classes():
    """Test presence of agent classes."""
    print("=== Agent Classes Test ===")
    
    agent_classes = [
        ("agents/ingestion/agent.py", "IngestionAgent"),
        ("agents/vectorization/agent.py", "VectorizationAgent"),
        ("agents/storage/agent.py", "StorageAgent"),
        ("agents/retrieval/agent.py", "RetrievalAgent"),
        ("agents/synthesis/agent.py", "SynthesisAgent"),
        ("agents/orchestration/agent.py", "OrchestrationAgent"),
        ("agents/feedback/agent.py", "FeedbackMemoryAgent")
    ]
    
    missing_classes = []
    for file_path, class_name in agent_classes:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if f"class {class_name}" in content:
                print(f"✅ Class found: {class_name} in {file_path}")
            else:
                missing_classes.append(f"{class_name} in {file_path}")
                print(f"❌ Missing class: {class_name} in {file_path}")
                
        except FileNotFoundError:
            missing_classes.append(f"{class_name} in {file_path} (file not found)")
            print(f"❌ File not found: {file_path}")
        except Exception as e:
            missing_classes.append(f"{class_name} in {file_path} (error: {e})")
            print(f"⚠️  Error checking: {file_path} - {e}")
    
    if missing_classes:
        print(f"\n⚠️  {len(missing_classes)} missing classes")
        return False
    else:
        print(f"\n✅ All agent classes are present")
        return True


def test_core_imports():
    """Test core module imports."""
    print("=== Core Imports Test ===")
    
    core_modules = [
        "core.config",
        "core.models", 
        "core.exceptions",
        "core.logging"
    ]
    
    import_errors = []
    for module_name in core_modules:
        try:
            # Add current directory to path
            if '.' not in sys.path:
                sys.path.insert(0, '.')
                
            importlib.import_module(module_name)
            print(f"✅ Import successful: {module_name}")
        except ImportError as e:
            import_errors.append(f"{module_name}: {e}")
            print(f"❌ Import error: {module_name} - {e}")
        except Exception as e:
            import_errors.append(f"{module_name}: {e}")
            print(f"⚠️  Warning: {module_name} - {e}")
    
    if import_errors:
        print(f"\n⚠️  {len(import_errors)} import errors detected")
        return False
    else:
        print(f"\n✅ All core imports work")
        return True


def test_api_structure():
    """Test API structure."""
    print("=== API Structure Test ===")
    
    api_files = ["api/main.py", "api/main_simple.py"]
    api_errors = []
    
    for api_file in api_files:
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic checks
            if "from fastapi import" in content or "FastAPI" in content:
                print(f"✅ FastAPI API detected: {api_file}")
            else:
                api_errors.append(f"{api_file}: FastAPI structure not detected")
                print(f"⚠️  FastAPI structure not detected: {api_file}")
                
        except FileNotFoundError:
            api_errors.append(f"{api_file}: File not found")
            print(f"❌ API file not found: {api_file}")
        except Exception as e:
            api_errors.append(f"{api_file}: {e}")
            print(f"⚠️  Error checking: {api_file} - {e}")
    
    if api_errors:
        print(f"\n⚠️  {len(api_errors)} API issues detected")
        return False
    else:
        print(f"\n✅ API structure validated")
        return True


def test_dependencies_availability():
    """Test dependency availability."""
    print("=== Dependencies Test ===")
    
    # Critical dependencies
    critical_deps = {
        "fastapi": "API Framework",
        "pydantic": "Data validation", 
        "sqlalchemy": "Database ORM",
        "asyncpg": "Async PostgreSQL driver"
    }
    
    # Optional dependencies
    optional_deps = {
        "openai": "OpenAI provider",
        "cohere": "Cohere provider", 
        "ollama": "Local Ollama provider",
        "crewai": "Multi-agent framework",
        "langchain": "LLM framework",
        "numpy": "Numerical computing",
        "sentence_transformers": "Embeddings",
        "aiofiles": "Async file I/O"
    }
    
    critical_missing = []
    optional_missing = []
    
    # Test critical dependencies
    for dep, desc in critical_deps.items():
        try:
            importlib.import_module(dep)
            print(f"✅ {dep} available ({desc})")
        except ImportError:
            critical_missing.append(dep)
            print(f"❌ {dep} missing (critical) - {desc}")
    
    # Test optional dependencies
    for dep, desc in optional_deps.items():
        try:
            importlib.import_module(dep)
            print(f"✅ {dep} available ({desc})")
        except ImportError:
            optional_missing.append(dep)
            print(f"⚠️  {dep} missing (optional) - {desc}")
    
    print(f"\nDependency summary:")
    print(f"- Critical missing: {len(critical_missing)}")
    print(f"- Optional missing: {len(optional_missing)}")
    
    return len(critical_missing) == 0


def main():
    """Main test function."""
    print("🚀 Simple Integration Test - RAG Multi-Agent System")
    print("=" * 60)
    
    # Check working directory
    if not Path("agents").exists():
        print("❌ Error: This script must be run from the MAR project root")
        return False
    
    # Run tests
    tests = [
        ("File Structure", test_file_structure),
        ("Module Syntax", test_module_syntax),
        ("Agent Classes", test_agent_classes),
        ("Core Imports", test_core_imports),
        ("API Structure", test_api_structure),
        ("Dependencies", test_dependencies_availability)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error in test {test_name}: {e}")
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall result: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Project is ready for integration.")
        return True
    else:
        print("⚠️  Some tests failed. Check errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
