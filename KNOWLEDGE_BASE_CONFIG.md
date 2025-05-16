# Knowledge Base Configuration Guide

This document describes the configuration structure for Knowledge Bases in the Document Loader system.

## Overview

A Knowledge Base in Document Loader is a named collection of documents that are synchronized from a source system to a RAG (Retrieval-Augmented Generation) system. Each Knowledge Base has:

1. A unique name
2. A source configuration (where to get files from)
3. A RAG configuration (where to send files to)

## Knowledge Base Structure

```python
KnowledgeBase:
  id: int                    # Auto-generated ID
  name: str                  # Unique name for the KB
  source_type: str           # Type of source (e.g., "file_system", "sharepoint")
  source_config: dict        # Configuration for the source
  rag_type: str             # Type of RAG system (e.g., "mock", "openai")
  rag_config: dict          # Configuration for the RAG system
  created_at: datetime      # Creation timestamp
  updated_at: datetime      # Last update timestamp
```

## Source Types and Configuration

### 1. File System Source

**Type**: `file_system`

**Configuration Schema**:
```json
{
  "root_path": "/path/to/documents",           // Required: Base directory path
  "include_patterns": ["*.pdf", "*.md"],       // Optional: File patterns to include (default: ["*"])
  "exclude_patterns": ["*.tmp", ".*"]          // Optional: File patterns to exclude (default: [])
}
```

**Example**:
```bash
document-loader create-kb \
  --name "my-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/home/user/documents",
    "include_patterns": ["*.pdf", "*.docx", "*.md"],
    "exclude_patterns": ["*.tmp", "~*", ".*"]
  }'
```

### 2. SharePoint Source

**Type**: `sharepoint`

**Configuration Schema**:
```json
{
  "site_url": "https://company.sharepoint.com",  // Required: SharePoint site URL
  "path": "/sites/my-site/documents",           // Required: Path within SharePoint
  "username": "user@company.com",               // Required: SharePoint username
  "password": "password",                       // Required: SharePoint password
  "recursive": true                             // Optional: Recurse into folders (default: true)
}
```

**Example**:
```bash
document-loader create-kb \
  --name "sharepoint-docs" \
  --source-type "sharepoint" \
  --source-config '{
    "site_url": "https://company.sharepoint.com",
    "path": "/sites/engineering/documents",
    "username": "john.doe@company.com",
    "password": "secure_password",
    "recursive": true
  }'
```

## RAG Types and Configuration

### 1. Mock RAG System

**Type**: `mock`

**Configuration Schema**:
```json
{}  // No configuration required for mock system
```

**Example**:
```bash
document-loader create-kb \
  --name "test-kb" \
  --source-type "file_system" \
  --source-config '{"root_path": "/tmp/test-docs"}' \
  --rag-type "mock" \
  --rag-config '{}'
```

### 2. Custom RAG Systems

Additional RAG systems can be implemented by:
1. Creating a new implementation of the RAG interface
2. Registering it in the `rag_type` table
3. Defining its configuration schema

## Complete Examples

### Example 1: PDF Documentation Knowledge Base
```bash
document-loader create-kb \
  --name "product-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/opt/documentation",
    "include_patterns": ["*.pdf"],
    "exclude_patterns": ["draft_*", "old_*"]
  }' \
  --rag-type "mock"
```

### Example 2: SharePoint Knowledge Base
```bash
document-loader create-kb \
  --name "hr-policies" \
  --source-type "sharepoint" \
  --source-config '{
    "site_url": "https://mycompany.sharepoint.com",
    "path": "/sites/HR/Policies",
    "username": "hr_user@mycompany.com",
    "password": "${SHAREPOINT_PASSWORD}",
    "recursive": true
  }' \
  --rag-type "mock"
```

### Example 3: Markdown Documentation
```bash
document-loader create-kb \
  --name "engineering-wiki" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/var/wiki/engineering",
    "include_patterns": ["*.md", "*.markdown"],
    "exclude_patterns": [".git/**"]
  }' \
  --rag-type "mock"
```

## Configuration Best Practices

1. **Use Environment Variables for Secrets**:
   ```bash
   export SHAREPOINT_PASSWORD="your_password"
   document-loader create-kb \
     --source-config "{\"password\": \"${SHAREPOINT_PASSWORD}\"}"
   ```

2. **Use Specific Include Patterns**:
   - Instead of processing all files, limit to specific types
   - This improves performance and reduces unnecessary processing

3. **Exclude Temporary Files**:
   - Always exclude temp files, hidden files, and version control directories
   - Common excludes: `["*.tmp", "~*", ".*", ".git/**", "__pycache__/**"]`

4. **Name Knowledge Bases Descriptively**:
   - Use clear, descriptive names that indicate the content
   - Examples: "product-docs-v2", "hr-policies-2024", "engineering-wiki"

## Viewing Configuration

To see the configuration of existing knowledge bases:

```bash
# List all knowledge bases
document-loader list-kb

# View detailed info about a specific KB
document-loader info my-docs
```

## Modifying Configuration

You can update knowledge base configurations using the `update-kb` command:

```bash
# Update source configuration only
document-loader update-kb --name "my-kb" \
  --source-config '{"root_path": "/new/path"}'

# Update RAG configuration
document-loader update-kb --name "my-kb" \
  --rag-config '{"api_key": "new-key"}'

# Change source type (be careful - this may affect sync)
document-loader update-kb --name "my-kb" \
  --source-type "sharepoint" \
  --source-config '{"site_url": "https://company.sharepoint.com", "path": "/sites/docs"}'

# Update multiple configurations at once
document-loader update-kb --name "my-kb" \
  --source-type "file_system" \
  --source-config '{"root_path": "/docs", "include_patterns": ["*.pdf"]}' \
  --rag-type "openai" \
  --rag-config '{"model": "gpt-4"}'
```

### Update Command Options

- `--name`: Required. The name of the knowledge base to update
- `--source-type`: New source type (must be a valid registered type)
- `--source-config`: New source configuration as JSON
- `--rag-type`: New RAG system type (must be a valid registered type)
- `--rag-config`: New RAG configuration as JSON

### Update Behavior

1. The command will show current configuration and proposed changes
2. You'll be prompted to confirm before applying changes
3. The `updated_at` timestamp is automatically updated
4. Invalid configurations or types will be rejected with helpful error messages

### Safety Features

- Type validation: Source and RAG types must exist in the system
- JSON validation: Configurations must be valid JSON objects
- Confirmation prompt: Prevents accidental updates
- Current state display: Shows what will be changed

## Adding New Source or RAG Types

To add support for new source or RAG types:

1. Implement the appropriate interface (`FileSource` or `RAGSystem`)
2. Register the type in the database:
   ```sql
   INSERT INTO source_type (name, class_name, config_schema) 
   VALUES ('my_source', 'path.to.MySource', '{"type": "object", ...}');
   ```
3. Update the factory classes to handle the new type

## Troubleshooting

Common configuration issues:

1. **Invalid JSON**: Ensure your JSON is properly formatted
   ```bash
   # Good
   --source-config '{"root_path": "/docs"}'
   
   # Bad (single quotes inside)
   --source-config '{'root_path': '/docs'}'
   ```

2. **Missing Required Fields**: Check the schema for required fields
3. **Path Issues**: Use absolute paths for file system sources
4. **Authentication Errors**: Verify credentials for remote sources

## Security Considerations

1. **Store credentials securely**: Use environment variables or secure vaults
2. **Limit file access**: Use include/exclude patterns to control access
3. **Network security**: Use HTTPS for remote sources when possible
4. **Audit trails**: Monitor sync runs for unusual activity