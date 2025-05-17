# File System Storage Implementation Guide

This guide helps you implement the `FileSystemStorage` class methods.

## Directory Structure

The implementation should create this structure:

```
<storage_path>/
├── documents/          # Main document storage
└── metadata/          # Optional separate metadata directory
```

## Method Implementation Guidelines

### 1. `__init__` Method

```python
def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    self.storage_path = Path(config.get('storage_path'))
    self.create_dirs = config.get('create_dirs', True)
    self.preserve_structure = config.get('preserve_structure', False)
    self.metadata_format = config.get('metadata_format', 'json')
    
    # Validate configuration
    if not self.storage_path:
        raise ValueError("storage_path is required")
    
    # Initialize subdirectories
    self.documents_dir = self.storage_path / "documents"
    self.metadata_dir = self.storage_path / "metadata"
```

### 2. `initialize` Method

```python
async def initialize(self):
    """Create directories and verify permissions."""
    # Create directories if configured
    if self.create_dirs:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
    
    # Verify directories exist
    if not self.storage_path.exists():
        raise ValueError(f"Storage path does not exist: {self.storage_path}")
    
    # Check write permissions
    test_file = self.storage_path / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        raise PermissionError(f"No write permission for: {self.storage_path}")
```

### 3. `upload_document` Method

```python
async def upload_document(self, content: bytes, filename: str, metadata: Dict[str, Any]) -> str:
    """Save document and metadata to file system."""
    # Determine file path
    if self.preserve_structure and 'original_path' in metadata:
        # Preserve original directory structure
        relative_path = Path(metadata['original_path']).parent
        file_path = self.documents_dir / relative_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        file_path = self.documents_dir / filename
    
    # Save content
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Save metadata
    metadata_path = self._get_metadata_path(file_path)
    await self._save_metadata(metadata_path, metadata)
    
    # Return file URI
    return self._path_to_uri(file_path)
```

### 4. `update_document` Method

```python
async def update_document(self, uri: str, content: bytes, metadata: Dict[str, Any]):
    """Update existing document and metadata."""
    file_path = self._uri_to_path(uri)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {uri}")
    
    # Update content
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Update metadata
    metadata_path = self._get_metadata_path(file_path)
    await self._save_metadata(metadata_path, metadata)
```

### 5. `delete_document` Method

```python
async def delete_document(self, uri: str):
    """Delete document and metadata files."""
    file_path = self._uri_to_path(uri)
    metadata_path = self._get_metadata_path(file_path)
    
    # Delete document
    if file_path.exists():
        file_path.unlink()
    
    # Delete metadata
    if metadata_path.exists():
        metadata_path.unlink()
    
    # Clean up empty directories if configured
    if self.preserve_structure:
        try:
            file_path.parent.rmdir()  # Only removes if empty
        except OSError:
            pass  # Directory not empty
```

### 6. `get_document` Method

```python
async def get_document(self, uri: str) -> Optional[DocumentMetadata]:
    """Get document metadata."""
    file_path = self._uri_to_path(uri)
    
    if not file_path.exists():
        return None
    
    # Read metadata
    metadata_path = self._get_metadata_path(file_path)
    metadata = await self._load_metadata(metadata_path)
    
    # Get file stats
    stat = file_path.stat()
    
    return DocumentMetadata(
        id=uri,
        name=file_path.name,
        uri=uri,
        size=stat.st_size,
        metadata=metadata
    )
```

### 7. `list_documents` Method

```python
async def list_documents(self, prefix: str = "") -> List[DocumentMetadata]:
    """List all documents with optional prefix filter."""
    documents = []
    
    # Walk through documents directory
    for file_path in self.documents_dir.rglob("*"):
        if not file_path.is_file():
            continue
        
        # Skip metadata files
        if file_path.suffix in ['.metadata', '.json', '.yaml']:
            continue
        
        # Apply prefix filter
        if prefix:
            relative_path = file_path.relative_to(self.documents_dir)
            if not str(relative_path).startswith(prefix):
                continue
        
        # Get document metadata
        uri = self._path_to_uri(file_path)
        doc_metadata = await self.get_document(uri)
        if doc_metadata:
            documents.append(doc_metadata)
    
    return documents
```

### 8. Helper Methods

```python
def _uri_to_path(self, uri: str) -> Path:
    """Convert file URI to Path."""
    from urllib.parse import urlparse, unquote
    
    parsed = urlparse(uri)
    if parsed.scheme != 'file':
        raise ValueError(f"Invalid file URI: {uri}")
    
    # Handle different URI formats
    path = unquote(parsed.path)
    if os.name == 'nt' and path.startswith('/'):
        # Windows: file:///C:/path -> C:/path
        path = path[1:]
    
    return Path(path)

def _path_to_uri(self, path: Path) -> str:
    """Convert Path to file URI."""
    from urllib.parse import quote
    
    # Convert to absolute path
    abs_path = path.absolute()
    
    # Convert to URI
    if os.name == 'nt':
        # Windows: C:\path -> file:///C:/path
        uri_path = '/' + str(abs_path).replace('\\', '/')
    else:
        # Unix: /path -> file:///path
        uri_path = str(abs_path)
    
    return f"file://{quote(uri_path)}"

def _get_metadata_path(self, document_path: Path) -> Path:
    """Get metadata file path for a document."""
    return document_path.with_suffix(document_path.suffix + f'.metadata.{self.metadata_format}')

async def _save_metadata(self, path: Path, metadata: Dict[str, Any]):
    """Save metadata to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if self.metadata_format == 'json':
        import json
        content = json.dumps(metadata, indent=2)
    else:  # yaml
        import yaml
        content = yaml.dump(metadata, default_flow_style=False)
    
    async with aiofiles.open(path, 'w') as f:
        await f.write(content)

async def _load_metadata(self, path: Path) -> Dict[str, Any]:
    """Load metadata from file."""
    if not path.exists():
        return {}
    
    async with aiofiles.open(path, 'r') as f:
        content = await f.read()
    
    if self.metadata_format == 'json':
        import json
        return json.loads(content)
    else:  # yaml
        import yaml
        return yaml.safe_load(content)
```

## Dependencies

Add these to your project:

```python
# For async file operations
aiofiles
# For YAML support (optional)
pyyaml
```

## Error Handling

```python
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    # File operations
except FileNotFoundError:
    logger.error(f"File not found: {path}")
    raise
except PermissionError:
    logger.error(f"Permission denied: {path}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

## Testing

Test your implementation:

```bash
# Create test knowledge base
document-loader create-kb \
  --name "test-fs-storage" \
  --source-type "file_system" \
  --source-config '{"root_path": "/tmp/test-docs"}' \
  --rag-type "file_system_storage" \
  --rag-config '{"storage_path": "/tmp/test-storage", "create_dirs": true}'

# Create test files
mkdir -p /tmp/test-docs
echo "Test content" > /tmp/test-docs/test.txt

# Run sync
document-loader sync --kb-name "test-fs-storage"

# Verify files
ls -la /tmp/test-storage/documents/
```

## Performance Considerations

1. **Async I/O**: Use `aiofiles` for non-blocking file operations
2. **Batch Operations**: Process multiple files concurrently when possible
3. **Caching**: Consider caching metadata for frequently accessed files
4. **Directory Listing**: Use generators for large directories to avoid memory issues

```python
# Good - async generator for large directories
async def _list_files_async(self, directory: Path):
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            yield file_path

# Better - concurrent processing
import asyncio

async def process_files(self, files: List[Path]):
    tasks = [self.process_file(f) for f in files]
    return await asyncio.gather(*tasks)
```