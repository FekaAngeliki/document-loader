#!/usr/bin/env python3
"""
Basic Import Test

This script tests that the multi-source implementation can be imported
without syntax errors or missing dependencies.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_multi_source_models():
    """Test importing multi-source models."""
    try:
        from data.multi_source_models import (
            MultiSourceKnowledgeBase,
            SourceDefinition,
            EnhancedFileRecord,
            create_multi_source_kb_from_config
        )
        print("✅ Multi-source models import successful")
        return True
    except Exception as e:
        print(f"❌ Multi-source models import failed: {e}")
        return False

def test_multi_source_repository():
    """Test importing multi-source repository."""
    try:
        from data.multi_source_repository import MultiSourceRepository
        print("✅ Multi-source repository import successful")
        return True
    except Exception as e:
        print(f"❌ Multi-source repository import failed: {e}")
        return False

def test_sharepoint_source():
    """Test importing SharePoint source."""
    try:
        from implementations.sharepoint_source import SharePointSource
        print("✅ SharePoint source import successful")
        return True
    except Exception as e:
        print(f"❌ SharePoint source import failed: {e}")
        return False

def test_enterprise_sharepoint_source():
    """Test importing enterprise SharePoint source."""
    try:
        from implementations.enterprise_sharepoint_source import EnterpriseSharePointSource
        print("✅ Enterprise SharePoint source import successful")
        return True
    except Exception as e:
        print(f"❌ Enterprise SharePoint source import failed: {e}")
        return False

def test_multi_source_batch_runner():
    """Test importing multi-source batch runner."""
    try:
        from core.multi_source_batch_runner import MultiSourceBatchRunner
        print("✅ Multi-source batch runner import successful")
        return True
    except Exception as e:
        print(f"❌ Multi-source batch runner import failed: {e}")
        return False

def test_cli_multi_source_commands():
    """Test importing CLI multi-source commands."""
    try:
        from cli.multi_source_commands import multi_source
        print("✅ CLI multi-source commands import successful")
        return True
    except Exception as e:
        print(f"❌ CLI multi-source commands import failed: {e}")
        return False

def test_basic_implementations():
    """Test basic implementation imports."""
    try:
        from implementations.file_system_source import FileSystemSource
        from implementations.mock_rag_system import MockRAGSystem
        print("✅ Basic implementations import successful")
        return True
    except Exception as e:
        print(f"❌ Basic implementations import failed: {e}")
        return False

def test_database_models():
    """Test database model imports."""
    try:
        from data.models import KnowledgeBase, SyncRun, FileRecord
        from data.database import Database, DatabaseConfig
        print("✅ Database models import successful")
        return True
    except Exception as e:
        print(f"❌ Database models import failed: {e}")
        return False

def test_core_components():
    """Test core component imports."""
    try:
        from core.factory import SourceFactory, RAGFactory
        from core.batch_runner import BatchRunner
        print("✅ Core components import successful")
        return True
    except Exception as e:
        print(f"❌ Core components import failed: {e}")
        return False

def run_import_tests():
    """Run all import tests."""
    print("Basic Import Tests")
    print("=" * 40)
    
    tests = [
        ("Database Models", test_database_models),
        ("Core Components", test_core_components),
        ("Basic Implementations", test_basic_implementations),
        ("Multi-Source Models", test_multi_source_models),
        ("Multi-Source Repository", test_multi_source_repository),
        ("SharePoint Source", test_sharepoint_source),
        ("Enterprise SharePoint Source", test_enterprise_sharepoint_source),
        ("Multi-Source Batch Runner", test_multi_source_batch_runner),
        ("CLI Multi-Source Commands", test_cli_multi_source_commands),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*40)
    print("IMPORT TEST SUMMARY")
    print("="*40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All import tests passed!")
        print("✅ Multi-source implementation can be imported successfully")
        return True
    else:
        print(f"\n⚠️  {total - passed} import tests failed.")
        print("Some modules may have syntax errors or missing dependencies.")
        return False

if __name__ == "__main__":
    success = run_import_tests()
    
    if success:
        print("\n🎯 Multi-source imports are working!")
        print("Ready to proceed with functional testing.")
        sys.exit(0)
    else:
        print("\n⚠️  Some import issues found. Check the errors above.")
        sys.exit(1)