#!/usr/bin/env python3
"""Test with the actual storage path"""

import asyncio
from pathlib import Path
from src.implementations.file_system_storage import FileSystemStorage

async def test_actual_storage():
    # Use the actual path configuration
    config = {
        'storage_path': '/Users/giorgosmarinos/Documents/KBRoot/test-docs',
        'kb_name': 'test-docs',
        'create_dirs': True,
    }
    
    storage = FileSystemStorage(config)
    await storage.initialize()
    
    print(f"Storage path: {storage.storage_path}")
    print(f"Documents dir: {storage.documents_dir}")
    print(f"Expected documents dir: /Users/giorgosmarinos/Documents/KBRoot/test-docs/documents")
    print()
    
    # Test the URI conversion
    test_uri = "test-docs/2f714fc7-fe69-46ea-d3f1-86994c226ee3.md"
    path = storage._uri_to_path(test_uri)
    print(f"URI: {test_uri}")
    print(f"Converted path: {path}")
    print(f"Expected path: /Users/giorgosmarinos/Documents/KBRoot/test-docs/documents/2f714fc7-fe69-46ea-d3f1-86994c226ee3.md")
    
    # Check what's in the current structure
    print("\nCurrent 'default' structure:")
    default_dir = Path("/Users/giorgosmarinos/Documents/KBRoot/test-docs/default/documents")
    if default_dir.exists():
        for file in default_dir.iterdir():
            print(f"  {file.name}")
    
    # Check what should be in the new structure
    print("\nNew structure (documents dir):")
    if storage.documents_dir.exists():
        for file in storage.documents_dir.iterdir():
            print(f"  {file.name}")
    else:
        print("  Directory doesn't exist yet")

if __name__ == "__main__":
    asyncio.run(test_actual_storage())