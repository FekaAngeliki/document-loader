#!/usr/bin/env python3
"""
Test script for validation implementation.

Tests the validation logic for create-kb and create-db operations.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.validators import validate_kb_creation, validate_db_creation, ValidationResult
from src.data.database import Database, DatabaseConfig
from src.data.repository import Repository


async def test_kb_validation():
    """Test knowledge base validation logic."""
    print("Testing Knowledge Base Validation...")
    print("=" * 50)
    
    # Test valid configuration
    print("\n1. Testing VALID configuration:")
    valid_config = {
        "name": "test-kb-validation",
        "description": "Test knowledge base for validation",
        "rag_type": "mock",
        "rag_config": {},
        "sources": [{
            "source_id": "test_source_1",
            "source_type": "file_system",
            "source_config": {
                "base_path": "/tmp"  # This should exist
            },
            "metadata_tags": {
                "source_system": "file_system",
                "test": "validation"
            }
        }]
    }
    
    try:
        # Get database connection
        config = DatabaseConfig()
        db = Database(config)
        await db.connect()
        repository = Repository(db)
        
        result = await validate_kb_creation(valid_config, repository)
        
        print(f"Validation result: {'✅ PASSED' if result.is_valid else '❌ FAILED'}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error.field}: {error.message}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning.field}: {warning.message}")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
    
    # Test invalid configuration
    print("\n2. Testing INVALID configuration:")
    invalid_config = {
        "name": "",  # Invalid: empty name
        "description": "Test knowledge base for validation",
        "rag_type": "invalid_rag_type",  # Invalid: non-existent RAG type
        "rag_config": {},
        "sources": [{
            "source_id": "test_source_1",
            "source_type": "invalid_source_type",  # Invalid: non-existent source type
            "source_config": {},  # Invalid: missing required fields
            "metadata_tags": {}
        }]
    }
    
    try:
        config = DatabaseConfig()
        db = Database(config)
        await db.connect()
        repository = Repository(db)
        
        result = await validate_kb_creation(invalid_config, repository)
        
        print(f"Validation result: {'✅ PASSED' if result.is_valid else '❌ FAILED (expected)'}")
        if result.errors:
            print("Errors (expected):")
            for error in result.errors:
                print(f"  - {error.field}: {error.message}")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")


async def test_db_validation():
    """Test database validation logic."""
    print("\n\nTesting Database Validation...")
    print("=" * 50)
    
    # Test valid database name
    print("\n1. Testing VALID database name:")
    try:
        config = DatabaseConfig()
        result = await validate_db_creation("test_validation_db", config)
        
        print(f"Validation result: {'✅ PASSED' if result.is_valid else '❌ FAILED'}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error.field}: {error.message}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning.field}: {warning.message}")
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
    
    # Test invalid database name
    print("\n2. Testing INVALID database names:")
    invalid_names = [
        "",  # Empty
        "123invalid",  # Starts with number
        "invalid-name-with-hyphens",  # Contains hyphens
        "postgres",  # Reserved name
    ]
    
    for invalid_name in invalid_names:
        print(f"\nTesting name: '{invalid_name}'")
        try:
            config = DatabaseConfig()
            result = await validate_db_creation(invalid_name, config)
            
            print(f"  Result: {'✅ PASSED' if result.is_valid else '❌ FAILED (expected)'}")
            if result.errors:
                for error in result.errors:
                    print(f"    - {error.field}: {error.message}")
                    
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")


async def main():
    """Run all validation tests."""
    print("🧪 Validation Implementation Test")
    print("=" * 60)
    
    try:
        await test_kb_validation()
        await test_db_validation()
        
        print("\n" + "=" * 60)
        print("✅ All validation tests completed!")
        print("\nTo test the CLI integration, you can run:")
        print("  document-loader create-kb --help")
        print("  document-loader create-db --help")
        print("\nBoth commands now support --force flag to skip validation.")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())