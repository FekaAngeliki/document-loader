#!/usr/bin/env python
"""
Test all fixes without database dependency.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# Import the components directly
from src.core.change_detector import ChangeDetector, ChangeType
from src.implementations.file_system_storage import FileSystemStorage
from src.abstractions.file_source import FileMetadata
from src.data.models import FileRecord, FileStatus

# Mock Repository
class MockRepository:
    """Mock repository for testing."""
    
    def __init__(self):
        self.files = {}
        self.next_id = 1
        
    async def get_knowledge_base(self, kb_id: int):
        """Mock implementation."""
        return type('MockKnowledgeBase', (), {'id': kb_id, 'name': 'test-kb'})()
    
    async def get_latest_file_records_for_kb(self, kb_name: str):
        """Mock implementation."""
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

async def test_all_fixes():
    """Test all fixes comprehensively."""
    print("=== Testing All Document Loader Fixes ===\n")
    
    # 1. Test restored file detection
    print("1. Testing Restored File Detection...")
    mock_repo = MockRepository()
    detector = ChangeDetector(mock_repo)
    
    # Add a deleted file
    mock_repo.add_file("file1.txt", FileStatus.DELETED.value)
    
    # Simulate the file reappearing
    source_files = [FileMetadata(
        uri="file1.txt",
        size=100,
        created_at=datetime.now(),
        modified_at=datetime.now(),
        content_type="text/plain"
    )]
    
    changes = await detector.detect_changes(
        source_files=source_files,
        knowledge_base_id=1,
        calculate_hashes=False
    )
    
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.NEW
    print("✓ Restored files are correctly detected as NEW")
    
    # 2. Test duplicate deletion prevention
    print("\n2. Testing Duplicate Deletion Prevention...")
    mock_repo2 = MockRepository()
    detector2 = ChangeDetector(mock_repo2)
    
    # Add an already-deleted file
    mock_repo2.add_file("file2.txt", FileStatus.DELETED.value)
    
    # Simulate the file still being absent
    changes2 = await detector2.detect_changes(
        source_files=[],
        knowledge_base_id=1,
        calculate_hashes=False
    )
    
    assert len(changes2) == 0
    print("✓ Already-deleted files don't create duplicate deletion records")
    
    # 3. Test FileSystemStorage URI handling
    print("\n3. Testing FileSystemStorage URI Handling...")
    with tempfile.TemporaryDirectory() as temp_dir:
        config = {
            'root_path': temp_dir,
            'kb_name': 'test-docs',
            'create_dirs': True
        }
        
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        # Test simple URI
        simple_uri = "test-docs/document.txt"
        path = storage._uri_to_path(simple_uri)
        expected = storage.documents_dir / "test-docs/document.txt"
        assert path == expected
        print("✓ Simple URI handling works correctly")
        
        # Test file:// URI
        file_uri = "file:///tmp/test.txt"
        path = storage._uri_to_path(file_uri)
        assert path == Path("/tmp/test.txt")
        print("✓ File URI handling still works")
    
    # 4. Test directory creation
    print("\n4. Testing Directory Creation...")
    with tempfile.TemporaryDirectory() as temp_dir:
        config = {
            'root_path': temp_dir,
            'kb_name': 'test-docs',
            'create_dirs': True
        }
        
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        # Test uploading a file (should create directories)
        test_content = b"Test content"
        test_filename = "test-file.txt"
        metadata = {"test": "value"}
        
        uri = await storage.upload_document(test_content, test_filename, metadata)
        
        # Verify file was created
        file_path = storage._uri_to_path(test_filename)
        assert file_path.exists(), f"File not created at {file_path}"
        print("✓ Directories are created automatically when uploading files")
    
    # 5. Test combined workflow
    print("\n5. Testing Combined Workflow...")
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup
        config = {
            'root_path': temp_dir,
            'kb_name': 'test-docs',
            'create_dirs': True
        }
        
        storage = FileSystemStorage(config)
        await storage.initialize()
        
        # Create a file
        content1 = b"Original content"
        filename1 = "workflow-test.txt"
        metadata1 = {"original": True}
        
        uri1 = await storage.upload_document(content1, filename1, metadata1)
        print(f"  Created file: {uri1}")
        
        # Update the file
        content2 = b"Updated content"
        metadata2 = {"original": False, "updated": True}
        
        await storage.update_document(filename1, content2, metadata2)
        print(f"  Updated file: {filename1}")
        
        # Get metadata to verify update
        doc_metadata = await storage.get_document(filename1)
        assert doc_metadata is not None
        assert doc_metadata.size == len(content2)
        print("  Verified update")
        
        # Delete the file
        await storage.delete_document(filename1)
        print(f"  Deleted file: {filename1}")
        
        # Verify deletion
        doc_metadata = await storage.get_document(filename1)
        assert doc_metadata is None
        print("  Verified deletion")
    
    print("\n=== All Tests Passed! ===")
    print("\nSummary of fixes verified:")
    print("1. Restored files are detected as NEW ✓")
    print("2. Duplicate deletions are prevented ✓")
    print("3. FileSystemStorage handles both URI formats ✓")
    print("4. Directories are created automatically ✓")
    print("5. Complete file lifecycle works correctly ✓")
    print("\nThe document loader is ready for use!")

async def main():
    """Run all tests."""
    try:
        await test_all_fixes()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())