#!/usr/bin/env python3
"""Test script to verify file deletion works correctly"""

import asyncio
from pathlib import Path
from src.implementations.file_system_storage import FileSystemStorage

async def test_deletion():
    # Configure the file system storage
    config = {
        'root_path': '/Users/giorgosmarinos/Documents/KBRoot',
        'kb_name': 'test-docs',
        'create_dirs': True,
        'preserve_structure': False,
        'metadata_format': 'json'
    }
    
    storage = FileSystemStorage(config)
    await storage.initialize()
    
    # Test URI
    uri = 'test-docs/2f714fc7-fe69-46ea-d3f1-86994c226ee3.md'
    
    print(f"Testing deletion of: {uri}")
    print(f"Documents directory: {storage.documents_dir}")
    
    # Convert URI to path
    file_path = storage._uri_to_path(uri)
    print(f"Computed file path: {file_path}")
    print(f"File exists: {file_path.exists()}")
    
    if file_path.exists():
        # Try to delete
        await storage.delete_document(uri)
        print(f"After deletion - File exists: {file_path.exists()}")
    else:
        print("File not found at computed path")
        # Let's check the actual path
        actual_path = Path('/Users/giorgosmarinos/Documents/KBRoot/test-docs/default/documents/2f714fc7-fe69-46ea-d3f1-86994c226ee3.md')
        print(f"Actual file exists at: {actual_path.exists()}")

if __name__ == "__main__":
    asyncio.run(test_deletion())