#!/usr/bin/env python3
"""
Test script to verify full path preservation in the database
"""
import asyncio
import tempfile
from pathlib import Path

from src.data.database import Database, DatabaseConfig
from src.data.repository import Repository
from src.implementations.file_system_source import FileSystemSource

async def test_database_full_path():
    """Test that full paths are preserved in the database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test directory structure
        test_dir = temp_path / "documents" / "project" / "src"
        test_dir.mkdir(parents=True)
        
        # Create test files
        files_data = [
            ("main.py", "print('Hello, World!')"),
            ("utils.py", "def helper():\n    pass"),
            ("config.json", '{"key": "value"}')
        ]
        
        for filename, content in files_data:
            test_file = test_dir / filename
            test_file.write_text(content)
        
        # Create a file in a different subdirectory
        other_dir = temp_path / "documents" / "tests"
        other_dir.mkdir(parents=True)
        test_file = other_dir / "test_main.py"
        test_file.write_text("def test_main():\n    assert True")
        
        # Create FileSystemSource
        source_config = {
            "root_path": str(temp_path / "documents"),
            "include_patterns": ["**/*.py", "**/*.json"]
        }
        
        source = FileSystemSource(source_config)
        await source.initialize()
        
        # List files
        files = await source.list_files()
        print(f"Found {len(files)} files:")
        print()
        
        for file in files:
            print(f"File: {file.uri}")
            print(f"  Absolute: {Path(file.uri).is_absolute()}")
            print(f"  Size: {file.size} bytes")
            print(f"  Type: {file.content_type}")
            print()
        
        # Show what would be stored in the database
        print("Database entries would contain:")
        print("─" * 50)
        print("original_uri column values:")
        for file in files:
            print(f"  {file.uri}")
        print()
        
        # Show relative paths that would be extracted
        print("Relative paths from storage:")
        for file in files:
            # Show how to extract relative path from full path
            full_path = Path(file.uri)
            if len(full_path.parts) >= 3:
                relative_parts = full_path.parts[-3:]
                relative_path = Path(*relative_parts)
                print(f"  {relative_path}")
            else:
                print(f"  {full_path.name}")

if __name__ == "__main__":
    asyncio.run(test_database_full_path())