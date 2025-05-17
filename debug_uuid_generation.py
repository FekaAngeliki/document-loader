#!/usr/bin/env python3
"""
Debug script to understand why UUIDs are being regenerated
"""
import asyncio
from src.core.file_processor import FileProcessor

async def debug_uuid_generation():
    """Debug UUID generation for specific files."""
    processor = FileProcessor()
    kb_name = "test-docs"
    
    # Test with your actual file paths
    test_files = [
        "/Users/giorgosmarinos/Documents/scrapper-output/claude-code-tutorials.md",
        "/Users/giorgosmarinos/Documents/scrapper-output/getting-started-chromadb.md"
    ]
    
    print("Testing UUID generation for files")
    print("=" * 50)
    
    for file_path in test_files:
        print(f"\nFile: {file_path}")
        
        # Generate UUID without existing UUID (new file scenario)
        uuid1 = processor.generate_uuid_filename(file_path, full_path=file_path)
        print(f"New file UUID: {uuid1}")
        
        # Generate again to check consistency
        uuid2 = processor.generate_uuid_filename(file_path, full_path=file_path)
        print(f"Second run UUID: {uuid2}")
        print(f"Match: {'YES' if uuid1 == uuid2 else 'NO'}")
        
        # Test with the UUIDs from your database
        if "claude-code-tutorials" in file_path:
            db_uuids = ["47b9cf7c-8aa6-4146-8b19-e6425812538d.md", "7ee40a56-dc7f-f93b-e947-ddf39a86ab71.md"]
        else:
            db_uuids = ["86b1c014-cbef-4444-b771-51e6b5a2ed8c.md", "0e342622-5f2d-ae28-6df0-f7d0739bde7c.md"]
        
        print(f"UUIDs from DB: {db_uuids}")
        print(f"Generated matches any DB UUID: {uuid1 in db_uuids}")
        
        # Test with existing UUID
        existing_uuid = db_uuids[0]
        uuid3 = processor.generate_uuid_filename(file_path, existing_uuid=existing_uuid, full_path=file_path)
        print(f"With existing UUID ({existing_uuid}): {uuid3}")
        print(f"Preserves existing: {'YES' if uuid3 == existing_uuid else 'NO'}")
    
    print("\n" + "=" * 50)
    print("Testing deterministic generation based on path hash")
    
    for file_path in test_files:
        print(f"\nFile: {file_path}")
        
        # Show the path hash
        import hashlib
        path_hash = hashlib.sha256(file_path.encode()).hexdigest()
        print(f"Path hash: {path_hash}")
        print(f"UUID format: {path_hash[:8]}-{path_hash[8:12]}-{path_hash[12:16]}-{path_hash[16:20]}-{path_hash[20:32]}")
        
        # Check if this matches what we generate
        generated_uuid = processor.generate_uuid_filename(file_path, full_path=file_path)
        print(f"Generated UUID: {generated_uuid}")
        
    print("\n" + "=" * 50)
    print("Checking actual process_file behavior")
    
    # Create dummy content
    dummy_content = b"test content"
    
    for file_path in test_files:
        print(f"\nFile: {file_path}")
        
        # First run (no existing UUID)
        hash1, uuid1, uri1 = await processor.process_file(dummy_content, file_path, kb_name)
        print(f"First run:")
        print(f"  UUID: {uuid1}")
        print(f"  URI: {uri1}")
        
        # Second run (still no existing UUID - simulating both marked as "new")
        hash2, uuid2, uri2 = await processor.process_file(dummy_content, file_path, kb_name)
        print(f"Second run (no existing UUID):")
        print(f"  UUID: {uuid2}")
        print(f"  URI: {uri2}")
        print(f"  Same as first: {'YES' if uuid1 == uuid2 else 'NO'}")
        
        # Third run with existing UUID
        hash3, uuid3, uri3 = await processor.process_file(dummy_content, file_path, kb_name, existing_uuid=uuid1)
        print(f"Third run (with existing UUID):")
        print(f"  UUID: {uuid3}")
        print(f"  URI: {uri3}")
        print(f"  Same as first: {'YES' if uuid1 == uuid3 else 'NO'}")

if __name__ == "__main__":
    asyncio.run(debug_uuid_generation())