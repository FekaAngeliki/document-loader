#!/usr/bin/env python3
"""Test script to demonstrate deleted file handling and reappearance with same RAG URI."""

import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class ChangeType(Enum):
    NEW = "new"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    DELETED = "deleted"

@dataclass
class FileRecord:
    original_uri: str
    rag_uri: str
    file_hash: str
    status: str
    sync_run_id: int
    
@dataclass 
class FileMetadata:
    uri: str
    content: str
    
@dataclass
class FileChange:
    uri: str
    change_type: ChangeType
    existing_record: Optional[FileRecord] = None

def generate_uuid_filename(original_filename: str, full_path: str) -> str:
    """Generate deterministic UUID based on full path."""
    # Extract file extension
    ext = original_filename.split('.')[-1] if '.' in original_filename else ''
    
    # Hash the full path to create a deterministic UUID
    path_hash = hashlib.sha256(full_path.encode()).hexdigest()
    uuid_part = f"{path_hash[:8]}-{path_hash[8:12]}-{path_hash[12:16]}-{path_hash[16:20]}-{path_hash[20:32]}"
    
    return f"{uuid_part}.{ext}" if ext else uuid_part

# Simulate sync runs
print("=== File Deletion and Reappearance Test ===\n")

# Initial state - files exist
print("SYNC RUN 1: Initial files")
initial_files = {
    "/Users/giorgosmarinos/Documents/file1.txt": "Content 1",
    "/Users/giorgosmarinos/Documents/file2.txt": "Content 2",
    "/Users/giorgosmarinos/Documents/file3.txt": "Content 3"
}

existing_records = {}
sync_run_id = 1

for path, content in initial_files.items():
    filename = path.split('/')[-1]
    uuid_filename = generate_uuid_filename(filename, path)
    rag_uri = f"test_kb/{uuid_filename}"
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    
    existing_records[path] = FileRecord(
        original_uri=path,
        rag_uri=rag_uri,
        file_hash=file_hash,
        status="new",
        sync_run_id=sync_run_id
    )
    
    print(f"  NEW: {path}")
    print(f"       RAG URI: {rag_uri}")
    print(f"       Hash: {file_hash[:16]}...")

print("\n" + "="*50 + "\n")

# Second sync run - file2 is deleted
print("SYNC RUN 2: file2.txt is deleted")
current_files = {
    "/Users/giorgosmarinos/Documents/file1.txt": "Content 1",
    "/Users/giorgosmarinos/Documents/file3.txt": "Content 3"
}

sync_run_id = 2
print("Current files:", list(current_files.keys()))
print("\nChange detection:")

# Detect changes
for uri, record in existing_records.items():
    if uri not in current_files:
        print(f"  DELETED: {uri}")
        print(f"           RAG URI: {record.rag_uri}")
        print(f"           Will delete from RAG and mark as deleted in DB")
        
        # Update record to show deletion
        new_record = FileRecord(
            original_uri=uri,
            rag_uri=record.rag_uri,
            file_hash=record.file_hash,
            status="deleted",
            sync_run_id=sync_run_id
        )
        existing_records[uri] = new_record

print("\n" + "="*50 + "\n")

# Third sync run - file2 reappears with same content
print("SYNC RUN 3: file2.txt reappears")
current_files = {
    "/Users/giorgosmarinos/Documents/file1.txt": "Content 1",
    "/Users/giorgosmarinos/Documents/file2.txt": "Content 2",  # Same content
    "/Users/giorgosmarinos/Documents/file3.txt": "Content 3"
}

sync_run_id = 3
print("Current files:", list(current_files.keys()))
print("\nChange detection:")

# Detect changes - file2 should be marked as NEW but get same UUID
for path, content in current_files.items():
    if path not in [r.original_uri for r in existing_records.values() if r.status != "deleted"]:
        # File doesn't exist or was deleted - treat as new
        filename = path.split('/')[-1]
        uuid_filename = generate_uuid_filename(filename, path)
        rag_uri = f"test_kb/{uuid_filename}"
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check if this was previously deleted
        was_deleted = any(r.original_uri == path and r.status == "deleted" 
                         for r in existing_records.values())
        
        if was_deleted:
            previous_record = next(r for r in existing_records.values() 
                                 if r.original_uri == path)
            print(f"  NEW (reappeared): {path}")
            print(f"       Previous RAG URI: {previous_record.rag_uri}")
            print(f"       New RAG URI:      {rag_uri}")
            print(f"       Same URI:         {previous_record.rag_uri == rag_uri}")
        else:
            print(f"  NEW: {path}")
            print(f"       RAG URI: {rag_uri}")

print("\n" + "="*50 + "\n")

# Fourth sync run - file2 reappears with different content
print("SYNC RUN 4: file2.txt reappears with different content")
current_files = {
    "/Users/giorgosmarinos/Documents/file1.txt": "Content 1",
    "/Users/giorgosmarinos/Documents/file2.txt": "Modified Content 2",  # Different content
    "/Users/giorgosmarinos/Documents/file3.txt": "Content 3"
}

sync_run_id = 4
print("Current files:", list(current_files.keys()))
print("\nChange detection:")

for path, content in current_files.items():
    filename = path.split('/')[-1]
    uuid_filename = generate_uuid_filename(filename, path)
    rag_uri = f"test_kb/{uuid_filename}"
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    
    if path == "/Users/giorgosmarinos/Documents/file2.txt":
        print(f"  NEW (reappeared with new content): {path}")
        print(f"       RAG URI: {rag_uri}")
        print(f"       New Hash: {file_hash[:16]}...")
        print(f"       Uses same UUID pattern despite content change")

print("\n=== Summary ===")
print("1. Deleted files are removed from RAG and marked as deleted in database")
print("2. Reappearing files are treated as NEW")
print("3. Reappearing files get the same deterministic UUID based on their full path")
print("4. This preserves the RAG URI structure for files at the same location")