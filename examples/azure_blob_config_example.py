"""
Azure Blob RAG System Configuration Examples
"""
from src.implementations.azure_blob_rag_config import (
    AzureBlobRAGConfig,
    AzureBlobConfig,
    AzureSearchConfig,
    AzureServicePrincipalAuth,
    AzureResourceConfig,
    AzureAuthMethod,
    AzureStorageRedundancy
)

# Example 1: Basic configuration with service principal authentication
basic_config = {
    "auth_method": "service_principal",
    "service_principal": {
        "tenant_id": "your-tenant-id",
        "client_id": "your-client-id", 
        "client_secret": "your-client-secret",
        "subscription_id": "your-subscription-id"
    },
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount",
        "public_access_level": "private",
        "enable_versioning": True,
        "enable_soft_delete": True,
        "soft_delete_retention_days": 30
    },
    "resource_config": {
        "resource_group_name": "myresourcegroup",
        "location": "eastus",
        "storage_redundancy": "Standard_GRS"  # Geo-redundant storage
    }
}

# Example 2: Configuration with Azure Cognitive Search integration
search_enabled_config = {
    "auth_method": "service_principal",
    "service_principal": {
        "tenant_id": "your-tenant-id",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret", 
        "subscription_id": "your-subscription-id"
    },
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount"
    },
    "resource_config": {
        "resource_group_name": "myresourcegroup",
        "location": "westus2"
    },
    "search_config": {
        "endpoint": "https://mysearch.search.windows.net",
        "api_key": "your-search-api-key",
        "index_name": "documents-index",
        "enable_semantic_search": True,
        "use_skillset": True,
        "skillset_name": "document-extraction"
    },
    "enable_blob_indexing": True
}

# Example 3: Configuration with connection string (simpler auth)
connection_string_config = {
    "auth_method": "connection_string",
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=mystorageaccount;AccountKey=your-key;EndpointSuffix=core.windows.net",
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount"
    },
    "max_concurrent_uploads": 10,
    "blob_tier": "cool"  # Use cool tier for less frequently accessed documents
}

# Example 4: Configuration with managed identity (for Azure-hosted apps)
managed_identity_config = {
    "auth_method": "managed_identity",
    "use_managed_identity": True,
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount"
    },
    "resource_config": {
        "resource_group_name": "myresourcegroup",
        "location": "eastus"
    }
}

# Example 5: Full configuration with all options
full_config = {
    "auth_method": "service_principal",
    "service_principal": {
        "tenant_id": "your-tenant-id",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "subscription_id": "your-subscription-id"
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
        "storage_redundancy": "Standard_RAGRS"  # Read-access geo-redundant storage
    },
    "search_config": {
        "endpoint": "https://ragsearch.search.windows.net",
        "api_key": "your-search-api-key",
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

# Example of using configuration with environment variables
env_var_config = {
    "auth_method": "service_principal",
    "service_principal": {
        # These will use environment variables if not provided
        "tenant_id": None,  # Will use AZURE_TENANT_ID
        "client_id": None,  # Will use AZURE_CLIENT_ID
        "client_secret": None,  # Will use AZURE_CLIENT_SECRET
        "subscription_id": None  # Will use AZURE_SUBSCRIPTION_ID
    },
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount"
    },
    "resource_config": {
        "resource_group_name": "myresourcegroup",
        "location": "eastus"
    }
}

def validate_config(config_dict):
    """Validate configuration by creating AzureBlobRAGConfig object"""
    try:
        config = AzureBlobRAGConfig.from_dict(config_dict)
        print("Configuration is valid!")
        print(f"Auth method: {config.auth_method.value}")
        print(f"Container: {config.blob_config.container_name}")
        print(f"Storage account: {config.blob_config.storage_account_name}")
        return config
    except Exception as e:
        print(f"Configuration error: {e}")
        return None

if __name__ == "__main__":
    # Test configuration validation
    print("=== Testing Basic Configuration ===")
    validate_config(basic_config)
    
    print("\n=== Testing Search-Enabled Configuration ===")
    validate_config(search_enabled_config)
    
    print("\n=== Testing Connection String Configuration ===")
    validate_config(connection_string_config)