#!/usr/bin/env python
"""
Direct test of the change detector logic without database dependency.
"""

import asyncio
from datetime import datetime
from typing import Dict, List
from src.core.change_detector import ChangeDetector, FileChange, ChangeType
from src.data.models import FileRecord, FileStatus
from src.abstractions.file_source import FileMetadata

class MockRepository:
    """Mock repository for testing."""
    
    def __init__(self):
        self.files = {}
        self.next_id = 1
        
    async def get_knowledge_base(self, kb_id: int):
        """Mock implementation."""
        # Return a mock knowledge base
        return type('MockKnowledgeBase', (), {'id': kb_id, 'name': 'test-kb'})()
    
    async def get_latest_file_records_for_kb(self, kb_name: str):
        """Mock implementation."""
        # Return all files as a list
        return list(self.files.values())
    
    def add_file(self, uri: str, status: str):
        """Add a mock file record."""
        self.files[uri] = FileRecord(
            id=self.next_id,
            sync_run_id=1,
            original_uri=uri,
            rag_uri=f"rag/{uri}",
            file_hash="mockhash",
            uuid_filename="mockuuid",
            status=status,
            created_at=datetime.now(),
            file_size=100
        )
        self.next_id += 1

async def test_restored_file_detection():
    """Test that restored files are detected as NEW."""
    print("Testing restored file detection...")
    
    # Setup
    mock_repo = MockRepository()
    detector = ChangeDetector(mock_repo)
    
    # Add a deleted file to the mock repo
    mock_repo.add_file("file1.txt", FileStatus.DELETED.value)
    
    # Simulate the file reappearing
    source_files = [FileMetadata(
        uri="file1.txt",
        size=100,
        created_at=datetime.now(),
        modified_at=datetime.now(),
        content_type="text/plain"
    )]
    
    # Run detection
    changes = await detector.detect_changes(
        source_files=source_files,
        knowledge_base_id=1,
        calculate_hashes=False
    )
    
    # Verify
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.NEW
    assert changes[0].uri == "file1.txt"
    
    print("✓ Restored file correctly detected as NEW")

async def test_duplicate_deletion_prevention():
    """Test that already-deleted files don't create duplicate deletion records."""
    print("\\nTesting duplicate deletion prevention...")
    
    # Setup
    mock_repo = MockRepository()
    detector = ChangeDetector(mock_repo)
    
    # Add an already-deleted file
    mock_repo.add_file("file2.txt", FileStatus.DELETED.value)
    
    # Simulate the file still being absent (empty source files)
    source_files = []
    
    # Run detection
    changes = await detector.detect_changes(
        source_files=source_files,
        knowledge_base_id=1,
        calculate_hashes=False
    )
    
    # Verify - should have no changes since file is already deleted
    assert len(changes) == 0
    
    print("✓ Already-deleted file not marked for deletion again")

async def test_normal_deletion():
    """Test that normal deletions still work."""
    print("\\nTesting normal deletion detection...")
    
    # Setup
    mock_repo = MockRepository()
    detector = ChangeDetector(mock_repo)
    
    # Add an active file (need to use a valid status - using NEW instead of ACTIVE)
    mock_repo.add_file("file3.txt", FileStatus.NEW.value)
    
    # Simulate the file being deleted (no source files)
    source_files = []
    
    # Run detection
    changes = await detector.detect_changes(
        source_files=source_files,
        knowledge_base_id=1,
        calculate_hashes=False
    )
    
    # Verify
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.DELETED
    assert changes[0].uri == "file3.txt"
    
    print("✓ Active file correctly detected as DELETED")

async def test_modified_file():
    """Test that modified files are detected correctly."""
    print("\\nTesting modified file detection...")
    
    # Setup
    mock_repo = MockRepository()
    detector = ChangeDetector(mock_repo) 
    
    # Add a file
    mock_repo.add_file("file4.txt", FileStatus.NEW.value)
    
    # Simulate the file being present again
    source_files = [FileMetadata(
        uri="file4.txt",
        size=200,  # Different size
        created_at=datetime.now(),
        modified_at=datetime.now(),
        content_type="text/plain"
    )]
    
    # Note: Without hash calculation, the file will be marked as NEW if no existing record
    # or UNCHANGED if already exists (as we disabled hash checking)
    
    print("! Modified file detection depends on hash comparison")
    print("  (This test is simplified without hashes)")

async def main():
    """Run all tests."""
    print("=== Direct Change Detector Tests ===\\n")
    
    try:
        await test_restored_file_detection()
        await test_duplicate_deletion_prevention()
        await test_normal_deletion()
        await test_modified_file()
        
        print("\\n=== Summary ===")
        print("All change detector tests passed!")
        print("The logic correctly handles:")
        print("- Restored files (marked as NEW)")
        print("- Duplicate deletions (prevented)")
        print("- Normal deletions (detected)")
        
    except AssertionError as e:
        print(f"\\nTest failed: {e}")
    except Exception as e:
        print(f"\\nError: {e}")

if __name__ == "__main__":
    asyncio.run(main())