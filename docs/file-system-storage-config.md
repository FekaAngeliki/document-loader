# File System Storage RAG Configuration

This document describes how to configure the File System Storage RAG system for your knowledge base.

## Overview

The File System Storage RAG system stores documents directly on the local file system. This is useful for:
- Development and testing environments
- On-premises deployments
- Situations where cloud storage is not available or desired
- Simple document management without external dependencies

## Configuration Parameters

### Required Parameters

- `storage_path` (string): Base directory path where documents will be stored

### Optional Parameters

- `create_dirs` (boolean): Whether to create directories if they don't exist (default: `true`)
- `preserve_structure` (boolean): Whether to preserve the original directory structure (default: `false`)
- `metadata_format` (string): Format for metadata files - either `"json"` or `"yaml"` (default: `"json"`)

## Configuration Examples

### Basic Configuration

```json
{
  "storage_path": "/var/lib/document-loader/storage"
}
```

### Full Configuration

```json
{
  "storage_path": "/var/lib/document-loader/storage",
  "create_dirs": true,
  "preserve_structure": false,
  "metadata_format": "json"
}
```

### Development Configuration

```json
{
  "storage_path": "/tmp/document-loader-dev",
  "create_dirs": true,
  "preserve_structure": true,
  "metadata_format": "yaml"
}
```

## Creating a Knowledge Base with File System Storage

```bash
# Basic setup
document-loader create-kb \
  --name "local-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/home/user/documents"}' \
  --rag-type "file_system_storage" \
  --rag-config '{"storage_path": "/var/lib/document-loader/storage"}'

# Development setup with structure preservation
document-loader create-kb \
  --name "dev-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/home/user/dev-docs", "include_extensions": [".md", ".txt", ".pdf"]}' \
  --rag-type "file_system_storage" \
  --rag-config '{
    "storage_path": "/tmp/document-loader-dev",
    "create_dirs": true,
    "preserve_structure": true,
    "metadata_format": "yaml"
  }'

# Production setup
document-loader create-kb \
  --name "prod-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/data/documents", "include_extensions": [".pdf", ".docx"]}' \
  --rag-type "file_system_storage" \
  --rag-config '{
    "storage_path": "/var/lib/document-loader/prod-storage",
    "create_dirs": false,
    "metadata_format": "json"
  }'
```

## Updating an Existing Knowledge Base

```bash
# Update to use file system storage
document-loader update-kb --name "my-docs" \
  --rag-type "file_system_storage" \
  --rag-config '{
    "storage_path": "/var/lib/document-loader/storage",
    "create_dirs": true
  }'

# Change storage path
document-loader update-kb --name "local-docs" \
  --rag-config '{"storage_path": "/new/storage/path"}'
```

## Directory Structure

The file system storage will create the following structure:

```
<storage_path>/
├── documents/
│   ├── 5feb1a5c-f449-493d-92df-fb357fac7746.pdf
│   ├── 5feb1a5c-f449-493d-92df-fb357fac7746.pdf.metadata.json
│   ├── 156571e2-6960-4b9d-9550-67b14f5ced14.docx
│   └── 156571e2-6960-4b9d-9550-67b14f5ced14.docx.metadata.json
```

If `preserve_structure` is `true`, the original directory structure will be maintained:

```
<storage_path>/
├── path/
│   └── to/
│       └── original/
│           ├── document.pdf
│           └── document.pdf.metadata.json
```

## Metadata Files

Metadata files contain information about each document:

### JSON Format (default)
```json
{
  "original_filename": "report.pdf",
  "original_uri": "file:///home/user/documents/report.pdf",
  "content_type": "application/pdf",
  "file_hash": "sha256_hash_value",
  "uuid_filename": "5feb1a5c-f449-493d-92df-fb357fac7746.pdf",
  "upload_time": "2024-01-20T10:30:00Z",
  "file_size": 1048576,
  "source": "file_system",
  "custom_metadata": {
    "author": "John Doe",
    "department": "Engineering"
  }
}
```

### YAML Format
```yaml
original_filename: report.pdf
original_uri: file:///home/user/documents/report.pdf
content_type: application/pdf
file_hash: sha256_hash_value
uuid_filename: 5feb1a5c-f449-493d-92df-fb357fac7746.pdf
upload_time: 2024-01-20T10:30:00Z
file_size: 1048576
source: file_system
custom_metadata:
  author: John Doe
  department: Engineering
```

## URI Format

Documents stored in file system storage will have URIs in the format:
```
file:///absolute/path/to/storage/filename
```

For example:
```
file:///var/lib/document-loader/storage/documents/5feb1a5c-f449-493d-92df-fb357fac7746.pdf
```

## Security Considerations

1. **Permissions**: Ensure the storage directory has appropriate permissions
2. **Path Validation**: The implementation should validate paths to prevent directory traversal attacks
3. **Disk Space**: Monitor available disk space
4. **Backup**: Implement regular backups of the storage directory
5. **Access Control**: Use OS-level permissions to control access to stored documents

## Advantages

1. **No External Dependencies**: Works without cloud services or external systems
2. **Simple Backup**: Easy to backup using standard file system tools
3. **Direct Access**: Files can be accessed directly from the file system
4. **Cost Effective**: No cloud storage costs
5. **Complete Control**: Full control over storage location and structure

## Limitations

1. **Scalability**: Limited by local disk space
2. **Redundancy**: No built-in redundancy (unless using RAID or similar)
3. **Network Access**: Requires NFS or similar for multi-server deployments
4. **Performance**: Limited by disk I/O performance
5. **Search**: No built-in search capabilities (unlike cloud solutions)

## Best Practices

1. **Storage Location**: Use a dedicated partition or volume for document storage
2. **Permissions**: Set restrictive permissions (e.g., 750 for directories, 640 for files)
3. **Monitoring**: Monitor disk usage and set up alerts
4. **Backup**: Implement automated backups to a separate location
5. **Cleanup**: Implement a cleanup strategy for old or unused documents