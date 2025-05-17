#!/usr/bin/env python3
"""Test to prevent duplicate deletion records."""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

class FileStatus(Enum):
    NEW = "new"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    DELETED = "deleted"

class ChangeType(Enum):
    NEW = "new"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    DELETED = "deleted"

class FileMetadata:
    def __init__(self, uri: str):
        self.uri = uri
        self.size = 1000
        self.modified_at = datetime.now()

class FileRecord:
    def __init__(self, uri: str, status: str, file_hash: str):
        self.original_uri = uri
        self.status = status
        self.file_hash = file_hash
        self.rag_uri = f"test/{uri.split('/')[-1]}"
        self.uuid_filename = f"{uri.split('/')[-1]}.uuid"

class FileChange:
    def __init__(self, uri: str, change_type: ChangeType, metadata=None, existing_record=None):
        self.uri = uri
        self.change_type = change_type
        self.metadata = metadata
        self.existing_record = existing_record

# Simulate the fixed change detection logic
async def detect_changes(source_files: List[FileMetadata], existing_records: Dict[str, FileRecord]):
    """Simulate change detection with duplicate deletion prevention."""
    changes = []
    source_uris = {file.uri for file in source_files}
    source_files_map = {file.uri: file for file in source_files}
    
    # Detect new and modified files
    for uri, metadata in source_files_map.items():
        if uri not in existing_records:
            # New file
            changes.append(FileChange(
                uri=uri,
                change_type=ChangeType.NEW,
                metadata=metadata
            ))
        else:
            # Existing file - check if it was deleted
            existing_record = existing_records[uri]
            
            # If the latest record shows the file was deleted, treat it as new (restored)
            if existing_record.status == FileStatus.DELETED.value:
                changes.append(FileChange(
                    uri=uri,
                    change_type=ChangeType.NEW,
                    metadata=metadata,
                    existing_record=existing_record
                ))
                print(f"  ✨ RESTORED: {uri} (was deleted, now treated as new)")
            else:
                # For existing non-deleted files, mark as potentially modified
                changes.append(FileChange(
                    uri=uri,
                    change_type=ChangeType.MODIFIED,
                    metadata=metadata,
                    existing_record=existing_record
                ))
                print(f"  📝 MODIFIED: {uri} (will check hash)")
    
    # Detect deleted files
    for uri, existing_record in existing_records.items():
        if uri not in source_uris:
            # Only mark as deleted if it's not already marked as deleted
            if existing_record.status != FileStatus.DELETED.value:
                changes.append(FileChange(
                    uri=uri,
                    change_type=ChangeType.DELETED,
                    existing_record=existing_record
                ))
                print(f"  ❌ DELETED: {uri}")
            else:
                print(f"  ⏭️  SKIPPED: {uri} (already marked as deleted)")
    
    return changes

async def main():
    print("=== Test Duplicate Deletion Prevention ===\n")
    
    # Scenario 1: First deletion
    print("Scenario 1: First deletion")
    source_files = []  # File no longer exists
    existing_records = {
        "/path/to/file1.txt": FileRecord("/path/to/file1.txt", FileStatus.NEW.value, "hash1")
    }
    
    changes = await detect_changes(source_files, existing_records)
    print(f"Changes: {[f'{c.uri} ({c.change_type.value})' for c in changes]}\n")
    
    # Scenario 2: Already deleted - should NOT create another deleted record
    print("Scenario 2: Already deleted - should NOT create another deleted record")
    source_files = []  # File still doesn't exist
    existing_records = {
        "/path/to/file1.txt": FileRecord("/path/to/file1.txt", FileStatus.DELETED.value, "hash1")
    }
    
    changes = await detect_changes(source_files, existing_records)
    print(f"Changes: {[f'{c.uri} ({c.change_type.value})' for c in changes]}\n")
    
    # Scenario 3: Your actual case - already deleted file
    print("Scenario 3: Your actual case - agentic-mesh file already deleted")
    source_files = []  # File doesn't exist
    existing_records = {
        "/Users/giorgosmarinos/Documents/scrapper-output/agentic-mesh-enterprise-grade-agents.md": 
        FileRecord(
            "/Users/giorgosmarinos/Documents/scrapper-output/agentic-mesh-enterprise-grade-agents.md",
            FileStatus.DELETED.value,
            "02757bd38b60071e7a27ace835c96d65a73c506310db694d32ac04627973c6dd"
        )
    }
    
    changes = await detect_changes(source_files, existing_records)
    print(f"Changes: {[f'{c.uri} ({c.change_type.value})' for c in changes]}")
    print("Result: No new deletion record should be created")

if __name__ == "__main__":
    asyncio.run(main())