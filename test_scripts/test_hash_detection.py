#!/usr/bin/env python3
"""Test script to demonstrate hash-only change detection."""

import hashlib
from datetime import datetime, timedelta

# Simulate file metadata with timestamps
files = [
    {
        "uri": "/data/file1.txt",
        "content": "Hello World",
        "modified_at": datetime.now(),
        "size": 11
    },
    {
        "uri": "/data/file2.txt", 
        "content": "Test Content",
        "modified_at": datetime.now() - timedelta(days=1),
        "size": 12
    },
    {
        "uri": "/data/file3.txt",
        "content": "Another File",
        "modified_at": datetime.now() - timedelta(hours=6),
        "size": 12
    }
]

# Simulate existing records
existing_records = {
    "/data/file1.txt": {
        "hash": hashlib.sha256("Hello World".encode()).hexdigest(),
        "created_at": datetime.now() - timedelta(days=7),
        "size": 11
    },
    "/data/file2.txt": {
        "hash": hashlib.sha256("Test Content".encode()).hexdigest(),
        "created_at": datetime.now() - timedelta(days=7),
        "size": 12
    }
}

print("=== Hash-Only Change Detection Demo ===\n")

print("Current Files:")
for file in files:
    current_hash = hashlib.sha256(file["content"].encode()).hexdigest()
    print(f"  {file['uri']}")
    print(f"    Content: '{file['content']}'")
    print(f"    Hash: {current_hash[:16]}...")
    print(f"    Modified: {file['modified_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    print()

print("Existing Records:")
for uri, record in existing_records.items():
    print(f"  {uri}")
    print(f"    Hash: {record['hash'][:16]}...")
    print(f"    Created: {record['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    print()

print("Change Detection Results (Hash-Only):")
for file in files:
    current_hash = hashlib.sha256(file["content"].encode()).hexdigest()
    
    if file["uri"] not in existing_records:
        print(f"  ✨ NEW: {file['uri']}")
        print(f"     No existing record found")
    else:
        existing = existing_records[file["uri"]]
        if current_hash == existing["hash"]:
            print(f"  ✅ UNCHANGED: {file['uri']}")
            print(f"     Hash matches (despite timestamp change)")
            print(f"     Old timestamp: {existing['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     New timestamp: {file['modified_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  📝 MODIFIED: {file['uri']}")
            print(f"     Hash mismatch")
    print()

# Demonstrate a real change
print("\n--- Simulating Content Change ---")
files[0]["content"] = "Hello World!"  # Added exclamation
new_hash = hashlib.sha256(files[0]["content"].encode()).hexdigest()
old_hash = existing_records["/data/file1.txt"]["hash"]

print(f"File: {files[0]['uri']}")
print(f"Old content: 'Hello World'")
print(f"New content: '{files[0]['content']}'")
print(f"Old hash: {old_hash[:16]}...")
print(f"New hash: {new_hash[:16]}...")
print(f"Result: {'MODIFIED' if new_hash != old_hash else 'UNCHANGED'}")