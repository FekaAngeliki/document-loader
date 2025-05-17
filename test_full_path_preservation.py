#!/usr/bin/env python3
"""
Test script to verify that full file paths are preserved in the database
"""
import asyncio
import tempfile
from pathlib import Path

from src.implementations.file_system_source import FileSystemSource
from src.implementations.file_system_storage import FileSystemStorage

async def test_full_path_preservation():
    """Test that full paths are preserved."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test directory structure
        test_dir = temp_path / "documents" / "subfolder"
        test_dir.mkdir(parents=True)
        
        # Create test file
        test_file = test_dir / "test.txt"
        test_file.write_text("Test content")
        
        # Create FileSystemSource
        source_config = {
            "root_path": str(temp_path),
            "include_patterns": ["**/*.txt"]
        }
        source = FileSystemSource(source_config)
        await source.initialize()
        
        # List files to see what URIs are generated
        files = await source.list_files()
        print(f"Found {len(files)} files")
        
        for file in files:
            print(f"\nFile metadata:")
            print(f"  URI: {file.uri}")
            print(f"  Size: {file.size}")
            print(f"  Content Type: {file.content_type}")
            
            # Test getting content with absolute path
            content = await source.get_file_content(file.uri)
            print(f"  Content: {content.decode()}")
            
            # Show what the expected database entry would be
            print(f"\nExpected database entry:")
            print(f"  original_uri: {file.uri}")
            print(f"  Full path preserved: {Path(file.uri).is_absolute()}")
            
            # Test FileSystemStorage handling
            storage_dir = temp_path / "storage"
            storage_config = {
                "storage_path": str(storage_dir),
                "create_dirs": True,
                "preserve_structure": True,  # Test structure preservation
                "metadata_format": "json"
            }
            
            storage = FileSystemStorage(storage_config)
            await storage.initialize()
            
            # Upload document with metadata containing original_uri
            metadata = {
                "original_uri": file.uri,
                "content_type": file.content_type
            }
            
            storage_uri = await storage.upload_document(
                content, 
                f"test-{Path(file.uri).name}",
                metadata
            )
            
            print(f"\nStorage results:")
            print(f"  Storage URI: {storage_uri}")
            print(f"  Preserved structure: {storage_dir}")
            
            # Check if directory structure was preserved
            storage_files = list(storage_dir.rglob("*"))
            print(f"  Files in storage:")
            for f in storage_files:
                if f.is_file():
                    print(f"    {f.relative_to(storage_dir)}")

if __name__ == "__main__":
    asyncio.run(test_full_path_preservation())