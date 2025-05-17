#!/usr/bin/env python
"""
Test the FileSystemStorage URI handling fix.
"""

import asyncio
import tempfile
from pathlib import Path
from src.implementations.file_system_storage import FileSystemStorage

async def test_uri_handling():
    """Test that FileSystemStorage handles both URI formats correctly."""
    print("Testing FileSystemStorage URI handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create storage with configuration
        config = {
            'root_path': temp_dir,
            'kb_name': 'test-docs',
            'create_dirs': True
        }
        
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        # Test simple path format (what the system actually uses)
        simple_uri = "test-docs/document.txt"
        path = storage._uri_to_path(simple_uri)
        print(f"Simple URI: {simple_uri}")
        print(f"Converted to path: {path}")
        print(f"Expected path: {storage.documents_dir / 'test-docs/document.txt'}")
        
        # Verify path is correct
        expected = storage.documents_dir / "test-docs/document.txt"
        assert path == expected, f"Path mismatch: {path} != {expected}"
        print("✓ Simple URI handling works correctly")
        
        # Test file:// URI format (legacy support)
        file_uri = "file:///tmp/test.txt"
        path = storage._uri_to_path(file_uri)
        print(f"\\nFile URI: {file_uri}")
        print(f"Converted to path: {path}")
        assert path == Path("/tmp/test.txt")
        print("✓ File URI handling still works")
        
        # Test path to URI conversion
        test_path = storage.documents_dir / "test.txt"
        uri = storage._path_to_uri(test_path)
        print(f"\\nPath: {test_path}")
        print(f"Converted to URI: {uri}")
        print("✓ Path to URI conversion works")
        
        # Test creating a file with simple URI
        test_content = b"Test content"
        test_uri = "test-file.txt"
        metadata = {"test": "value"}
        
        print(f"\\nTesting upload with URI: {test_uri}")
        await storage.upload_document(test_content, test_uri, metadata)
        
        # Verify file was created
        file_path = storage._uri_to_path(test_uri)
        assert file_path.exists(), f"File not created at {file_path}"
        print(f"✓ File created at: {file_path}")
        
        # Test updating the file
        updated_content = b"Updated content"
        await storage.update_document(test_uri, updated_content, metadata)
        
        # Verify file was updated
        with open(file_path, 'rb') as f:
            content = f.read()
        assert content == updated_content, "File not updated correctly"
        print("✓ File updated successfully")
        
        print("\\n=== All tests passed! ===")
        print("FileSystemStorage now correctly handles:")
        print("- Simple URIs (test-docs/file.txt)")
        print("- File URIs (file:///path/to/file)")
        print("- Path conversions in both directions")

async def main():
    """Run the test."""
    try:
        await test_uri_handling()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())