# Document Loader for RAG Systems

A flexible document management system for collecting files from various sources, processing them, and uploading them to RAG (Retrieval-Augmented Generation) systems.

![CLI Demo](docs/cli-demo.png)

## ✨ Features

- 📁 Multiple file source support (currently File System, expandable to SharePoint, etc.)
- 🔍 Change detection for efficient incremental updates
- 🔌 Configurable RAG system integration
- 💾 PostgreSQL database for tracking file history and sync runs
- 🎨 Beautiful command-line interface with rich formatting
- ⚙️ Configuration management system with version control
- 👨‍💼 Admin CLI tools for enterprise configuration management
- 🔄 Multi-source knowledge bases (mixed source types)

## Installation

### From source with UV

1. Clone the repository:
```bash
git clone https://github.com/yourusername/document-loader.git
cd document-loader
```

2. Install as an editable package:
```bash
uv pip install -e .
```

3. Set up PostgreSQL database and configure environment variables:
```bash
# Create a .env file with your database configuration
cat > .env << EOF
DOCUMENT_LOADER_DB_HOST=localhost
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=document_loader
DOCUMENT_LOADER_DB_USER=postgres
DOCUMENT_LOADER_DB_PASSWORD=your_password_here
DOCUMENT_LOADER_DB_MIN_POOL_SIZE=10
DOCUMENT_LOADER_DB_MAX_POOL_SIZE=20
EOF
```

4. Check database connectivity:
```bash
document-loader check-connection
```

