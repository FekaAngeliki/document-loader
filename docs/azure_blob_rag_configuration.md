# Azure Blob RAG System Configuration Guide

This guide explains how to configure the Azure Blob RAG System with all available parameters.

## Configuration Structure

The Azure Blob RAG System uses a comprehensive configuration structure that supports multiple authentication methods, storage options, and optional Azure Cognitive Search integration.

### Authentication Methods

The system supports four authentication methods:

1. **Service Principal** - Recommended for production
2. **Connection String** - Simple but less secure
3. **Managed Identity** - For Azure-hosted applications
4. **Default Credential** - Uses Azure CLI or environment authentication

### Configuration Schema

```python
{
    # Authentication method (required)
    "auth_method": "service_principal" | "connection_string" | "managed_identity" | "default_credential",
    
    # Service Principal authentication (required if auth_method is "service_principal")
    "service_principal": {
        "tenant_id": "string",
        "client_id": "string", 
        "client_secret": "string",
        "subscription_id": "string"
    },
    
    # Connection string (required if auth_method is "connection_string")
    "connection_string": "string",
    
    # Managed identity flag (required if auth_method is "managed_identity")
    "use_managed_identity": true,
    
    # Blob storage configuration (required)
    "blob_config": {
        "container_name": "string",
        "storage_account_name": "string",
        "public_access_level": "private" | "blob" | "container",
        "enable_versioning": boolean,
        "enable_soft_delete": boolean,
        "soft_delete_retention_days": integer
    },
    
    # Azure resource configuration (required for service principal)
    "resource_config": {
        "resource_group_name": "string",
        "location": "string",  # e.g., "eastus", "westus2"
        "storage_redundancy": "Standard_LRS" | "Standard_ZRS" | "Standard_GRS" | "Standard_RAGRS"
    },
    
    # Azure Cognitive Search configuration (optional)
    "search_config": {
        "endpoint": "string",
        "api_key": "string",
        "index_name": "string",
        "enable_semantic_search": boolean,
        "use_skillset": boolean,
        "skillset_name": "string"
    },
    
    # Performance settings
    "max_concurrent_uploads": integer,
    "max_upload_retry_attempts": integer,
    "upload_timeout_seconds": integer,
    
    # Blob tier settings
    "blob_tier": "hot" | "cool" | "archive",
    "enable_blob_indexing": boolean
}
```

## Configuration Examples

### Example 1: Basic Service Principal Authentication

```json
{
    "auth_method": "service_principal",
    "service_principal": {
        "tenant_id": "12345678-1234-1234-1234-123456789012",
        "client_id": "87654321-4321-4321-4321-210987654321",
        "client_secret": "your-client-secret",
        "subscription_id": "98765432-1234-5678-9012-345678901234"
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
```

### Example 2: Connection String Authentication

```json
{
    "auth_method": "connection_string",
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=mystorageaccount;AccountKey=your-key;EndpointSuffix=core.windows.net",
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount"
    }
}
```

### Example 3: With Azure Cognitive Search

```json
{
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
        "enable_semantic_search": true
    }
}
```

### Example 4: Managed Identity (for Azure-hosted apps)

```json
{
    "auth_method": "managed_identity",
    "use_managed_identity": true,
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount"
    },
    "resource_config": {
        "resource_group_name": "myresourcegroup",
        "location": "eastus"
    }
}
```

## Configuration Parameters

### Authentication Parameters

- **auth_method**: The authentication method to use
- **service_principal**: Service principal credentials (tenant_id, client_id, client_secret, subscription_id)
- **connection_string**: Full Azure Storage connection string
- **use_managed_identity**: Flag to use managed identity authentication

### Blob Configuration Parameters

- **container_name**: Name of the blob container to use
- **storage_account_name**: Name of the Azure Storage account
- **public_access_level**: Container access level ("private", "blob", or "container")
- **enable_versioning**: Enable blob versioning
- **enable_soft_delete**: Enable soft delete for blobs
- **soft_delete_retention_days**: Number of days to retain soft-deleted blobs

### Resource Configuration Parameters

- **resource_group_name**: Azure resource group name
- **location**: Azure region (e.g., "eastus", "westus2", "centralus")
- **storage_redundancy**: Storage redundancy option:
  - Standard_LRS: Locally redundant storage
  - Standard_ZRS: Zone-redundant storage
  - Standard_GRS: Geo-redundant storage
  - Standard_RAGRS: Read-access geo-redundant storage

### Search Configuration Parameters

- **endpoint**: Azure Cognitive Search endpoint URL
- **api_key**: Azure Cognitive Search API key
- **index_name**: Name of the search index
- **enable_semantic_search**: Enable semantic search capabilities
- **use_skillset**: Use cognitive skillset for document processing
- **skillset_name**: Name of the cognitive skillset

### Performance Parameters

- **max_concurrent_uploads**: Maximum number of concurrent uploads (default: 5)
- **max_upload_retry_attempts**: Maximum retry attempts for failed uploads (default: 3)
- **upload_timeout_seconds**: Upload timeout in seconds (default: 300)

### Blob Settings

- **blob_tier**: Storage tier for blobs ("hot", "cool", or "archive")
- **enable_blob_indexing**: Enable blob indexing in Azure Search

## Environment Variable Support

The system supports using environment variables for sensitive values:

```json
{
    "auth_method": "service_principal",
    "service_principal": {
        "tenant_id": null,      // Will use AZURE_TENANT_ID
        "client_id": null,      // Will use AZURE_CLIENT_ID  
        "client_secret": null,  // Will use AZURE_CLIENT_SECRET
        "subscription_id": null // Will use AZURE_SUBSCRIPTION_ID
    },
    "blob_config": {
        "container_name": "documents",
        "storage_account_name": "mystorageaccount"
    }
}
```

## Migration from Old Configuration

If you have existing configurations, use the migration script:

```bash
python scripts/migrate_azure_blob_config.py
```

This will automatically convert old configuration formats to the new structure.

## Validation

To validate your configuration:

```python
from src.implementations.azure_blob_rag_config import AzureBlobRAGConfig

# Load your configuration
config_dict = {...}

# Validate
try:
    config = AzureBlobRAGConfig.from_dict(config_dict)
    print("Configuration is valid!")
except Exception as e:
    print(f"Configuration error: {e}")
```

## Best Practices

1. **Use Service Principal for Production**: More secure than connection strings
2. **Enable Soft Delete**: Protects against accidental deletions
3. **Choose Appropriate Storage Redundancy**: Based on your disaster recovery needs
4. **Use Cool Tier for Archival**: Reduces storage costs for infrequently accessed documents
5. **Enable Search Integration**: For better document discovery
6. **Set Appropriate Timeouts**: Based on your document sizes and network conditions
7. **Use Environment Variables**: For sensitive configuration values

## Troubleshooting

Common configuration issues:

1. **Missing Required Fields**: Ensure all required fields for your auth method are provided
2. **Invalid Enum Values**: Check that string values match the allowed options
3. **Authentication Failures**: Verify service principal permissions and credentials
4. **Container Access**: Ensure the service principal has appropriate storage permissions
5. **Search Integration**: Verify search endpoint and API key are correct