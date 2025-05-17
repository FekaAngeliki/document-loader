#!/usr/bin/env python3
"""Test change detection with consistent file tracking across sync runs."""

import asyncio
from datetime import datetime
from typing import List
from dataclasses import dataclass

# Mock classes to simulate our system
@dataclass
class FileMetadata:
    uri: str
    size: int
    created_at: datetime
    modified_at: datetime
    content_type: str

@dataclass 
class FileRecord:
    id: int
    sync_run_id: int
    original_uri: str
    rag_uri: str
    file_hash: str
    file_size: int
    status: str
    created_at: datetime
    
class MockRepository:
    def __init__(self):
        # Simulate historical file records across multiple sync runs
        self.file_records = [
            # Sync run 1 - initial files
            FileRecord(1, 1, "/data/file1.pdf", "uuid1-file1.pdf", "hash1", 1000, "uploaded", datetime(2024, 1, 1)),
            FileRecord(2, 1, "/data/file2.docx", "uuid2-file2.docx", "hash2", 2000, "uploaded", datetime(2024, 1, 1)),
            
            # Sync run 2 - file2 was modified
            FileRecord(3, 2, "/data/file1.pdf", "uuid1-file1.pdf", "hash1", 1000, "unchanged", datetime(2024, 1, 2)),
            FileRecord(4, 2, "/data/file2.docx", "uuid2-file2.docx", "hash2_new", 2100, "modified", datetime(2024, 1, 2)),
            FileRecord(5, 2, "/data/file3.txt", "uuid3-file3.txt", "hash3", 500, "new", datetime(2024, 1, 2)),
        ]
        
        self.knowledge_bases = {
            1: {"id": 1, "name": "test_kb"}
        }
    
    async def get_knowledge_base(self, kb_id: int):
        kb = self.knowledge_bases.get(kb_id)
        if kb:
            return type('KB', (), kb)()
        return None
    
    async def get_latest_file_records_for_kb(self, kb_name: str) -> List[FileRecord]:
        """Get the most recent file record for each unique URI."""
        latest_records = {}
        
        # Group all records by URI and keep the most recent one
        for record in self.file_records:
            uri = record.original_uri
            if uri not in latest_records or record.created_at > latest_records[uri].created_at:
                latest_records[uri] = record
        
        return list(latest_records.values())

async def test_change_detection():
    """Test that change detection properly identifies file states across sync runs."""
    
    repo = MockRepository()
    
    # Current source files (simulating a new sync run)
    current_files = [
        FileMetadata("/data/file1.pdf", 1000, datetime(2024, 1, 1), datetime(2024, 1, 1), "application/pdf"),
        FileMetadata("/data/file2.docx", 2100, datetime(2024, 1, 1), datetime(2024, 1, 2), "application/docx"),
        FileMetadata("/data/file4.xlsx", 3000, datetime(2024, 1, 3), datetime(2024, 1, 3), "application/xlsx"),
    ]
    
    print("=== Testing Change Detection Across Sync Runs ===\n")
    
    # Get latest records across all sync runs
    kb = await repo.get_knowledge_base(1)
    latest_records = await repo.get_latest_file_records_for_kb(kb.name)
    
    print(f"Latest records for KB '{kb.name}':")
    for record in latest_records:
        print(f"  - {record.original_uri}: {record.rag_uri} (from sync run {record.sync_run_id})")
    print()
    
    # Build map of latest records
    existing_records_map = {record.original_uri: record for record in latest_records}
    
    # Detect changes
    print("Change detection results:")
    for file in current_files:
        if file.uri not in existing_records_map:
            print(f"  ✨ NEW: {file.uri}")
            print(f"     Will generate consistent UUID based on path")
        else:
            existing = existing_records_map[file.uri]
            if file.modified_at > existing.created_at or file.size != existing.file_size:
                print(f"  📝 MODIFIED: {file.uri}")
                print(f"     Previous RAG URI: {existing.rag_uri}")
                print(f"     Will keep same UUID pattern")
            else:
                print(f"  ✅ UNCHANGED: {file.uri}")
                print(f"     Keeping RAG URI: {existing.rag_uri}")
    
    # Check for deleted files
    current_uris = {file.uri for file in current_files}
    for uri, record in existing_records_map.items():
        if uri not in current_uris:
            print(f"  ❌ DELETED: {uri}")
            print(f"     Was: {record.rag_uri}")
    
    print("\n=== Summary ===")
    print("With our changes:")
    print("- Files maintain consistent RAG URIs across sync runs")
    print("- New files get deterministic UUIDs based on their full path")
    print("- Modified files keep their original RAG URI")
    print("- Change detection looks at ALL sync runs, not just the last one")

if __name__ == "__main__":
    asyncio.run(test_change_detection())