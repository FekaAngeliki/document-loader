#!/usr/bin/env python3
"""
Multi-Source Models Test

This script tests the core multi-source data models and configuration
functionality without requiring external dependencies.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_multi_source_kb_creation():
    """Test creating a MultiSourceKnowledgeBase from configuration."""
    try:
        from data.multi_source_models import (
            MultiSourceKnowledgeBase,
            SourceDefinition,
            create_multi_source_kb_from_config
        )
        
        # Test configuration
        config = {
            "name": "test-multi-kb",
            "description": "Test multi-source knowledge base",
            "rag_type": "mock",
            "rag_config": {"storage_path": "/tmp/test"},
            "sources": [
                {
                    "source_id": "hr_docs",
                    "source_type": "file_system",
                    "enabled": True,
                    "source_config": {"root_path": "/hr/docs"},
                    "metadata_tags": {"department": "HR"},
                    "sync_schedule": "0 2 * * *"
                },
                {
                    "source_id": "finance_docs",
                    "source_type": "enterprise_sharepoint",
                    "enabled": True,
                    "source_config": {
                        "site_url": "https://company.sharepoint.com/sites/finance",
                        "client_id": "test-client-id"
                    },
                    "metadata_tags": {"department": "Finance"},
                    "sync_schedule": "0 3 * * *"
                }
            ]
        }
        
        # Test creation from config
        multi_kb = create_multi_source_kb_from_config(config)
        
        # Validate structure
        assert multi_kb.name == "test-multi-kb"
        assert multi_kb.rag_type == "mock"
        assert len(multi_kb.sources) == 2
        
        # Test individual sources
        hr_source = multi_kb.sources[0]
        assert hr_source.source_id == "hr_docs"
        assert hr_source.source_type == "file_system"
        assert hr_source.enabled == True
        assert hr_source.metadata_tags["department"] == "HR"
        
        finance_source = multi_kb.sources[1]
        assert finance_source.source_id == "finance_docs"
        assert finance_source.source_type == "enterprise_sharepoint"
        assert finance_source.metadata_tags["department"] == "Finance"
        
        print("✅ Multi-source KB creation successful")
        print(f"   Created KB: {multi_kb.name}")
        print(f"   Sources: {len(multi_kb.sources)}")
        print(f"   RAG Type: {multi_kb.rag_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Multi-source KB creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_source_definition_validation():
    """Test SourceDefinition validation and functionality."""
    try:
        from data.multi_source_models import SourceDefinition
        
        # Test valid source definition
        source = SourceDefinition(
            source_id="test_source",
            source_type="file_system",
            source_config={"root_path": "/test"},
            metadata_tags={"env": "test", "owner": "team1"},
            sync_schedule="0 1 * * *",
            enabled=True
        )
        
        assert source.source_id == "test_source"
        assert source.source_type == "file_system"
        assert source.enabled == True
        assert source.metadata_tags["env"] == "test"
        
        # Test to_dict functionality
        source_dict = source.to_dict()
        assert source_dict["source_id"] == "test_source"
        assert source_dict["metadata_tags"]["owner"] == "team1"
        
        # Test from_dict functionality
        source2 = SourceDefinition.from_dict(source_dict)
        assert source2.source_id == source.source_id
        assert source2.metadata_tags == source.metadata_tags
        
        print("✅ Source definition validation successful")
        print(f"   Source ID: {source.source_id}")
        print(f"   Type: {source.source_type}")
        print(f"   Tags: {source.metadata_tags}")
        
        return True
        
    except Exception as e:
        print(f"❌ Source definition validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_file_record():
    """Test EnhancedFileRecord functionality."""
    try:
        from data.multi_source_models import EnhancedFileRecord
        
        # Test enhanced file record creation
        record = EnhancedFileRecord(
            original_uri="/path/to/file.pdf",
            rag_uri="rag://kb1/uuid123.pdf",
            file_hash="sha256hash",
            size=1024,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            modified_at=datetime(2024, 1, 2, 12, 0, 0),
            content_type="application/pdf",
            source_id="hr_docs",
            source_type="file_system",
            source_metadata={"department": "HR", "confidential": True}
        )
        
        assert record.original_uri == "/path/to/file.pdf"
        assert record.source_id == "hr_docs"
        assert record.source_type == "file_system"
        assert record.source_metadata["department"] == "HR"
        assert record.source_metadata["confidential"] == True
        
        # Test dict conversion
        record_dict = record.to_dict()
        assert record_dict["source_id"] == "hr_docs"
        assert record_dict["source_metadata"]["department"] == "HR"
        
        print("✅ Enhanced file record successful")
        print(f"   URI: {record.original_uri}")
        print(f"   Source: {record.source_id}")
        print(f"   Metadata: {record.source_metadata}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced file record failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_json_serialization():
    """Test JSON serialization of multi-source models."""
    try:
        from data.multi_source_models import (
            MultiSourceKnowledgeBase,
            SourceDefinition,
            create_multi_source_kb_from_config
        )
        
        # Create test KB
        config = {
            "name": "json-test-kb",
            "description": "JSON serialization test",
            "rag_type": "mock",
            "rag_config": {},
            "sources": [
                {
                    "source_id": "test_source",
                    "source_type": "file_system",
                    "source_config": {"root_path": "/test"},
                    "metadata_tags": {"test": True}
                }
            ]
        }
        
        multi_kb = create_multi_source_kb_from_config(config)
        
        # Test serialization to dict
        kb_dict = multi_kb.to_dict()
        assert "name" in kb_dict
        assert "sources" in kb_dict
        assert len(kb_dict["sources"]) == 1
        
        # Test JSON serialization
        json_str = json.dumps(kb_dict, indent=2, default=str)
        assert "json-test-kb" in json_str
        assert "test_source" in json_str
        
        # Test deserialization
        parsed_dict = json.loads(json_str)
        assert parsed_dict["name"] == "json-test-kb"
        
        print("✅ JSON serialization successful")
        print(f"   KB serialized successfully")
        print(f"   JSON length: {len(json_str)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_template():
    """Test creating configuration templates."""
    try:
        from data.multi_source_models import create_multi_source_kb_from_config
        
        # Test minimal configuration
        minimal_config = {
            "name": "minimal-kb",
            "rag_type": "mock",
            "rag_config": {},
            "sources": []
        }
        
        kb = create_multi_source_kb_from_config(minimal_config)
        assert kb.name == "minimal-kb"
        assert len(kb.sources) == 0
        
        # Test configuration with enterprise SharePoint
        enterprise_config = {
            "name": "enterprise-kb",
            "description": "Enterprise multi-source KB",
            "rag_type": "azure_blob",
            "rag_config": {
                "azure_storage_account_name": "mystorageaccount",
                "azure_storage_container_name": "documents"
            },
            "sources": [
                {
                    "source_id": "hr_sharepoint",
                    "source_type": "enterprise_sharepoint",
                    "source_config": {
                        "site_url": "https://company.sharepoint.com/sites/hr",
                        "client_id": "${AZURE_CLIENT_ID}",
                        "client_secret": "${AZURE_CLIENT_SECRET}",
                        "tenant_id": "${AZURE_TENANT_ID}"
                    },
                    "metadata_tags": {
                        "department": "HR",
                        "content_type": "policies"
                    }
                },
                {
                    "source_id": "finance_sharepoint",
                    "source_type": "enterprise_sharepoint",
                    "source_config": {
                        "site_url": "https://company.sharepoint.com/sites/finance",
                        "client_id": "${AZURE_CLIENT_ID}",
                        "client_secret": "${AZURE_CLIENT_SECRET}",
                        "tenant_id": "${AZURE_TENANT_ID}"
                    },
                    "metadata_tags": {
                        "department": "Finance",
                        "content_type": "reports"
                    }
                }
            ],
            "file_organization": {
                "naming_convention": "{source_id}/{department}/{uuid}{extension}",
                "folder_structure": "source_based"
            },
            "sync_strategy": {
                "default_mode": "parallel",
                "batch_size": 10
            }
        }
        
        enterprise_kb = create_multi_source_kb_from_config(enterprise_config)
        assert enterprise_kb.name == "enterprise-kb"
        assert len(enterprise_kb.sources) == 2
        assert enterprise_kb.rag_type == "azure_blob"
        
        hr_source = next(s for s in enterprise_kb.sources if s.source_id == "hr_sharepoint")
        assert hr_source.source_type == "enterprise_sharepoint"
        assert hr_source.metadata_tags["department"] == "HR"
        
        print("✅ Configuration template successful")
        print(f"   Minimal KB: {kb.name}")
        print(f"   Enterprise KB: {enterprise_kb.name} with {len(enterprise_kb.sources)} sources")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration template failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_model_tests():
    """Run all model tests."""
    print("Multi-Source Models Test")
    print("=" * 40)
    
    tests = [
        ("Multi-Source KB Creation", test_multi_source_kb_creation),
        ("Source Definition Validation", test_source_definition_validation),
        ("Enhanced File Record", test_enhanced_file_record),
        ("JSON Serialization", test_json_serialization),
        ("Configuration Template", test_configuration_template),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*40)
    print("MODEL TEST SUMMARY")
    print("="*40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All model tests passed!")
        print("✅ Multi-source data models are working correctly")
        print("✅ Configuration parsing and validation work")
        print("✅ JSON serialization works")
        return True
    else:
        print(f"\n⚠️  {total - passed} model tests failed.")
        print("Core data models need fixes before proceeding.")
        return False

if __name__ == "__main__":
    success = run_model_tests()
    
    if success:
        print("\n🎯 Multi-source models are working!")
        print("Core data structures are ready for functional testing.")
        sys.exit(0)
    else:
        print("\n⚠️  Model issues found. Check the errors above.")
        sys.exit(1)