# Document Loader CLI Command Reference

This document provides a comprehensive reference for all CLI commands and their available options.

## Available Source Types

The following source types are available for document collection:

- `file_system` - Local file system source (default)
- `sharepoint` - SharePoint document library source

## Available RAG Types

The following RAG (Retrieval-Augmented Generation) system types are available:

- `mock` - Mock RAG system for testing (default)
- `azure_blob` - Azure Blob Storage
- `file_system_storage` - Local file system storage

## Commands

### `create-kb` - Create a Knowledge Base

Creates a new knowledge base with specified source and RAG configurations.

**Options:**
- `--name` (required) - Knowledge base name
- `--source-type` - Source type for documents. Available: `file_system`, `sharepoint` (default: `file_system`)
- `--source-config` (required) - Source configuration as JSON
- `--rag-type` - RAG system type. Available: `mock`, `azure_blob`, `file_system_storage` (default: `mock`)
- `--rag-config` - RAG configuration as JSON (default: `{}`)

**Examples:**

```bash
# File system source with mock RAG
document-loader create-kb \
  --name "my-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents"}' \
  --rag-type "mock"

# SharePoint source with Azure Blob RAG
document-loader create-kb \
  --name "sharepoint-docs" \
  --source-type "sharepoint" \
  --source-config '{"site_url": "https://company.sharepoint.com/sites/docs"}' \
  --rag-type "azure_blob" \
  --rag-config '{}'
```

### `update-kb` - Update Knowledge Base

Updates an existing knowledge base configuration.

**Options:**
- `--name` (required) - Knowledge base name
- `--source-type` - New source type. Available: `file_system`, `sharepoint`
- `--source-config` - New source configuration as JSON
- `--rag-type` - New RAG system type. Available: `mock`, `azure_blob`, `file_system_storage`
- `--rag-config` - New RAG configuration as JSON

**Examples:**

```bash
# Update RAG type to Azure Blob
document-loader update-kb \
  --name "my-docs" \
  --rag-type "azure_blob" \
  --rag-config '{}'

# Update source configuration
document-loader update-kb \
  --name "my-docs" \
  --source-config '{"root_path": "/new/path/to/documents"}'
```

### `scan` - Scan Files

Scans files and calculates hashes without syncing to the RAG system.

**Options:**
- `--path` - Path to scan (overrides KB config if --kb-name is provided)
- `--source-type` - Source type. Available: `file_system`, `sharepoint` (default: `file_system`)
- `--source-config` - Additional source configuration as JSON (default: `{}`)
- `--table` - Show results in a table format
- `--recursive/--no-recursive` - Scan recursively (default: True)
- `--update-db` - Update database as if this were a real sync
- `--kb-name` - Knowledge base name (uses KB config if --path not provided)

**Examples:**

```bash
# Scan local directory
document-loader scan \
  --path "/path/to/documents" \
  --source-type "file_system" \
  --recursive

# Scan using knowledge base config
document-loader scan \
  --kb-name "my-docs" \
  --table
```

### `init-azure` - Initialize Azure Storage

Initializes Azure Blob Storage container for a knowledge base configured to use Azure Blob.

**Options:**
- `--kb-name` (required) - Knowledge base name to initialize

**Example:**

```bash
document-loader init-azure --kb-name my-azure-kb
```

### Other Commands

- `list-kb` - List all knowledge bases
- `info` - Show detailed information about a knowledge base
- `status` - Show sync history for a knowledge base
- `sync` - Synchronize a knowledge base
- `check-connection` - Check database connectivity
- `create-db` - Create the database and schema
- `init-db` - Initialize the database (optionally create if not exists)
- `setup` - Set up the database schema

## Configuration Examples

### File System Source Configuration

```json
{
  "root_path": "/path/to/documents",
  "include_patterns": ["*.pdf", "*.txt", "*.md"],
  "exclude_patterns": ["*.tmp", ".*"]
}
```

### SharePoint Source Configuration

