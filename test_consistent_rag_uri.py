#!/usr/bin/env python3
"""
Test script to verify that RAG URIs remain consistent across multiple runs
"""
import asyncio
import tempfile
from pathlib import Path

from src.core.file_processor import FileProcessor
from src.implementations.file_system_source import FileSystemSource

async def test_consistent_rag_uri():
    """Test that RAG URIs remain consistent for the same file path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        test_files = [
            temp_path / "docs" / "readme.md",
            temp_path / "src" / "main.py",
            temp_path / "src" / "utils" / "helper.py",
        ]
        
        for file_path in test_files:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"Content of {file_path.name}")
        
        # Create FileProcessor
        processor = FileProcessor()
        kb_name = "test-kb"
        
        print("Testing RAG URI generation consistency")
        print("=" * 50)
        
        for file_path in test_files:
            print(f"\nFile: {file_path}")
            content = file_path.read_bytes()
            
            # Generate URI multiple times for the same file
            results = []
            for i in range(3):
                file_hash, uuid_filename, rag_uri = await processor.process_file(
                    content, 
                    str(file_path.absolute()),  # Use absolute path
                    kb_name
                )
                results.append((uuid_filename, rag_uri))
                print(f"  Run {i+1}: UUID={uuid_filename}, RAG_URI={rag_uri}")
            
            # Verify all runs produce the same result
            first_uuid, first_uri = results[0]
            all_same = all(uuid == first_uuid and uri == first_uri for uuid, uri in results)
            
            if all_same:
                print(f"  ✓ Consistent: All runs produced the same UUID and RAG URI")
            else:
                print(f"  ✗ Inconsistent: Different results across runs")
        
        print("\n" + "=" * 50)
        print("Testing with existing UUID...")
        
        # Test that existing UUID is preserved
        test_file = test_files[0]
        content = test_file.read_bytes()
        
        # First run - generate new UUID
        hash1, uuid1, uri1 = await processor.process_file(
            content,
            str(test_file.absolute()),
            kb_name
        )
        print(f"\nInitial run: UUID={uuid1}, RAG_URI={uri1}")
        
        # Second run - use existing UUID
        hash2, uuid2, uri2 = await processor.process_file(
            content,
            str(test_file.absolute()),
            kb_name,
            existing_uuid=uuid1
        )
        print(f"With existing UUID: UUID={uuid2}, RAG_URI={uri2}")
        
        if uuid1 == uuid2 and uri1 == uri2:
            print("✓ Existing UUID preserved correctly")
        else:
            print("✗ Existing UUID not preserved")
        
        print("\n" + "=" * 50)
        print("Testing path-based deterministic generation...")
        
        # Test that the same path always generates the same UUID
        for file_path in test_files:
            uuid1 = processor.generate_uuid_filename(
                str(file_path.absolute()),
                full_path=str(file_path.absolute())
            )
            uuid2 = processor.generate_uuid_filename(
                str(file_path.absolute()),
                full_path=str(file_path.absolute())
            )
            
            print(f"\n{file_path.name}:")
            print(f"  UUID 1: {uuid1}")
            print(f"  UUID 2: {uuid2}")
            print(f"  Match: {'✓' if uuid1 == uuid2 else '✗'}")

if __name__ == "__main__":
    asyncio.run(test_consistent_rag_uri())