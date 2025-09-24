#!/usr/bin/env python3
"""Test full sync functionality"""

import asyncio
from pathlib import Path
from src.implementations.file_system_storage import FileSystemStorage

async def test_full_sync():
    config = {
        'storage_path': '/Users/giorgosmarinos/Documents/KBRoot/test-docs',
        'kb_name': 'test-docs',
        'create_dirs': True,
    }
    
    storage = FileSystemStorage(config)
    await storage.initialize()
    
    # Test 1: List all current files
    print("Current files in documents directory:")
    docs_dir = Path('/Users/giorgosmarinos/Documents/KBRoot/test-docs/documents')
    if docs_dir.exists():
        files = list(docs_dir.iterdir())
        for file in files[:5]:  # Show first 5 files
            print(f"  {file.name}")
        print(f"  ... (total: {len(files)} files)")
    print()
    
    # Test 2: Delete a file using database URI format
    test_uri = "test-docs/2f714fc7-fe69-46ea-d3f1-86994c226ee3.md"
    print(f"Testing deletion of: {test_uri}")
    
    file_path = storage._uri_to_path(test_uri)
    print(f"File path: {file_path}")
    print(f"Exists before deletion: {file_path.exists()}")
    
    if file_path.exists():
        await storage.delete_document(test_uri)
        print(f"Exists after deletion: {file_path.exists()}")
    else:
        print("File not found, skipping deletion test")
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_full_sync())