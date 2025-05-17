#!/usr/bin/env python3
"""Test URI mapping between database and file system"""

import asyncio
from pathlib import Path
from src.implementations.file_system_storage import FileSystemStorage

async def test_uri_mapping():
    # Use the actual configuration
    config = {
        'storage_path': '/Users/giorgosmarinos/Documents/KBRoot/test-docs',
        'kb_name': 'test-docs',
        'create_dirs': True,
    }
    
    storage = FileSystemStorage(config)
    await storage.initialize()
    
    print("Testing URI mapping:")
    print(f"Storage path: {storage.storage_path}")
    print(f"Documents dir: {storage.documents_dir}")
    print()
    
    # Test case 1: Database URI to file path
    db_uri = "test-docs/2f714fc7-fe69-46ea-d3f1-86994c226ee3.md"
    file_path = storage._uri_to_path(db_uri)
    print(f"Database URI: {db_uri}")
    print(f"Converted to path: {file_path}")
    print(f"File exists: {file_path.exists()}")
    print()
    
    # Test case 2: File path to database URI
    test_file_path = storage.documents_dir / "2f714fc7-fe69-46ea-d3f1-86994c226ee3.md"
    converted_uri = storage._path_to_uri(test_file_path)
    print(f"File path: {test_file_path}")
    print(f"Converted to URI: {converted_uri}")
    print(f"Matches database format: {converted_uri == db_uri}")
    print()
    
    # Test upload and get the URI
    content = b"Test content"
    filename = "test-file.md"
    metadata = {"test": "data"}
    
    uploaded_uri = await storage.upload_document(content, filename, metadata)
    print(f"Uploaded file URI: {uploaded_uri}")
    print(f"Expected format: test-docs/test-file.md")
    print(f"Matches expected: {uploaded_uri == 'test-docs/test-file.md'}")
    
    # Clean up
    await storage.delete_document(uploaded_uri)

if __name__ == "__main__":
    asyncio.run(test_uri_mapping())