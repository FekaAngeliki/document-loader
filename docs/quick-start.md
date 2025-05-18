# Document Loader Quick Start Guide

This guide will help you get started with the Document Loader CLI tool.

## Prerequisites

- PostgreSQL database
- Python environment with `uv` installed
- Required environment variables set (for database and optionally Azure)

## Step-by-Step Guide

### 🔧 Step 1: Check Database Connection

First, verify that you can connect to your PostgreSQL database:

```bash
document-loader check-connection
```

This will check:
- PostgreSQL server connectivity
- Database existence
- Schema initialization status

### 🗄️ Step 2: Create Database and Schema

If the database doesn't exist or schema isn't initialized:

```bash
document-loader create-db
```

This command will:
- Create the database if it doesn't exist
- Initialize all required tables and indexes

### 📚 Step 3: Create a Knowledge Base

Create your first knowledge base:

#### Example 1: Local Files with Mock Storage

```bash
document-loader create-kb \
  --name "my-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents"}' \
  --rag-type "mock"
```

#### Example 2: Local Files with File System Storage

```bash
document-loader create-kb \
  --name "local-storage" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents"}' \
  --rag-type "file_system_storage" \
  --rag-config '{"storage_path": "/path/to/storage", "kb_name": "local-storage"}'
```

#### Example 3: Local Files with Azure Blob Storage

```bash
document-loader create-kb \
  --name "azure-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents"}' \
  --rag-type "azure_blob" \
  --rag-config '{}'  # Uses environment variables
```

### 📋 Step 4: List Knowledge Bases

View all your knowledge bases:

```bash
document-loader list-kb
```

This displays a table with:
- Knowledge base names
- Source types
- RAG types
- Creation dates

### ☁️ Step 5: Initialize Azure Storage (if using azure_blob)

If you're using Azure Blob storage, initialize the resources:

```bash
document-loader init-azure --kb-name azure-docs
```

This command will:
- Create the storage account if it doesn't exist
- Create the blob container if it doesn't exist
- Use credentials from environment variables or config

### 🔄 Step 6: Update Configuration

Update an existing knowledge base:

```bash
# Change the source path
document-loader update-kb \
  --name "my-docs" \
  --source-config '{"root_path": "/new/path/to/documents"}'

# Change to Azure Blob storage
document-loader update-kb \
  --name "my-docs" \
  --rag-type "azure_blob" \
  --rag-config '{}'
```

### 🔄 Step 7: Sync Knowledge Base

Synchronize documents with the RAG system:

```bash
document-loader sync --kb-name my-docs
```

This will:
- Scan the source for files
- Calculate hashes to detect changes
- Upload new/modified files to the RAG system
- Update the database records

## Available Types

### Source Types
- `file_system`: Local file system
- `sharepoint`: SharePoint document library

### RAG Types
- `mock`: Mock storage for testing
- `azure_blob`: Azure Blob Storage
- `file_system_storage`: Local file system storage

## Configuration Examples

### File System Source
```json
{
  "root_path": "/path/to/documents",
  "include_patterns": ["*.pdf", "*.txt", "*.md"],
  "exclude_patterns": ["*.tmp", ".*"]
}
```

### Azure Blob RAG
```json
{
  "azure_tenant_id": "...",              // Or use env: AZURE_TENANT_ID
  "azure_subscription_id": "...",        // Or use env: AZURE_SUBSCRIPTION_ID
  "azure_client_id": "...",              // Or use env: AZURE_CLIENT_ID
  "azure_client_secret": "...",          // Or use env: AZURE_CLIENT_SECRET
  "azure_resource_group_name": "...",    // Or use env: AZURE_RESOURCE_GROUP_NAME
  "azure_storage_account_name": "...",   // Or use env: AZURE_STORAGE_ACCOUNT_NAME
  "azure_storage_container_name": "..."  // Or use env: AZURE_STORAGE_CONTAINER_NAME
}
```

### File System Storage RAG
```json
{
  "storage_path": "/path/to/storage",
  "kb_name": "knowledge-base-name",
  "create_dirs": true,
  "preserve_structure": false,
  "metadata_format": "json"
}
```

## Getting Help

For detailed help on any command:

```bash
document-loader <command> --help
```

For example:
```bash
document-loader create-kb --help
document-loader sync --help
```

## Environment Variables

### Database Configuration
```bash
export DOCUMENT_LOADER_DB_HOST=localhost
export DOCUMENT_LOADER_DB_PORT=5432
export DOCUMENT_LOADER_DB_NAME=document_loader
export DOCUMENT_LOADER_DB_USER=your_user
export DOCUMENT_LOADER_DB_PASSWORD=your_password
```

### Azure Configuration (optional)
```bash
export AZURE_TENANT_ID=your-tenant-id
export AZURE_SUBSCRIPTION_ID=your-subscription-id
export AZURE_CLIENT_ID=your-client-id
export AZURE_CLIENT_SECRET=your-client-secret
export AZURE_RESOURCE_GROUP_NAME=your-resource-group
export AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
export AZURE_STORAGE_CONTAINER_NAME=your-container
```

## Next Steps

1. 📖 Read the [full documentation](./command-line-help.md)
2. 🧪 Try the example scripts in `test_scripts/`
3. 🔍 Use `scan` command to preview what will be synced
4. ⚙️ Explore advanced configuration options