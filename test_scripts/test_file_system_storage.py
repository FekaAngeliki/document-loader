#!/usr/bin/env python3
"""
Test script for FileSystemStorage implementation
"""
import asyncio
import tempfile
from pathlib import Path

from src.implementations.file_system_storage import FileSystemStorage

async def test_file_system_storage():
    """Test the FileSystemStorage implementation."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing in temporary directory: {temp_dir}")
        
        # Configure the storage
        config = {
            "storage_path": temp_dir,
            "create_dirs": True,
            "preserve_structure": False,
            "metadata_format": "json"
        }
        
        # Create storage instance
        storage = FileSystemStorage(config)
        
        try:
            # Initialize
            print("Initializing storage...")
            await storage.initialize()
            print("✓ Storage initialized")
            
            # Test upload
            print("\nTesting document upload...")
            content = b"Hello, World! This is a test document."
            filename = "test-document.txt"
            metadata = {
                "original_filename": "test.txt",
                "content_type": "text/plain",
                "author": "Test User"
            }
            
            uri = await storage.upload_document(content, filename, metadata)
            print(f"✓ Document uploaded: {uri}")
            
            # Test get
            print("\nTesting document retrieval...")
            doc_metadata = await storage.get_document(uri)
            if doc_metadata:
                print(f"✓ Document found: {doc_metadata.name}")
                print(f"  Size: {doc_metadata.size} bytes")
                print(f"  Metadata: {doc_metadata.metadata}")
            else:
                print("✗ Document not found")
            
            # Test list
            print("\nTesting document listing...")
            documents = await storage.list_documents()
            print(f"✓ Found {len(documents)} document(s)")
            for doc in documents:
                print(f"  - {doc.name} ({doc.size} bytes)")
            
            # Test update
            print("\nTesting document update...")
            new_content = b"Updated content for the test document."
            new_metadata = metadata.copy()
            new_metadata["updated"] = True
            
            await storage.update_document(uri, new_content, new_metadata)
            print("✓ Document updated")
            
            # Verify update
            doc_metadata = await storage.get_document(uri)
            if doc_metadata:
                print(f"  New size: {doc_metadata.size} bytes")
                print(f"  Updated metadata: {doc_metadata.metadata}")
            
            # Test delete
            print("\nTesting document deletion...")
            await storage.delete_document(uri)
            print("✓ Document deleted")
            
            # Verify deletion
            doc_metadata = await storage.get_document(uri)
            if doc_metadata is None:
                print("✓ Document successfully removed")
            else:
                print("✗ Document still exists")
            
            # Cleanup
            await storage.cleanup()
            print("\n✓ All tests completed successfully!")
            
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_file_system_storage())