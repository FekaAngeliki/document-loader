#!/usr/bin/env python3
"""
Test script to validate Azure Blob RAG configuration structure
"""
import asyncio
import logging
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.implementations.azure_blob_rag_config import (
    AzureBlobRAGConfig,
    AzureBlobConfig,
    AzureSearchConfig,
    AzureServicePrincipalAuth,
    AzureResourceConfig,
    AzureAuthMethod,
    AzureStorageRedundancy
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_config_creation():
    """Test creating various Azure Blob RAG configurations"""
    print("\n=== Testing Configuration Creation ===")
    
    # Test 1: Basic service principal config
    print("\n1. Basic Service Principal Configuration:")
    try:
        config1 = AzureBlobRAGConfig(
            auth_method=AzureAuthMethod.SERVICE_PRINCIPAL,
            service_principal=AzureServicePrincipalAuth(
                tenant_id="test-tenant",
                client_id="test-client",
                client_secret="test-secret",
                subscription_id="test-subscription"
            ),
            blob_config=AzureBlobConfig(
                container_name="test-container",
                storage_account_name="testaccount"
            ),
            resource_config=AzureResourceConfig(
                resource_group_name="test-rg",
                location="eastus"
            )
        )
        print("✓ Created successfully")
        print(f"  Container: {config1.blob_config.container_name}")
        print(f"  Storage Account: {config1.blob_config.storage_account_name}")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 2: Connection string config
    print("\n2. Connection String Configuration:")
    try:
        config2 = AzureBlobRAGConfig(
            auth_method=AzureAuthMethod.CONNECTION_STRING,
            connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=key;EndpointSuffix=core.windows.net",
            blob_config=AzureBlobConfig(
                container_name="test-container",
                storage_account_name="testaccount"
            )
        )
        print("✓ Created successfully")
        print(f"  Auth Method: {config2.auth_method.value}")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 3: Config with Azure Search
    print("\n3. Configuration with Azure Search:")
    try:
        config3 = AzureBlobRAGConfig(
            auth_method=AzureAuthMethod.SERVICE_PRINCIPAL,
            service_principal=AzureServicePrincipalAuth(
                tenant_id="test-tenant",
                client_id="test-client",
                client_secret="test-secret",
                subscription_id="test-subscription"
            ),
            blob_config=AzureBlobConfig(
                container_name="test-container",
                storage_account_name="testaccount"
            ),
            resource_config=AzureResourceConfig(
                resource_group_name="test-rg",
                location="westus2"
            ),
            search_config=AzureSearchConfig(
                endpoint="https://testsearch.search.windows.net",
                api_key="test-api-key",
                index_name="test-index",
                enable_semantic_search=True
            )
        )
        print("✓ Created successfully")
        print(f"  Search Endpoint: {config3.search_config.endpoint}")
        print(f"  Search Index: {config3.search_config.index_name}")
    except Exception as e:
        print(f"✗ Failed: {e}")

def test_config_serialization():
    """Test configuration serialization and deserialization"""
    print("\n=== Testing Configuration Serialization ===")
    
    # Create a config
    original_config = AzureBlobRAGConfig(
        auth_method=AzureAuthMethod.SERVICE_PRINCIPAL,
        service_principal=AzureServicePrincipalAuth(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            subscription_id="test-subscription"
        ),
        blob_config=AzureBlobConfig(
            container_name="test-container",
            storage_account_name="testaccount",
            enable_versioning=True,
            public_access_level="private"
        ),
        resource_config=AzureResourceConfig(
            resource_group_name="test-rg",
            location="centralus",
            storage_redundancy=AzureStorageRedundancy.GRS
        ),
        max_concurrent_uploads=10,
        blob_tier="cool"
    )
    
    # Convert to dict
    config_dict = original_config.to_dict()
    print("1. Converted to dictionary:")
    print(json.dumps(config_dict, indent=2)[:200] + "...")
    
    # Convert back from dict
    restored_config = AzureBlobRAGConfig.from_dict(config_dict)
    print("\n2. Restored from dictionary:")
    print(f"  Auth Method: {restored_config.auth_method.value}")
    print(f"  Container: {restored_config.blob_config.container_name}")
    print(f"  Location: {restored_config.resource_config.location}")
    print(f"  Redundancy: {restored_config.resource_config.storage_redundancy.value}")
    
    # Verify they match
    if original_config.to_dict() == restored_config.to_dict():
        print("\n✓ Serialization/deserialization successful!")
    else:
        print("\n✗ Serialization/deserialization mismatch!")

def test_config_validation():
    """Test configuration validation"""
    print("\n=== Testing Configuration Validation ===")
    
    # Test 1: Missing required auth for connection string
    print("\n1. Testing missing connection string:")
    try:
        config = AzureBlobRAGConfig(
            auth_method=AzureAuthMethod.CONNECTION_STRING,
            # Missing connection_string
            blob_config=AzureBlobConfig(
                container_name="test",
                storage_account_name="test"
            )
        )
        # This should be caught during initialization in the actual implementation
        print("✗ Should have failed validation")
    except Exception as e:
        print(f"✓ Correctly caught error: {e}")
    
    # Test 2: Invalid storage redundancy
    print("\n2. Testing invalid storage redundancy:")
    try:
        config_dict = {
            "auth_method": "service_principal",
            "service_principal": {
                "tenant_id": "test",
                "client_id": "test",
                "client_secret": "test",
                "subscription_id": "test"
            },
            "blob_config": {
                "container_name": "test",
                "storage_account_name": "test"
            },
            "resource_config": {
                "resource_group_name": "test",
                "location": "eastus",
                "storage_redundancy": "INVALID_VALUE"
            }
        }
        config = AzureBlobRAGConfig.from_dict(config_dict)
        print("✗ Should have failed validation")
    except Exception as e:
        print(f"✓ Correctly caught error: {e}")

def test_environment_variable_fallback():
    """Test configuration with environment variable fallback"""
    print("\n=== Testing Environment Variable Fallback ===")
    
    config_dict = {
        "auth_method": "service_principal",
        "service_principal": {
            # These will use environment variables if None
            "tenant_id": None,
            "client_id": None,
            "client_secret": None,
            "subscription_id": None
        },
        "blob_config": {
            "container_name": "test",
            "storage_account_name": "test"
        }
    }
    
    try:
        config = AzureBlobRAGConfig.from_dict(config_dict)
        print("✓ Configuration created with None values (will use env vars)")
        print(f"  Service Principal: {config.service_principal}")
    except Exception as e:
        print(f"Error: {e}")

def test_advanced_configurations():
    """Test advanced configuration scenarios"""
    print("\n=== Testing Advanced Configurations ===")
    
    # Test 1: Full configuration with all options
    print("\n1. Full configuration with all options:")
    full_config = {
        "auth_method": "service_principal",
        "service_principal": {
            "tenant_id": "test-tenant",
            "client_id": "test-client",
            "client_secret": "test-secret",
            "subscription_id": "test-subscription"
        },
        "blob_config": {
            "container_name": "rag-documents",
            "storage_account_name": "ragstorageaccount",
            "public_access_level": "private",
            "enable_versioning": True,
            "enable_soft_delete": True,
            "soft_delete_retention_days": 14
        },
        "resource_config": {
            "resource_group_name": "rag-resource-group",
            "location": "centralus",
            "storage_redundancy": "Standard_RAGRS"
        },
        "search_config": {
            "endpoint": "https://ragsearch.search.windows.net",
            "api_key": "search-api-key",
            "index_name": "rag-documents-index",
            "enable_semantic_search": True,
            "use_skillset": True,
            "skillset_name": "rag-document-skillset"
        },
        "max_concurrent_uploads": 8,
        "max_upload_retry_attempts": 5,
        "upload_timeout_seconds": 600,
        "blob_tier": "hot",
        "enable_blob_indexing": True
    }
    
    try:
        config = AzureBlobRAGConfig.from_dict(full_config)
        print("✓ Full configuration created successfully")
        print(f"  Blob Tier: {config.blob_tier}")
        print(f"  Soft Delete Days: {config.blob_config.soft_delete_retention_days}")
        print(f"  Semantic Search: {config.search_config.enable_semantic_search}")
        print(f"  Max Concurrent Uploads: {config.max_concurrent_uploads}")
    except Exception as e:
        print(f"✗ Failed: {e}")

def main():
    """Run all tests"""
    print("Azure Blob RAG Configuration Test Suite")
    print("=====================================")
    
    test_config_creation()
    test_config_serialization()
    test_config_validation()
    test_environment_variable_fallback()
    test_advanced_configurations()
    
    print("\n=== Test Suite Complete ===")

if __name__ == "__main__":
    main()