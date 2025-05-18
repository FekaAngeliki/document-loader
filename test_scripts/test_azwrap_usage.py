#!/usr/bin/env python3
"""
Test different ways to use azwrap for blob containers
"""
import sys
import os

def test_azwrap_patterns():
    """Test different patterns for accessing blob containers in azwrap"""
    print("=== Testing azwrap blob container patterns ===\n")
    
    try:
        # Test 1: Direct imports
        print("Test 1: Direct imports")
        try:
            from azwrap import Identity, Subscription, ResourceGroup, StorageAccount
            print("  ✓ Basic imports successful")
            
            # Check if StorageAccount has container methods
            print("\n  StorageAccount methods related to containers:")
            for attr in dir(StorageAccount):
                if 'container' in attr.lower() or 'blob' in attr.lower():
                    print(f"    - {attr}")
        except ImportError as e:
            print(f"  ✗ Error: {e}")
        
        # Test 2: Check for blob-specific modules
        print("\nTest 2: Blob-specific modules")
        try:
            from azwrap.storage import BlobContainer
            print("  ✓ Found BlobContainer in azwrap.storage")
        except ImportError:
            print("  - BlobContainer not in azwrap.storage")
        
        try:
            from azwrap.blob import BlobContainer
            print("  ✓ Found BlobContainer in azwrap.blob")
        except ImportError:
            print("  - BlobContainer not in azwrap.blob")
        
        # Test 3: Check if it's part of StorageAccount
        print("\nTest 3: Container access through StorageAccount")
        # This is a common pattern in Azure SDKs
        print("  Common patterns:")
        print("    - storage_account.get_blob_container()")
        print("    - storage_account.create_blob_container()")
        print("    - storage_account.list_blob_containers()")
        
        # Test 4: Alternative Azure SDK
        print("\nTest 4: Alternative - Azure Storage Blob SDK")
        try:
            from azure.storage.blob import BlobServiceClient, ContainerClient
            print("  ✓ Azure Storage Blob SDK is available")
            print("    - Use BlobServiceClient for account-level operations")
            print("    - Use ContainerClient for container operations")
        except ImportError:
            print("  - Azure Storage Blob SDK not installed")
            print("    Install with: pip install azure-storage-blob")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_azwrap_patterns()
    
    print("\n=== Recommendation ===")
    print("Based on the error, it seems BlobContainer is not directly importable from azwrap.")
    print("You likely need to:")
    print("1. Use StorageAccount methods to work with containers")
    print("2. Or switch to the official Azure Storage Blob SDK")
    print("3. Or check azwrap documentation for the correct import path")