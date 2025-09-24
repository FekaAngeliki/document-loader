# Azure Blob RAG System Configuration

This document describes how to configure the Azure Blob RAG system for your knowledge base.

## Overview

The Azure Blob RAG system stores documents in Azure Blob Storage and optionally integrates with Azure Cognitive Search for indexing and search capabilities.

## Configuration Parameters

### Required Parameters

- `connection_string` (string): Azure Storage connection string
- `container_name` (string): Name of the blob container to use

### Optional Parameters

- `index_name` (string): Name of the Azure Cognitive Search index
- `endpoint` (string): Azure Cognitive Search endpoint URL
- `api_key` (string): Azure Cognitive Search API key

## Configuration Examples

### Basic Configuration (Blob Storage Only)

```json
{
  "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net",
  "container_name": "documents"
}
```

### Full Configuration (With Azure Cognitive Search)

```json
{
  "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net",
  "container_name": "documents",
  "index_name": "rag-documents",
  "endpoint": "https://mysearchservice.search.windows.net",
  "api_key": "your-search-api-key"
}
```

## Creating a Knowledge Base with Azure Blob

```bash
# Basic setup with blob storage only
document-loader create-kb \
  --name "azure-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents", "include_extensions": [".pdf", ".docx", ".txt"]}' \
  --rag-type "azure_blob" \
  --rag-config '{
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net",
    "container_name": "documents"
  }'

# Full setup with Azure Cognitive Search
document-loader create-kb \
  --name "azure-docs-search" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents", "include_extensions": [".pdf", ".docx", ".txt"]}' \
  --rag-type "azure_blob" \
  --rag-config '{
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net",
    "container_name": "documents",
    "index_name": "rag-documents",
    "endpoint": "https://mysearchservice.search.windows.net",
    "api_key": "your-search-api-key"
  }'
```

## Updating an Existing Knowledge Base

```bash
# Update to use Azure Blob
document-loader update-kb --name "my-docs" \
  --rag-type "azure_blob" \
  --rag-config '{
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net",
    "container_name": "documents"
  }'
```

## Implementation Notes

The Azure Blob RAG system implementation should:

1. **Upload**: Store documents in the specified container with appropriate metadata
2. **Update**: Replace existing blobs and update metadata
3. **Delete**: Remove blobs from storage
4. **List**: Enumerate blobs with optional prefix filtering
5. **Get**: Retrieve blob metadata and properties

When Azure Cognitive Search is configured:
- Documents should be indexed for search
- Metadata should be searchable
- Deletion should remove documents from the index

## URI Format

Documents stored in Azure Blob will have URIs in the format:
```
https://{account}.blob.core.windows.net/{container}/{filename}
```

For example:
```
https://myaccount.blob.core.windows.net/documents/5feb1a5c-f449-493d-92df-fb357fac7746.pdf
```

## Security Considerations

1. Store connection strings securely (use environment variables or Azure Key Vault)
2. Use SAS tokens for limited access when possible
3. Enable encryption at rest for blob storage
4. Configure appropriate CORS policies if needed
5. Use managed identities when running in Azure

## Prerequisites

Before using the Azure Blob RAG system:

1. Create an Azure Storage account
2. Create a blob container
3. Obtain the connection string
4. (Optional) Set up Azure Cognitive Search service
5. (Optional) Create a search index with appropriate schema