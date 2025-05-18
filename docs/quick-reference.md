# Document Loader - Quick Reference Card

## 🎯 Command Overview

| Command | Purpose | Basic Usage |
|---------|---------|-------------|
| `check-connection` | Test DB connection | `document-loader check-connection` |
| `create-db` | Create database | `document-loader create-db` |
| `create-kb` | Create knowledge base | `document-loader create-kb --name <n> ...` |
| `list-kb` | List all KBs | `document-loader list-kb` |
| `init-azure` | Init Azure storage | `document-loader init-azure --kb-name <n>` |
| `update-kb` | Update KB config | `document-loader update-kb --name <n> ...` |
| `sync` | Sync documents | `document-loader sync --kb-name <n>` |
| `scan` | Preview sync | `document-loader scan --kb-name <n>` |
| `info` | Show KB details | `document-loader info <kb-name>` |
| `status` | Show sync history | `document-loader status <kb-name>` |

## 🔧 Configuration Structures

### File System Source
```json
{
  "root_path": "/path/to/docs",
  "include_patterns": ["*.pdf", "*.txt"],
  "exclude_patterns": ["*.tmp"]
}
```

### Mock RAG (Testing)
```json
{}  // No configuration needed
```

### File System Storage RAG
```json
{
  "storage_path": "/path/to/storage",
  "kb_name": "my-kb",
  "create_dirs": true
}
```

### Azure Blob RAG
```json
{}  // Uses environment variables
```
Or explicit:
```json
{
  "azure_tenant_id": "...",
  "azure_subscription_id": "...",
  "azure_client_id": "...",
  "azure_client_secret": "...",
  "azure_resource_group_name": "...",
  "azure_storage_account_name": "...",
  "azure_storage_container_name": "..."
}
```

## 🚀 Common Workflows

### Create and Sync Local Files
```bash
# 1. Create KB
document-loader create-kb \
  --name "docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/docs"}' \
  --rag-type "mock"

# 2. Preview what will be synced
document-loader scan --kb-name docs --table

# 3. Sync files
document-loader sync --kb-name docs
```

### Create and Sync to Azure
```bash
# 1. Create KB with Azure
document-loader create-kb \
  --name "azure-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/docs"}' \
  --rag-type "azure_blob" \
  --rag-config '{}'

# 2. Initialize Azure resources
document-loader init-azure --kb-name azure-docs

# 3. Sync files
document-loader sync --kb-name azure-docs
```

## 🔍 Useful Commands

### Check what's configured
```bash
# List all KBs
document-loader list-kb

# Show KB details
document-loader info my-kb

# Show sync history
document-loader status my-kb --limit 5
```

### Update configuration
```bash
# Change source path
document-loader update-kb \
  --name my-kb \
  --source-config '{"root_path": "/new/path"}'

# Change to Azure
document-loader update-kb \
  --name my-kb \
  --rag-type azure_blob \
  --rag-config '{}'
```

## 📊 Environment Variables

```bash
# Database (Required)
export DOCUMENT_LOADER_DB_HOST=localhost
export DOCUMENT_LOADER_DB_PORT=5432
export DOCUMENT_LOADER_DB_NAME=document_loader
export DOCUMENT_LOADER_DB_USER=user
export DOCUMENT_LOADER_DB_PASSWORD=pass

# Azure (Optional)
export AZURE_TENANT_ID=xxx
export AZURE_SUBSCRIPTION_ID=xxx
export AZURE_CLIENT_ID=xxx
export AZURE_CLIENT_SECRET=xxx
export AZURE_RESOURCE_GROUP_NAME=xxx
export AZURE_STORAGE_ACCOUNT_NAME=xxx
export AZURE_STORAGE_CONTAINER_NAME=xxx
```

## 💡 Tips

1. Always run `check-connection` first
2. Use `scan --table` to preview before syncing
3. Use environment variables for sensitive data
4. Run `--help` on any command for details
5. Check `status` to see sync history

---
**Quick Help:** `document-loader --help` | **Command Help:** `document-loader <command> --help`