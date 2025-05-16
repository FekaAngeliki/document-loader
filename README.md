# Document Loader for RAG Systems

A flexible document management system for collecting files from various sources, processing them, and uploading them to RAG (Retrieval-Augmented Generation) systems.

![CLI Demo](docs/cli-demo.png)

## ✨ Features

- 📁 Multiple file source support (currently File System, expandable to SharePoint, etc.)
- 🔍 Change detection for efficient incremental updates
- 🔌 Configurable RAG system integration
- 💾 PostgreSQL database for tracking file history and sync runs
- 🎨 Beautiful command-line interface with rich formatting

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

Scan files in a directory and calculate hashes without creating a knowledge base:

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