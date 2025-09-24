#!/usr/bin/env python3
"""Test the new directory structure"""

import asyncio
import tempfile
from pathlib import Path
from src.implementations.file_system_storage import FileSystemStorage

async def test_structure():
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir) / "test-kb"
        test_path.mkdir(exist_ok=True)
        
        config = {
            'storage_path': str(test_path),
            'kb_name': 'test-kb',  # This should not create additional subdirectory
            'create_dirs': True,
        }
        
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        print(f"Storage path: {storage.storage_path}")
        print(f"Documents dir: {storage.documents_dir}")
        print(f"Metadata dir: {storage.metadata_dir}")
        
        # Test saving a document
        content = b"Test content"
        filename = "test-doc.txt"
        metadata = {"source": "test"}
        
        uri = await storage.upload_document(content, filename, metadata)
        print(f"\nSaved document URI: {uri}")
        
        # Check the actual file location
        expected_path = test_path / "documents" / filename
        print(f"Expected path: {expected_path}")
        print(f"File exists: {expected_path.exists()}")
        
        # List directory structure
        print(f"\nDirectory structure:")
        for item in test_path.rglob("*"):
            rel_path = item.relative_to(test_path)
            print(f"  {rel_path}")
        
        # Test deletion
        await storage.delete_document(uri)
        print(f"\nAfter deletion - File exists: {expected_path.exists()}")
        
        return uri

if __name__ == "__main__":
    uri = asyncio.run(test_structure())
    print(f"\nTest completed successfully with URI: {uri}")