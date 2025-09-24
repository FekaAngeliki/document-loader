# Document Loader - Quick Start

## 🚀 Getting Started in 7 Steps

```bash
# 1. Check database connection
document-loader check-connection

# 2. Create database and schema
document-loader create-db

# 3. Create a knowledge base
document-loader create-kb \
  --name "my-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents"}' \
  --rag-type "mock"

# 4. List knowledge bases
document-loader list-kb

# 5. Initialize Azure (if using azure_blob)
document-loader init-azure --kb-name my-docs

# 6. Update configuration (optional)
document-loader update-kb --name my-docs [options]

# 7. Sync your knowledge base
document-loader sync --kb-name my-docs
```

## 📌 Available Options

**Source Types:**
- `file_system` - Local files
- `sharepoint` - SharePoint documents

**RAG Types:**
- `mock` - Testing (no config needed)
- `azure_blob` - Azure Blob Storage
- `file_system_storage` - Local storage

## 💡 Common Examples

### Local Files → Mock Storage
```bash
document-loader create-kb \
  --name "test" \
  --source-type "file_system" \
  --source-config '{"root_path": "/docs"}' \
  --rag-type "mock"
```

### Local Files → Azure Blob
```bash
document-loader create-kb \
  --name "prod" \
  --source-type "file_system" \
  --source-config '{"root_path": "/docs"}' \
  --rag-type "azure_blob" \
  --rag-config '{}'  # Uses env vars
```

### Local Files → File System Storage
```bash
document-loader create-kb \
  --name "local" \
  --source-type "file_system" \
  --source-config '{"root_path": "/docs"}' \
  --rag-type "file_system_storage" \
  --rag-config '{"storage_path": "/storage"}'
```

## 🔍 Get Help

```bash
# General help
document-loader --help

# Command-specific help
document-loader create-kb --help
document-loader sync --help
```

## 🔐 Environment Variables

### Database (Required)
```bash
DOCUMENT_LOADER_DB_HOST=localhost
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=document_loader
DOCUMENT_LOADER_DB_USER=user
DOCUMENT_LOADER_DB_PASSWORD=password
```

### Azure (Optional)
```bash
AZURE_TENANT_ID=xxx
AZURE_SUBSCRIPTION_ID=xxx
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx
AZURE_RESOURCE_GROUP_NAME=xxx
AZURE_STORAGE_ACCOUNT_NAME=xxx
AZURE_STORAGE_CONTAINER_NAME=xxx
```

---
**Tip:** Use `document-loader <command> --help` for detailed configuration options!