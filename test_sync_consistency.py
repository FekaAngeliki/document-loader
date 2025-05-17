#!/usr/bin/env python3
"""
Test script to verify that sync runs maintain consistent RAG URIs
"""
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

from src.core.file_processor import FileProcessor
from src.implementations.file_system_source import FileSystemSource
from src.core.change_detector import ChangeDetector, ChangeType
from src.data.models import FileRecord, FileStatus

class MockRepository:
    """Mock repository for testing"""
    def __init__(self):
        self.file_records = []
        self.last_sync_run = None
        
    async def get_last_sync_run(self, kb_id):
        return self.last_sync_run
    
    async def get_file_records_by_sync_run(self, sync_run_id):
        return self.file_records
    
    def add_file_record(self, record):
        self.file_records.append(record)

async def test_sync_consistency():
    """Test that sync runs maintain consistent RAG URIs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        kb_name = "test-kb"
        processor = FileProcessor()
        
        # Create test files
        docs_dir = temp_path / "documents"
        docs_dir.mkdir()
        
        test_files = {
            "readme.md": "# Project README",
            "src/main.py": "def main():\n    pass",
            "src/utils.py": "def helper():\n    return 42",
        }
        
        for file_path, content in test_files.items():
            full_path = docs_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        # Create file source
        source = FileSystemSource({"root_path": str(docs_dir)})
        await source.initialize()
        
        # Mock repository
        mock_repo = MockRepository()
        change_detector = ChangeDetector(mock_repo)
        
        print("=== First Sync Run ===")
        
        # First sync - all files are new
        source_files = await source.list_files()
        changes = await change_detector.detect_changes(source_files, 1)
        
        print(f"Found {len(changes)} changes")
        
        # Process files and store records
        records = {}
        for change in changes:
            print(f"\nProcessing: {change.uri}")
            print(f"  Change type: {change.change_type.value}")
            
            content = await source.get_file_content(change.uri)
            file_hash, uuid_filename, rag_uri = await processor.process_file(
                content,
                change.uri,
                kb_name
            )
            
            print(f"  UUID: {uuid_filename}")
            print(f"  RAG URI: {rag_uri}")
            
            # Store record
            record = FileRecord(
                sync_run_id=1,
                original_uri=change.uri,
                rag_uri=rag_uri,
                file_hash=file_hash,
                uuid_filename=uuid_filename,
                upload_time=datetime.now(),
                file_size=change.metadata.size,
                status=FileStatus.NEW.value,
                created_at=datetime.now()  # Add created_at field
            )
            mock_repo.add_file_record(record)
            records[change.uri] = record
        
        # Set up for second sync
        mock_repo.last_sync_run = type('SyncRun', (), {'id': 1})()
        
        print("\n=== Second Sync Run (no changes) ===")
        
        # Second sync - no files changed
        source_files = await source.list_files()
        changes = await change_detector.detect_changes(source_files, 1)
        
        print(f"Found {len(changes)} changes")
        
        for change in changes:
            if change.change_type != ChangeType.UNCHANGED:
                print(f"\nProcessing: {change.uri}")
                print(f"  Change type: {change.change_type.value}")
                
                # Get existing record
                existing_record = change.existing_record
                if existing_record:
                    print(f"  Existing UUID: {existing_record.uuid_filename}")
                    print(f"  Existing RAG URI: {existing_record.rag_uri}")
                
                # Process with existing UUID
                content = await source.get_file_content(change.uri)
                file_hash, uuid_filename, rag_uri = await processor.process_file(
                    content,
                    change.uri,
                    kb_name,
                    existing_uuid=existing_record.uuid_filename if existing_record else None
                )
                
                print(f"  New UUID: {uuid_filename}")
                print(f"  New RAG URI: {rag_uri}")
                
                # Verify consistency
                if existing_record:
                    if uuid_filename == existing_record.uuid_filename:
                        print("  ✓ UUID preserved")
                    else:
                        print("  ✗ UUID changed!")
                    
                    if rag_uri == existing_record.rag_uri:
                        print("  ✓ RAG URI preserved")
                    else:
                        print("  ✗ RAG URI changed!")
        
        print("\n=== Third Sync Run (modify one file) ===")
        
        # Modify one file
        modified_file = docs_dir / "src/main.py"
        modified_file.write_text("def main():\n    print('Hello!')\n")
        
        # Update the metadata for the modified file
        source_files = await source.list_files()
        changes = await change_detector.detect_changes(source_files, 1)
        
        print(f"Found {len(changes)} changes")
        
        for change in changes:
            if change.change_type != ChangeType.UNCHANGED:
                print(f"\nProcessing: {change.uri}")
                print(f"  Change type: {change.change_type.value}")
                
                # Get existing record
                existing_record = change.existing_record
                if existing_record:
                    print(f"  Existing UUID: {existing_record.uuid_filename}")
                    print(f"  Existing RAG URI: {existing_record.rag_uri}")
                
                # Process file
                content = await source.get_file_content(change.uri)
                file_hash, uuid_filename, rag_uri = await processor.process_file(
                    content,
                    change.uri,
                    kb_name,
                    existing_uuid=existing_record.uuid_filename if existing_record else None
                )
                
                print(f"  New UUID: {uuid_filename}")
                print(f"  New RAG URI: {rag_uri}")
                
                # For modified files, UUID should be preserved but hash changes
                if change.change_type == ChangeType.MODIFIED and existing_record:
                    if uuid_filename == existing_record.uuid_filename:
                        print("  ✓ UUID preserved for modified file")
                    else:
                        print("  ✗ UUID changed for modified file!")
                    
                    if rag_uri == existing_record.rag_uri:
                        print("  ✓ RAG URI preserved for modified file")
                    else:
                        print("  ✗ RAG URI changed for modified file!")

if __name__ == "__main__":
    asyncio.run(test_sync_consistency())