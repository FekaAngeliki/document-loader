#!/usr/bin/env python3
"""Run all key tests for the document-loader application"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path so we can import the modules
sys.path.append(str(Path(__file__).parent.parent))

from src.implementations.file_system_storage import FileSystemStorage

async def test_uri_mapping(config: Dict[str, Any]) -> bool:
    """Test URI mapping between database and file system"""
    print("\n=== Testing URI Mapping ===")
    try:
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        # Test URI to path conversion
        db_uri = "test-docs/test-file.md"
        file_path = storage._uri_to_path(db_uri)
        print(f"✓ URI '{db_uri}' maps to path: {file_path}")
        
        # Test path to URI conversion
        test_path = storage.documents_dir / "test-file.md"
        converted_uri = storage._path_to_uri(test_path)
        print(f"✓ Path '{test_path}' maps to URI: {converted_uri}")
        
        # Verify they match
        assert converted_uri == db_uri, f"URI mismatch: {converted_uri} != {db_uri}"
        print("✓ URI mapping is bidirectional and consistent")
        
        return True
    except Exception as e:
        print(f"✗ URI mapping test failed: {e}")
        return False

async def test_file_operations(config: Dict[str, Any]) -> bool:
    """Test file upload and deletion operations"""
    print("\n=== Testing File Operations ===")
    try:
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        # Test upload
        content = b"Test content for file operations"
        filename = "test-operations.md"
        metadata = {"test": "data", "timestamp": "2024-01-01"}
        
        uri = await storage.upload_document(content, filename, metadata)
        print(f"✓ Uploaded file with URI: {uri}")
        
        # Verify file exists
        file_path = storage._uri_to_path(uri)
        assert file_path.exists(), f"File not found at {file_path}"
        print(f"✓ File exists at: {file_path}")
        
        # Test deletion
        await storage.delete_document(uri)
        assert not file_path.exists(), f"File still exists after deletion: {file_path}"
        print(f"✓ File successfully deleted")
        
        return True
    except Exception as e:
        print(f"✗ File operations test failed: {e}")
        return False

async def test_directory_structure(config: Dict[str, Any]) -> bool:
    """Test the directory structure is created correctly"""
    print("\n=== Testing Directory Structure ===")
    try:
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        # Check documents directory
        assert storage.documents_dir.exists(), f"Documents directory missing: {storage.documents_dir}"
        print(f"✓ Documents directory exists: {storage.documents_dir}")
        
        # Check metadata directory
        assert storage.metadata_dir.exists(), f"Metadata directory missing: {storage.metadata_dir}"
        print(f"✓ Metadata directory exists: {storage.metadata_dir}")
        
        # Verify no extra "default" directories
        wrong_path = storage.storage_path / "default" / "documents"
        if wrong_path.exists():
            print(f"⚠ Warning: Old directory structure still exists: {wrong_path}")
        else:
            print("✓ No unnecessary 'default' subdirectories")
        
        return True
    except Exception as e:
        print(f"✗ Directory structure test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("Document Loader Test Suite")
    print("=" * 50)
    
    # Test configuration
    config = {
        'storage_path': '/Users/giorgosmarinos/Documents/KBRoot/test-docs',
        'kb_name': 'test-docs',
        'create_dirs': True,
    }
    
    print(f"Configuration:")
    print(f"  Storage Path: {config['storage_path']}")
    print(f"  KB Name: {config['kb_name']}")
    
    # Run tests
    results = []
    results.append(await test_directory_structure(config))
    results.append(await test_uri_mapping(config))
    results.append(await test_file_operations(config))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)