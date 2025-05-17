#!/usr/bin/env python3
"""Migrate files from old structure to new structure"""

import shutil
from pathlib import Path

def migrate_storage(kb_path: str):
    """Migrate files from default/ subdirectory to direct structure"""
    kb_path = Path(kb_path)
    
    # Old structure paths (there are actually two levels of default)
    old_documents = kb_path / "default" / "default" / "documents"
    old_metadata = kb_path / "default" / "default" / "metadata"
    
    # Also check for single level default
    if not old_documents.exists():
        old_documents = kb_path / "default" / "documents"
        old_metadata = kb_path / "default" / "metadata"
    
    # New structure paths
    new_documents = kb_path / "documents"
    new_metadata = kb_path / "metadata"
    
    print(f"Migrating storage structure for: {kb_path}")
    print(f"Old documents: {old_documents}")
    print(f"New documents: {new_documents}")
    
    # Check if old structure exists
    if not old_documents.exists():
        print("Old structure doesn't exist, nothing to migrate")
        return
    
    # Create new directories if they don't exist
    new_documents.mkdir(exist_ok=True)
    new_metadata.mkdir(exist_ok=True)
    
    # Move documents
    if old_documents.exists():
        print(f"\nMoving documents...")
        for file in old_documents.iterdir():
            new_path = new_documents / file.name
            print(f"  {file.name} -> {new_path}")
            shutil.move(str(file), str(new_path))
    
    # Move metadata
    if old_metadata.exists():
        print(f"\nMoving metadata...")
        for file in old_metadata.iterdir():
            new_path = new_metadata / file.name
            print(f"  {file.name} -> {new_path}")
            shutil.move(str(file), str(new_path))
    
    # Remove old directories
    try:
        shutil.rmtree(kb_path / "default")
        print(f"\nRemoved old 'default' directory")
    except Exception as e:
        print(f"Could not remove old directory: {e}")
    
    print("\nMigration complete!")
    
    # Show new structure
    print("\nNew structure:")
    for item in kb_path.iterdir():
        if item.is_dir():
            print(f"  {item.name}/")
            for subitem in item.iterdir():
                print(f"    {subitem.name}")

if __name__ == "__main__":
    # Migrate the test-docs knowledge base
    migrate_storage("/Users/giorgosmarinos/Documents/KBRoot/test-docs")