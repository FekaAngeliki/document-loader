# Azure Blob RAG System Implementation Guide

This guide helps you implement the `AzureBlobRAGSystem` class methods.

## Required Dependencies

```python
# Add these to your requirements or pyproject.toml
azure-storage-blob
azure-search-documents  # Optional, for search functionality
```

## Method Implementation Guidelines

### 1. `__init__` Method

```python
def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    # Initialize Azure SDK clients here
    # Example:
    # from azure.storage.blob import BlobServiceClient
    # self.blob_service_client = BlobServiceClient.from_connection_string(
    #     self.connection_string
    # )
    # self.container_client = self.blob_service_client.get_container_client(
    #     self.container_name
    # )
```

### 2. `initialize` Method

```python
async def initialize(self):
    """Create container if it doesn't exist."""
    # Example implementation:
    # try:
    #     await self.container_client.create_container()
    # except ResourceExistsError:
    #     pass  # Container already exists
    # 
    # If search is configured:
    # - Verify search index exists
    # - Create index if needed
```

### 3. `upload_document` Method

```python
async def upload_document(self, content: bytes, filename: str, metadata: Dict[str, Any]) -> str:
    """Upload to blob storage."""
    # 1. Create blob client for the filename
    # 2. Upload content with metadata
    # 3. Return the full blob URI
    # 
    # Example:
    # blob_client = self.container_client.get_blob_client(filename)
    # await blob_client.upload_blob(content, metadata=metadata, overwrite=True)
    # return f"https://{account}.blob.core.windows.net/{container}/{filename}"
```

### 4. `update_document` Method

```python
async def update_document(self, uri: str, content: bytes, metadata: Dict[str, Any]):
    """Update existing blob."""
    # 1. Extract blob name from URI
    # 2. Get blob client
    # 3. Upload new content (overwrite=True)
    # 4. Update metadata
    # 5. Update search index if configured
```

### 5. `delete_document` Method

```python
async def delete_document(self, uri: str):
    """Delete blob from storage."""
    # 1. Extract blob name from URI
    # 2. Get blob client
    # 3. Delete blob
    # 4. Remove from search index if configured
```

### 6. `get_document` Method

```python
async def get_document(self, uri: str) -> Optional[DocumentMetadata]:
    """Get blob metadata."""
    # 1. Extract blob name from URI
    # 2. Get blob properties
    # 3. Create DocumentMetadata object
    # 
    # Example return:
    # return DocumentMetadata(
    #     id=uri,
    #     name=blob_name,
    #     uri=uri,
    #     size=properties.size,
    #     metadata=properties.metadata
    # )
```

### 7. `list_documents` Method

```python
async def list_documents(self, prefix: str = "") -> List[DocumentMetadata]:
    """List blobs with optional prefix."""
    # 1. List blobs in container
    # 2. Filter by prefix if provided
    # 3. Convert to DocumentMetadata objects
    # 
    # Example:
    # documents = []
    # async for blob in self.container_client.list_blobs(prefix=prefix):
    #     documents.append(DocumentMetadata(...))
    # return documents
```

### 8. `cleanup` Method

```python
async def cleanup(self):
    """Close connections."""
    # Close any open clients or connections
    # Release resources
```

## Error Handling

Each method should handle common Azure exceptions:

```python
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

try:
    # Azure operation
except ResourceNotFoundError:
    logger.error(f"Resource not found: {uri}")
    raise
except Exception as e:
    logger.error(f"Azure operation failed: {e}")
    raise
```

## Metadata Format

When storing metadata, consider this structure:

```python
metadata = {
    "original_filename": "document.pdf",
    "content_type": "application/pdf",
    "file_hash": "sha256_hash",
    "upload_time": "2024-01-20T10:30:00Z",
    "source": "file_system",
    # Add any custom metadata from the input
}
```

## URI Parsing

Helper function for extracting blob name from URI:

```python
def _extract_blob_name(self, uri: str) -> str:
    """Extract blob name from URI."""
    # Example: https://account.blob.core.windows.net/container/filename
    # Returns: filename
    from urllib.parse import urlparse
    parsed = urlparse(uri)
    return parsed.path.split('/')[-1]
```

## Testing

Test your implementation:

```bash
# Create a test knowledge base
document-loader create-kb \
  --name "test-azure" \
  --source-type "file_system" \
  --source-config '{"root_path": "/tmp/test-docs"}' \
  --rag-type "azure_blob" \
  --rag-config '{"connection_string": "your-connection-string", "container_name": "test"}'

# Run sync
document-loader sync --kb-name "test-azure"
```

## Async/Await Best Practices

Since the system uses asyncio:

1. Use `async` methods from Azure SDK when available
2. Don't block the event loop with synchronous operations
3. Use `asyncio.gather()` for parallel operations when appropriate

```python
# Good - parallel uploads
results = await asyncio.gather(*[
    self.upload_document(content, filename, metadata)
    for content, filename, metadata in documents
])

# Bad - sequential uploads
for content, filename, metadata in documents:
    await self.upload_document(content, filename, metadata)
```