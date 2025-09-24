# Azure Blob Storage Initialization Command

The `init-azure` command allows you to initialize Azure Blob Storage resources for a knowledge base configured to use Azure Blob as its RAG system.

## Purpose

This command automates the creation of Azure resources required for document storage:
- Creates the Azure Storage Account if it doesn't exist
- Creates the Blob Container if it doesn't exist
- Uses the configuration from the knowledge base

## Prerequisites

1. Azure environment variables must be set:
```bash
export AZURE_TENANT_ID=your-tenant-id
export AZURE_SUBSCRIPTION_ID=your-subscription-id
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret
export AZURE_RESOURCE_GROUP_NAME=your-resource-group
export AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
export AZURE_STORAGE_CONTAINER_NAME=your-container
```

2. A knowledge base must exist with `rag_type` set to `azure_blob`

## Usage

### Basic Usage

```bash
document-loader init-azure --kb-name <knowledge-base-name>
```

### Example

1. First, create a knowledge base with Azure Blob configuration:
```bash
document-loader create-kb \
  --name "my-azure-kb" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents"}' \
  --rag-type "azure_blob" \
  --rag-config '{}'
```

2. Initialize the Azure resources:
```bash
document-loader init-azure --kb-name my-azure-kb
```

3. After successful initialization, you can sync your documents:
```bash
document-loader sync --kb-name my-azure-kb
```

## What the Command Does

1. Retrieves the knowledge base configuration from the database
2. Validates that the knowledge base uses `azure_blob` as its RAG type
3. Creates a connection to Azure using the service principal credentials
4. Checks if the storage account exists, creates it if needed
5. Checks if the blob container exists, creates it if needed
6. Reports success or failure with detailed error messages

## Configuration

The Azure configuration can be provided in two ways:

1. Through environment variables (recommended for security)
2. Through the knowledge base RAG configuration JSON

The system uses the pipe operator (`|`) to fallback to environment variables if values are not in the config:

```python
self.azure_tenant_id = config.get('azure_tenant_id') | AZURE_TENANT_ID
```

## Error Handling

The command provides detailed error messages and stack traces for debugging:
- Missing knowledge base
- Wrong RAG type
- Azure authentication failures
- Resource creation failures

## Security Considerations

- Never commit Azure credentials to version control
- Use environment variables for sensitive information
- Consider using Azure Key Vault for production deployments
- Ensure proper RBAC permissions for the service principal

## Troubleshooting

Common issues and solutions:

1. **Authentication Failed**
   - Verify all environment variables are set correctly
   - Check service principal permissions in Azure

2. **Resource Group Not Found**
   - Ensure the resource group exists or the service principal has permission to create it

3. **Storage Account Creation Failed**
   - Check Azure subscription quotas
   - Verify the storage account name is globally unique
   - Ensure the location is valid

4. **Knowledge Base Not Found**
   - List knowledge bases with `document-loader list-kb`
   - Verify the knowledge base name is correct