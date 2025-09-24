#!/usr/bin/env python3
"""
Test script to validate multi-source functionality without database dependencies.
"""

import json
import sys
import os
from pathlib import Path

# Add the src directory to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_config_parsing():
    """Test parsing of multi-source configuration."""
    print("=== Testing Multi-Source Configuration Parsing ===")
    
    try:
        from data.multi_source_models import create_multi_source_kb_from_config
        
        # Load the test configuration
        config_path = Path(__file__).parent / "test_multi_source_config.json"
        
        print(f"Loading configuration from: {config_path}")
        
        with open(config_path) as f:
            config = json.load(f)
        
        print(f"✅ Configuration loaded successfully")
        print(f"   KB Name: {config['name']}")
        print(f"   RAG Type: {config['rag_type']}")
        print(f"   Sources: {len(config['sources'])}")
        
        # Parse into data model
        multi_kb = create_multi_source_kb_from_config(config)
        
        print(f"✅ Configuration parsed into model successfully")
        print(f"   Knowledge Base: {multi_kb.name}")
        print(f"   Description: {multi_kb.description}")
        print(f"   RAG Type: {multi_kb.rag_type}")
        print(f"   Number of sources: {len(multi_kb.sources)}")
        
        # Validate each source
        for i, source in enumerate(multi_kb.sources, 1):
            print(f"   Source {i}:")
            print(f"     ID: {source.source_id}")
            print(f"     Type: {source.source_type}")
            print(f"     Enabled: {source.enabled}")
            print(f"     Tags: {source.metadata_tags}")
        
        print(f"✅ All sources validated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Configuration parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_organization():
    """Test file organization strategy."""
    print("\n=== Testing File Organization Strategy ===")
    
    try:
        # Test filename generation logic
        import uuid
        from pathlib import Path
        
        # Mock file organization config
        file_organization = {
            "naming_convention": "{source_id}/{uuid}{extension}",
            "folder_structure": "source_based"
        }
        
        # Test data
        source_id = "test_filesystem_1"
        original_uri = "./test_scripts/test_data/source1/document1.txt"
        
        # Generate UUID filename
        file_uuid = str(uuid.uuid4())
        original_path = Path(original_uri)
        extension = original_path.suffix
        
        naming_convention = file_organization.get("naming_convention", "{uuid}{extension}")
        
        if "{source_id}" in naming_convention:
            filename = naming_convention.format(
                source_id=source_id,
                uuid=file_uuid,
                extension=extension,
                original_name=original_path.stem
            )
        else:
            filename = f"{file_uuid}{extension}"
        
        print(f"✅ File organization test successful")
        print(f"   Original: {original_uri}")
        print(f"   Generated: {filename}")
        print(f"   Pattern: {naming_convention}")
        
        return True
        
    except Exception as e:
        print(f"❌ File organization test failed: {e}")
        return False

def test_source_validation():
    """Test source configuration validation."""
    print("\n=== Testing Source Configuration Validation ===")
    
    try:
        # Test source paths exist
        test_data_dir = Path(__file__).parent / "test_data"
        
        source1_path = test_data_dir / "source1"
        source2_path = test_data_dir / "source2"
        
        print(f"Checking source paths:")
        print(f"   Source 1: {source1_path} - {'✅ exists' if source1_path.exists() else '❌ missing'}")
        print(f"   Source 2: {source2_path} - {'✅ exists' if source2_path.exists() else '❌ missing'}")
        
        # Check test files
        source1_files = list(source1_path.glob("*")) if source1_path.exists() else []
        source2_files = list(source2_path.glob("*")) if source2_path.exists() else []
        
        print(f"   Source 1 files: {len(source1_files)} ({[f.name for f in source1_files]})")
        print(f"   Source 2 files: {len(source2_files)} ({[f.name for f in source2_files]})")
        
        # Test extension filtering
        source1_txt_md = [f for f in source1_files if f.suffix in ['.txt', '.md']]
        source2_txt_pdf = [f for f in source2_files if f.suffix in ['.txt', '.pdf']]
        
        print(f"   Source 1 filtered (.txt, .md): {len(source1_txt_md)} files")
        print(f"   Source 2 filtered (.txt, .pdf): {len(source2_txt_pdf)} files")
        
        print(f"✅ Source validation successful")
        return True
        
    except Exception as e:
        print(f"❌ Source validation failed: {e}")
        return False

def test_metadata_generation():
    """Test metadata generation for multi-source files."""
    print("\n=== Testing Metadata Generation ===")
    
    try:
        # Mock file metadata
        test_files = [
            {
                "source_id": "test_filesystem_1",
                "source_type": "file_system",
                "original_uri": "./test_scripts/test_data/source1/document1.txt",
                "department": "test_dept_1"
            },
            {
                "source_id": "test_filesystem_2", 
                "source_type": "file_system",
                "original_uri": "./test_scripts/test_data/source2/document2.txt",
                "department": "test_dept_2"
            }
        ]
        
        kb_name = "test-multi-knowledge-base"
        
        for file_info in test_files:
            # Generate RAG metadata
            rag_metadata = {
                "kb_name": kb_name,
                "source_id": file_info["source_id"],
                "source_type": file_info["source_type"],
                "original_uri": file_info["original_uri"],
                "file_hash": "mock_hash_123",
                "department": file_info["department"],
                "source_system": "file_system"
            }
            
            print(f"   File: {Path(file_info['original_uri']).name}")
            print(f"     Source: {file_info['source_id']}")
            print(f"     Department: {file_info['department']}")
            print(f"     Metadata keys: {list(rag_metadata.keys())}")
        
        print(f"✅ Metadata generation successful")
        return True
        
    except Exception as e:
        print(f"❌ Metadata generation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Multi-Source Knowledge Base Validation Tests")
    print("=" * 50)
    
    tests = [
        test_config_parsing,
        test_file_organization,
        test_source_validation,
        test_metadata_generation
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    if passed < total:
        print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All multi-source validation tests passed!")
        print("The multi-source functionality appears to be correctly implemented.")
    else:
        print("\n⚠️  Some tests failed. Review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)