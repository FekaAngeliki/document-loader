#!/usr/bin/env python3
"""
Test script to verify SharePoint folder hierarchy preservation functionality.

This script tests the _extract_sharepoint_folder_path function to ensure it correctly
extracts folder paths from SharePoint webUrl strings.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.multi_source_batch_runner import MultiSourceBatchRunner
from data.repository import Repository

def test_sharepoint_folder_extraction():
    """Test SharePoint folder path extraction with various URL patterns."""
    
    # Create a minimal batch runner instance for testing
    class MockRepository:
        pass
    
    runner = MultiSourceBatchRunner(MockRepository())
    
    # Test cases with different SharePoint URL patterns
    test_cases = [
        {
            "url": "https://groupnbg.sharepoint.com/sites/div991secb/Έγγραφα/Policy_Manual.pdf",
            "expected": "",  # Root level file
            "description": "Root level file in library"
        },
        {
            "url": "https://groupnbg.sharepoint.com/sites/div991secb/Έγγραφα/HR/Employee_Handbook.pdf",
            "expected": "HR",
            "description": "File in HR subfolder"
        },
        {
            "url": "https://groupnbg.sharepoint.com/sites/div991secb/Έγγραφα/HR/Policies/Benefits/Health_Insurance.pdf",
            "expected": "HR/Policies/Benefits",
            "description": "File in nested subfolder structure"
        },
        {
            "url": "https://groupnbg.sharepoint.com/sites/div991secb/Shared%20Documents/Archive/2023/Q1/Report.docx",
            "expected": "Archive/2023/Q1",
            "description": "File with URL encoding and nested folders"
        },
        {
            "url": "https://example.com/not-sharepoint/file.pdf",
            "expected": "",
            "description": "Non-SharePoint URL should return empty"
        }
    ]
    
    print("Testing SharePoint folder hierarchy extraction")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = runner._extract_sharepoint_folder_path(test_case["url"])
            expected = test_case["expected"]
            
            if result == expected:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
                failed += 1
            
            print(f"Test {i}: {status}")
            print(f"  Description: {test_case['description']}")
            print(f"  URL: {test_case['url']}")
            print(f"  Expected: '{expected}'")
            print(f"  Got: '{result}'")
            print()
            
        except Exception as e:
            print(f"Test {i}: ❌ ERROR")
            print(f"  Description: {test_case['description']}")
            print(f"  Error: {e}")
            print()
            failed += 1
    
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0

def test_filename_generation():
    """Test complete filename generation with different configurations."""
    
    class MockRepository:
        pass
    
    runner = MultiSourceBatchRunner(MockRepository())
    
    test_configs = [
        {
            "config": {
                "naming_convention": "{source_id}/{uuid}{extension}",
                "folder_structure": "source_based"
            },
            "description": "Flat structure (current default)"
        },
        {
            "config": {
                "naming_convention": "{source_id}/{uuid}{extension}",
                "folder_structure": "preserve_hierarchy"
            },
            "description": "Hierarchical structure with basic naming"
        },
        {
            "config": {
                "naming_convention": "{source_id}/{folder_path}/{uuid}{extension}",
                "folder_structure": "preserve_hierarchy"
            },
            "description": "Hierarchical with explicit folder path in naming"
        },
        {
            "config": {
                "naming_convention": "{source_id}/{folder_path}/{original_name}_{uuid}{extension}",
                "folder_structure": "preserve_hierarchy"
            },
            "description": "Hierarchical with original name preservation"
        }
    ]
    
    test_url = "https://groupnbg.sharepoint.com/sites/div991secb/Έγγραφα/HR/Policies/Employee_Handbook.pdf"
    source_id = "Sharepoint_1"
    
    print("\nTesting filename generation with different configurations")
    print("=" * 60)
    print(f"Test URL: {test_url}")
    print(f"Source ID: {source_id}")
    print()
    
    for i, test_config in enumerate(test_configs, 1):
        try:
            # Mock UUID for consistent testing
            import uuid
            original_uuid4 = uuid.uuid4
            uuid.uuid4 = lambda: type('MockUUID', (), {'__str__': lambda self: 'test-uuid-1234'})()
            
            result = runner._generate_source_filename(
                source_id=source_id,
                original_uri=test_url,
                file_organization=test_config["config"]
            )
            
            # Restore original uuid function
            uuid.uuid4 = original_uuid4
            
            print(f"Config {i}: {test_config['description']}")
            print(f"  Result: {result}")
            print()
            
        except Exception as e:
            print(f"Config {i}: ❌ ERROR")
            print(f"  Description: {test_config['description']}")
            print(f"  Error: {e}")
            print()

if __name__ == "__main__":
    print("SharePoint Folder Hierarchy Test Suite")
    print("=" * 60)
    
    # Run tests
    folder_test_passed = test_sharepoint_folder_extraction()
    test_filename_generation()
    
    if folder_test_passed:
        print("\n🎉 All folder extraction tests passed!")
    else:
        print("\n❌ Some tests failed. Check output above.")
    
    print("\n💡 To test with real SharePoint data:")
    print("   document-loader multi-source sync-multi-kb --config-name premium-rms-hierarchy-example")