```json
{
  "site_url": "https://company.sharepoint.com/sites/docs",
  "folder_path": "/Shared Documents",
  "username": "user@company.com",
  "password": "password"
}
```

### Azure Blob RAG Configuration

```json
{
  "azure_tenant_id": "your-tenant-id",          // Or use env: AZURE_TENANT_ID
  "azure_subscription_id": "your-subscription-id",  // Or use env: AZURE_SUBSCRIPTION_ID
  "azure_client_id": "your-client-id",          // Or use env: AZURE_CLIENT_ID
  "azure_client_secret": "your-client-secret",  // Or use env: AZURE_CLIENT_SECRET
  "azure_resource_group_name": "your-rg",       // Or use env: AZURE_RESOURCE_GROUP_NAME
  "azure_storage_account_name": "youraccount",  // Or use env: AZURE_STORAGE_ACCOUNT_NAME
  "azure_storage_container_name": "container"   // Or use env: AZURE_STORAGE_CONTAINER_NAME
}
```

**Configuration Fields (all optional if environment variables are set):**
- `azure_tenant_id`: Azure AD tenant ID (fallback to env var: AZURE_TENANT_ID)
- `azure_subscription_id`: Azure subscription ID (fallback to env var: AZURE_SUBSCRIPTION_ID)
- `azure_client_id`: Service principal client ID (fallback to env var: AZURE_CLIENT_ID)
- `azure_client_secret`: Service principal client secret (fallback to env var: AZURE_CLIENT_SECRET)
- `azure_resource_group_name`: Azure resource group name (fallback to env var: AZURE_RESOURCE_GROUP_NAME)
- `azure_storage_account_name`: Storage account name (fallback to env var: AZURE_STORAGE_ACCOUNT_NAME)
- `azure_storage_container_name`: Blob container name (fallback to env var: AZURE_STORAGE_CONTAINER_NAME)

**Environment Variable Fallback:**
- If a configuration field is not provided or is empty, the system automatically uses the corresponding environment variable
- You can use an empty configuration `{}` and rely entirely on environment variables
- Configuration values always take precedence over environment variables when provided

**Security Note:** It's recommended to use environment variables for sensitive values like client secrets instead of putting them directly in the configuration JSON.

### Mock RAG Configuration

```json
{}
```

The mock RAG system doesn't require any configuration.

### File System Storage Configuration

```json
{
  "storage_path": "/path/to/storage",     // Base directory for documents
  "kb_name": "knowledge-base-name",       // Subdirectory name
  "create_dirs": true,                    // Auto-create directories (default: true)
  "preserve_structure": false,            // Keep original structure (default: false)
  "metadata_format": "json"               // Metadata format: "json" or "yaml" (default: "json")
}
```

**Configuration Fields:**
- `storage_path` or `root_path`: Base directory where documents will be stored
  - If not provided, falls back to env var: `DOCUMENT_LOADER_STORAGE_PATH`
  - Can be specified as either `storage_path` or `root_path` for compatibility
- `kb_name` (optional): Subdirectory name for this knowledge base (default: "default")
- `create_dirs` (optional): Whether to create directories if they don't exist (default: true)
- `preserve_structure` (optional): Whether to preserve the original directory structure (default: false)
- `metadata_format` (optional): Format for metadata files - "json" or "yaml" (default: "json")

**Environment Variable Fallback:**
- If neither `storage_path` nor `root_path` is provided in the config, the system uses `DOCUMENT_LOADER_STORAGE_PATH` environment variable

## Environment Variables

For Azure Blob RAG, the following environment variables can be used:

- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_RESOURCE_GROUP_NAME`
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_CONTAINER_NAME`

For database connection:

- `DOCUMENT_LOADER_DB_HOST`
- `DOCUMENT_LOADER_DB_PORT`
- `DOCUMENT_LOADER_DB_NAME`
- `DOCUMENT_LOADER_DB_USER`
- `DOCUMENT_LOADER_DB_PASSWORD`