5. Create the database and schema (if they don't exist):
```bash
# Option 1: Use the CLI command (creates database + schema)
document-loader create-db

# Option 2: Create during initialization  
document-loader init-db --create-db

# Option 3: Create database only (no schema)
document-loader create-db --no-schema

# Option 4: Create manually
createdb document_loader
document-loader setup  # Then run this to create schema
```

### Using UV tool install

```bash
uv tool install document-loader
```

## 🚀 Usage

### Scan Files (New Feature!)

Scan files in a directory and calculate hashes, displaying each file's:
- Original filename (full path)
- Generated UUID filename
- SHA-256 hash (abbreviated)
- File size
- Content type

Optionally update the database as if performing a real sync run:

```bash
# Scan a local directory (line by line output)
document-loader scan --path /path/to/documents

# Scan and show results in a table
document-loader scan --path /path/to/documents --table

# Scan only top-level files (no recursion)
document-loader scan --path /path/to/documents --no-recursive

# Scan with specific patterns
document-loader scan --path /path/to/documents \
  --source-config '{"include_patterns": ["*.pdf", "*.docx"]}'

# Scan with specific extensions only
document-loader scan --path /path/to/documents \
  --source-config '{"include_extensions": [".pdf", ".docx", ".xlsx"]}'

# Scan with both include extensions and patterns
document-loader scan --path /path/to/documents \
  --source-config '{"include_extensions": [".pdf", ".md"], "include_patterns": ["2024/**", "docs/**"]}'

# Scan a SharePoint folder (requires configuration)
document-loader scan --path /sites/my-site/documents \
  --source-type sharepoint \
  --source-config '{"site_url": "https://company.sharepoint.com", "username": "user", "password": "pass"}'

# Scan using knowledge base configuration
document-loader scan --kb-name "my-docs"

# Scan and update database (as if doing a real sync)
document-loader scan --path /path/to/documents \
  --update-db --kb-name "my-docs"

# Scan with table format and database update
document-loader scan --path /path/to/documents \
  --table --update-db --kb-name "my-docs"

# Scan using KB config and update database
document-loader scan --kb-name "my-docs" --update-db

# Note: Scan runs are recorded in the database with special statuses:
# - scan_running, scan_completed, scan_failed (instead of running, completed, failed)
# - File records are marked as 'scanned' (instead of 'uploaded')
# This allows you to distinguish between actual sync runs and scan runs
```

### Create a Knowledge Base

```bash
# Create with pattern matching
document-loader create-kb \
  --name "my-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents", "include_patterns": ["*.pdf", "*.md"]}' \
  --rag-type "mock" \
  --rag-config '{}'

# Create with extension filtering (more efficient)
document-loader create-kb \
  --name "my-docs" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents", "include_extensions": [".pdf", ".md", ".docx"], "exclude_extensions": [".tmp", ".log"]}' \
  --rag-type "mock" \
  --rag-config '{}'
```

#### Using the Mock RAG System

The mock RAG system is perfect for testing and development. It requires no configuration:

```bash
# Basic example with file system source
document-loader create-kb \
  --name "test-knowledge-base" \
  --source-type "file_system" \
  --source-config '{"root_path": "/path/to/documents", "include_patterns": ["**/*.txt", "**/*.pdf"]}' \
  --rag-type "mock" \
  --rag-config '{}'

# Example with more specific file filtering
document-loader create-kb \
  --name "development-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/home/user/docs",
    "include_extensions": [".md", ".txt"],
    "exclude_patterns": ["temp/**", "**/*.tmp"]
  }' \
  --rag-type "mock" \
  --rag-config '{}'
```

The mock RAG system will:
- Store documents in memory during execution
- Return generated URIs like `/mock/{uuid_filename}`
- Log all operations for debugging
- Support all standard RAG operations (upload, update, delete, list)

### List Knowledge Bases

```bash
document-loader list-kb
# or using the short command
docloader list-kb
```

### View Knowledge Base Details

```bash
document-loader info my-docs
```

### Update Knowledge Base Configuration

```bash
# Update source configuration
document-loader update-kb --name "my-docs" \
  --source-config '{"root_path": "/new/path", "include_patterns": ["*.pdf", "*.docx"]}'

# Update with extension filtering
document-loader update-kb --name "my-docs" \
  --source-config '{"root_path": "/new/path", "include_extensions": [".pdf", ".docx", ".xlsx"], "exclude_extensions": [".tmp", ".log"]}'

# Update RAG type
document-loader update-kb --name "my-docs" \
  --rag-type "new-rag-system" \
  --rag-config '{"api_key": "new-key"}'

# Update multiple fields
document-loader update-kb --name "my-docs" \
  --source-type "sharepoint" \
  --source-config '{"site_url": "https://new-site.com", "path": "/docs"}' \
  --rag-type "openai" \
  --rag-config '{"model": "gpt-4"}'
```

### Show Sync History

```bash
document-loader status my-docs --limit 20
```

### Sync a Knowledge Base

```bash
document-loader sync --kb-name "my-docs"
# or using the short command
docloader sync --kb-name "my-docs"
```

## 🏢 Configuration Management for Admins

The system includes enterprise-grade configuration management tools for administrators to manage knowledge base configurations stored in PostgreSQL.

### Admin CLI Tools

#### Upload Configuration Files

```bash
# Upload a configuration file
document-loader upload-config configs/production.json --name "prod-kb" --description "Production knowledge base"

# Upload with specific admin user
document-loader upload-config configs/production.json --name "prod-kb" --description "Production KB" --created-by "admin"
```

#### List and Manage Configurations

```bash
# List all stored configurations
document-loader list-configs

# List archived configurations
document-loader list-configs --status archived

# Show configuration details
document-loader show-config prod-kb --show-full

# Deploy configuration to create knowledge base
document-loader deploy-config prod-kb

# Export configuration back to file
document-loader export-config prod-kb backup.json

# Show system statistics
document-loader config-summary
```

#### Configuration Management Operations

```bash
# Archive configuration (soft delete)
document-loader delete-config prod-kb --force

# Deploy specific version
document-loader deploy-config prod-kb --version 2

# Export specific version
document-loader export-config prod-kb backup.json --version 1
```

### Configuration File Format for Multi-Source KBs

```json
{
  "name": "multi-source-knowledge-base",
  "description": "Knowledge base with multiple source types",
  "rag_type": "azure_openai",
  "rag_config": {
    "api_endpoint": "https://your-openai.openai.azure.com/",
    "api_key": "${AZURE_OPENAI_API_KEY}",
    "deployment_name": "text-embedding-ada-002"
  },
  "sources": [
    {
      "source_id": "hr_file_system",
      "source_type": "file_system",
      "enabled": true,
      "source_config": {
        "root_path": "/data/hr",
        "include_extensions": [".pdf", ".docx", ".txt"],
        "recursive": true
      },
      "metadata_tags": {
        "department": "HR",
        "content_type": "hr_documents",
        "security_level": "internal"
      },
      "sync_schedule": "0 2 * * *"
    },
    {
      "source_id": "finance_sharepoint",
      "source_type": "enterprise_sharepoint",
      "enabled": true,
      "source_config": {
        "site_url": "https://company.sharepoint.com/sites/finance",
        "document_library": "Financial Documents",
        "folder_path": "/Reports",
        "include_extensions": [".xlsx", ".pdf"],
        "auth_method": "service_principal",
        "client_id": "${SHAREPOINT_CLIENT_ID}",
        "client_secret": "${SHAREPOINT_CLIENT_SECRET}",
        "tenant_id": "${SHAREPOINT_TENANT_ID}"
      },
      "metadata_tags": {
        "department": "Finance",
        "content_type": "financial_reports",
        "security_level": "confidential"
      },
      "sync_schedule": "0 3 * * *"
    }
  ],
  "file_organization": {
    "naming_convention": "{source_id}/{department}/{uuid}{extension}",
    "folder_structure": "source_based"
  },
  "sync_strategy": {
    "default_mode": "parallel",
    "batch_size": 50,
    "max_retries": 3
  }
}
```

### Configuration Management Features

- **Version Control**: Automatic versioning when configurations are updated
- **PostgreSQL Storage**: All configurations stored with SHA-256 integrity hashing
- **Deployment Tracking**: Marks configurations as deployed with timestamps
- **Mixed Source Types**: Support for combining different source types in one KB
- **Rich Metadata**: Department, security level, content type tagging per source
- **Audit Trails**: Complete history of uploads, deployments, and changes

## Troubleshooting

### Database Connection Issues

The CLI provides helpful error messages for common database problems:

1. **PostgreSQL not running**:
   ```
   Cannot connect to PostgreSQL at localhost:5432
   Please ensure PostgreSQL is running:
     On macOS: brew services start postgresql
     On Linux: sudo systemctl start postgresql
   ```

2. **Database doesn't exist**:
   ```
   Database 'document_loader' does not exist.
   You have several options to create it:
   
   1. Use the document-loader CLI:
      document-loader create-db
   
   2. Create it manually:
      createdb -U postgres -h localhost -p 5432 document_loader
   ```

3. **Invalid password**:
   ```
   Invalid password for user 'postgres'.
   Please check your .env configuration:
     DOCUMENT_LOADER_DB_PASSWORD
   ```

4. **Database exists but tables not initialized**:
   ```
   Database tables are not initialized.
   The database exists but the schema hasn't been set up.
   
   Please run one of these commands:
     document-loader create-db  # Will setup schema if database exists
     document-loader setup      # Setup schema only
   ```

Use `document-loader check-connection` to diagnose connection issues step by step.

## Configuration

See the following documentation for detailed configuration information:
- [KNOWLEDGE_BASE_CONFIG.md](KNOWLEDGE_BASE_CONFIG.md) - Complete knowledge base configuration guide
- [SOURCE_CONFIG_GUIDE.md](SOURCE_CONFIG_GUIDE.md) - Detailed source configuration documentation
- [docs/source-config-examples.md](docs/source-config-examples.md) - Real-world configuration examples
- [docs/source-config-validation.md](docs/source-config-validation.md) - Configuration validation guide

### Quick Configuration Examples

#### File System Source

```json
{
  "root_path": "/path/to/documents",
  "include_patterns": ["*.pdf", "*.md"],
  "exclude_patterns": ["*.tmp", ".*"],
  "include_extensions": [".pdf", ".docx", ".xlsx"],
  "exclude_extensions": [".tmp", ".log"]
}
```

#### SharePoint Source

```json
{
  "site_url": "https://company.sharepoint.com",
  "path": "/sites/my-site/documents",
  "username": "user@company.com",
  "password": "password",
  "recursive": true
}
```

### Environment Variables

All environment variables are prefixed with `DOCUMENT_LOADER_` to avoid conflicts.

```bash
# Database configuration
DOCUMENT_LOADER_DB_HOST=localhost
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=document_loader
DOCUMENT_LOADER_DB_USER=postgres
DOCUMENT_LOADER_DB_PASSWORD=your_password
DOCUMENT_LOADER_DB_MIN_POOL_SIZE=10
DOCUMENT_LOADER_DB_MAX_POOL_SIZE=20

# SharePoint configuration (for enterprise_sharepoint sources)
SHAREPOINT_CLIENT_ID=your_client_id
SHAREPOINT_CLIENT_SECRET=your_client_secret
SHAREPOINT_TENANT_ID=your_tenant_id

# Azure OpenAI configuration (for azure_openai RAG)
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/

# Logging
DOCUMENT_LOADER_LOG_LEVEL=INFO
```

You can:
- Set these in a `.env` file (see `.env.example`)
- Export them in your shell (use `source env_setup.sh`)
- Set them in your shell profile for persistent configuration

## Architecture

The system is built with extensibility in mind:

- **File Sources**: Implement the `FileSource` interface to add new sources
- **RAG Systems**: Implement the `RAGSystem` interface to integrate with different RAG providers
- **Database**: PostgreSQL with asyncpg for high-performance database operations
- **Processing**: Asynchronous file processing with change detection

## Development

To add a new file source:
1. Create a new class implementing `FileSource` interface
2. Add the implementation to the factory
3. Register in the `source_type` table

To add a new RAG system:
1. Create a new class implementing `RAGSystem` interface
2. Add the implementation to the factory
3. Register in the `rag_type` table