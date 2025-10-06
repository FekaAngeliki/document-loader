#!/usr/bin/env python3
"""
Simple test script to verify SharePoint folder hierarchy preservation functionality.

This script tests the core folder path extraction logic without dependencies.
"""

import sys
import os
from urllib.parse import urlparse, unquote
from pathlib import Path

def extract_sharepoint_folder_path(sharepoint_url: str) -> str:
    """Extract folder path from SharePoint webUrl, preserving hierarchy."""
    try:
        parsed = urlparse(sharepoint_url)
        path_parts = [unquote(part) for part in parsed.path.split('/') if part]
        
        # SharePoint URL pattern: /sites/sitename/LibraryName/folder1/folder2/file.ext
        if 'sites' in path_parts:
            sites_index = path_parts.index('sites')
            # Skip: sites, sitename, libraryname
            if sites_index + 3 < len(path_parts):
                # Get folder path (everything except the filename)
                folder_parts = path_parts[sites_index + 3:-1]  # -1 to exclude filename
                if folder_parts:
                    return '/'.join(folder_parts)
        
        return ""
    except Exception as e:
        print(f"Error extracting folder path from {sharepoint_url}: {e}")
        return ""

def generate_source_filename(source_id: str, original_uri: str, file_organization: dict) -> str:
    """Generate UUID filename with source organization."""
    import uuid
    
    # Generate base UUID (mock for testing)
    file_uuid = "test-uuid-1234"
    original_path = Path(original_uri)
    extension = original_path.suffix
    
    # Get folder structure setting
    folder_structure = file_organization.get("folder_structure", "source_based")
    
    # Extract folder hierarchy for SharePoint URLs
    folder_path = ""
    if folder_structure == "preserve_hierarchy" and "sharepoint.com" in original_uri:
        folder_path = extract_sharepoint_folder_path(original_uri)
    
    # Apply file organization strategy
    naming_convention = file_organization.get("naming_convention", "{uuid}{extension}")
    
    # Prepare the filename based on convention
    if "{folder_path}" in naming_convention:
        filename = naming_convention.format(
            source_id=source_id,
            uuid=file_uuid,
            extension=extension,
            original_name=original_path.stem,
            folder_path=folder_path
        )
    elif "{source_id}" in naming_convention:
        if folder_path and folder_structure == "preserve_hierarchy":
            # Insert folder path between source_id and uuid
            filename = f"{source_id}/{folder_path}/{file_uuid}{extension}"
        else:
            filename = naming_convention.format(
                source_id=source_id,
                uuid=file_uuid,
                extension=extension,
                original_name=original_path.stem
            )
    else:
        filename = f"{file_uuid}{extension}"
    
    return filename

def test_sharepoint_folder_extraction():
    """Test SharePoint folder path extraction with various URL patterns."""
    
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
            result = extract_sharepoint_folder_path(test_case["url"])
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
            result = generate_source_filename(
                source_id=source_id,
                original_uri=test_url,
                file_organization=test_config["config"]
            )
            
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
    
    print("\n💡 Example configurations:")
    print("  • folder_structure: 'source_based' → Sharepoint_1/uuid.pdf")
    print("  • folder_structure: 'preserve_hierarchy' → Sharepoint_1/HR/Policies/uuid.pdf")
    print("  • naming_convention: '{source_id}/{folder_path}/{original_name}_{uuid}{extension}'")
    print("    → Sharepoint_1/HR/Policies/Employee_Handbook_uuid.pdf")