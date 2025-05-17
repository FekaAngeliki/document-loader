#!/usr/bin/env python3
"""Test deterministic UUID generation for consistent RAG URIs."""

import os
import hashlib
from pathlib import Path

def generate_uuid_filename(original_filename: str, full_path: str = None) -> str:
    """Generate a deterministic UUID based on the full file path."""
    # Extract file extension
    file_extension = Path(original_filename).suffix
    
    if full_path:
        # Hash the full path to create a deterministic UUID
        path_hash = hashlib.sha256(full_path.encode()).hexdigest()
        uuid_part = f"{path_hash[:8]}-{path_hash[8:12]}-{path_hash[12:16]}-{path_hash[16:20]}-{path_hash[20:32]}"
    else:
        # Fallback to random UUID if no path provided
        import uuid
        uuid_part = str(uuid.uuid4())
    
    return f"{uuid_part}{file_extension}"

def main():
    # Test files with their full paths
    test_files = [
        ("/Users/giorgosmarinos/aiwork/IDP/document-loader/test/data/sample.pdf", "sample.pdf"),
        ("/Users/giorgosmarinos/aiwork/IDP/document-loader/test/data/report.docx", "report.docx"),
        ("/Users/giorgosmarinos/aiwork/IDP/document-loader/test/data/analysis.xlsx", "analysis.xlsx"),
    ]
    
    print("=== Testing Deterministic UUID Generation ===\n")
    
    for full_path, filename in test_files:
        # Generate UUID multiple times to verify consistency
        uuid1 = generate_uuid_filename(filename, full_path)
        uuid2 = generate_uuid_filename(filename, full_path)
        uuid3 = generate_uuid_filename(filename, full_path)
        
        print(f"File: {filename}")
        print(f"Path: {full_path}")
        print(f"UUID 1: {uuid1}")
        print(f"UUID 2: {uuid2}")
        print(f"UUID 3: {uuid3}")
        
        if uuid1 == uuid2 == uuid3:
            print("✅ UUIDs are consistent!")
        else:
            print("❌ UUIDs are DIFFERENT!")
        
        print("-" * 40)
    
    # Test what happens with different paths but same filename
    print("\n=== Testing Different Paths with Same Filename ===\n")
    
    path1 = "/path/one/document.pdf"
    path2 = "/path/two/document.pdf"
    filename = "document.pdf"
    
    uuid_path1 = generate_uuid_filename(filename, path1)
    uuid_path2 = generate_uuid_filename(filename, path2)
    
    print(f"Path 1: {path1}")
    print(f"UUID 1: {uuid_path1}")
    print(f"\nPath 2: {path2}")
    print(f"UUID 2: {uuid_path2}")
    
    if uuid_path1 != uuid_path2:
        print("\n✅ Different paths produce different UUIDs (as expected)")
    else:
        print("\n❌ Different paths produce the SAME UUID (unexpected!)")

if __name__ == "__main__":
    main()