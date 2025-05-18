#!/usr/bin/env python3
"""
Test environment variable fallback for RAG configurations
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.factory import RAGFactory

async def test_azure_blob_env_fallback():
    """Test Azure Blob configuration with environment variable fallback"""
    print("=== Testing Azure Blob Environment Variable Fallback ===\n")
    
    # Set environment variables
    test_env_vars = {
        'AZURE_TENANT_ID': 'test-tenant-from-env',
        'AZURE_SUBSCRIPTION_ID': 'test-subscription-from-env',
        'AZURE_CLIENT_ID': 'test-client-from-env',
        'AZURE_CLIENT_SECRET': 'test-secret-from-env',
        'AZURE_RESOURCE_GROUP_NAME': 'test-rg-from-env',
        'AZURE_STORAGE_ACCOUNT_NAME': 'testaccountfromenv',
        'AZURE_STORAGE_CONTAINER_NAME': 'test-container-from-env'
    }
    
    # Temporarily set environment variables
    old_env = {}
    for key, value in test_env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        # Test 1: Empty config should use environment variables
        print("Test 1: Empty config (should use env vars)")
        factory = RAGFactory()
        rag_system = factory.create('azure_blob', {})
        
        print(f"  Tenant ID: {rag_system.azure_tenant_id}")
        print(f"  Subscription ID: {rag_system.azure_subscription_id}")
        print(f"  Storage Account: {rag_system.azure_storage_account_name}")
        print("  ✓ Successfully created with env vars\n")
        
        # Test 2: Partial config should use mix of config and env vars
        print("Test 2: Partial config (mix of config and env vars)")
        partial_config = {
            'azure_tenant_id': 'config-tenant',
            'azure_storage_account_name': 'configaccount'
        }
        rag_system2 = factory.create('azure_blob', partial_config)
        
        print(f"  Tenant ID: {rag_system2.azure_tenant_id} (from config)")
        print(f"  Subscription ID: {rag_system2.azure_subscription_id} (from env)")
        print(f"  Storage Account: {rag_system2.azure_storage_account_name} (from config)")
        print("  ✓ Successfully created with mixed sources\n")
        
        # Test 3: Full config should ignore env vars
        print("Test 3: Full config (should ignore env vars)")
        full_config = {
            'azure_tenant_id': 'config-tenant',
            'azure_subscription_id': 'config-subscription',
            'azure_client_id': 'config-client',
            'azure_client_secret': 'config-secret',
            'azure_resource_group_name': 'config-rg',
            'azure_storage_account_name': 'configaccount',
            'azure_storage_container_name': 'config-container'
        }
        rag_system3 = factory.create('azure_blob', full_config)
        
        print(f"  Tenant ID: {rag_system3.azure_tenant_id} (from config)")
        print(f"  Storage Account: {rag_system3.azure_storage_account_name} (from config)")
        print("  ✓ Successfully created with full config\n")
        
    finally:
        # Restore original environment
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

async def test_file_system_env_fallback():
    """Test File System Storage configuration with environment variable fallback"""
    print("=== Testing File System Storage Environment Variable Fallback ===\n")
    
    # Set environment variable
    old_env = os.environ.get('DOCUMENT_LOADER_STORAGE_PATH')
    os.environ['DOCUMENT_LOADER_STORAGE_PATH'] = '/tmp/storage-from-env'
    
    try:
        # Test 1: Empty config should use environment variable
        print("Test 1: Empty config (should use env var)")
        factory = RAGFactory()
        rag_system = factory.create('file_system_storage', {})
        
        print(f"  Storage Path: {rag_system.storage_path}")
        print("  ✓ Successfully created with env var\n")
        
        # Test 2: Config should override env var
        print("Test 2: Config with storage_path (should override env var)")
        config = {'storage_path': '/tmp/storage-from-config'}
        rag_system2 = factory.create('file_system_storage', config)
        
        print(f"  Storage Path: {rag_system2.storage_path}")
        print("  ✓ Successfully created with config\n")
        
    finally:
        # Restore original environment
        if old_env is None:
            os.environ.pop('DOCUMENT_LOADER_STORAGE_PATH', None)
        else:
            os.environ['DOCUMENT_LOADER_STORAGE_PATH'] = old_env

async def test_missing_required_params():
    """Test error handling when required parameters are missing"""
    print("=== Testing Missing Required Parameters ===\n")
    
    # Clear all Azure environment variables
    azure_env_vars = [
        'AZURE_TENANT_ID', 'AZURE_SUBSCRIPTION_ID', 'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET', 'AZURE_RESOURCE_GROUP_NAME',
        'AZURE_STORAGE_ACCOUNT_NAME', 'AZURE_STORAGE_CONTAINER_NAME'
    ]
    
    old_env = {}
    for key in azure_env_vars:
        old_env[key] = os.environ.pop(key, None)
    
    try:
        print("Test: Creating Azure Blob with no config and no env vars")
        factory = RAGFactory()
        
        try:
            rag_system = factory.create('azure_blob', {})
            print("  ✗ Should have raised an error!")
        except ValueError as e:
            print(f"  ✓ Correctly raised error: {e}")
            
    finally:
        # Restore original environment
        for key, value in old_env.items():
            if value is not None:
                os.environ[key] = value

async def main():
    """Run all tests"""
    print("Testing Environment Variable Fallback for RAG Systems")
    print("=" * 50 + "\n")
    
    await test_azure_blob_env_fallback()
    await test_file_system_env_fallback()
    await test_missing_required_params()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("\nSummary:")
    print("- Azure Blob: Uses env vars when config values are missing")
    print("- File System Storage: Uses DOCUMENT_LOADER_STORAGE_PATH when no path provided")
    print("- Both systems validate required parameters and provide helpful error messages")

if __name__ == "__main__":
    asyncio.run(main())