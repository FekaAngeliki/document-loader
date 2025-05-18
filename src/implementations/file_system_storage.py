import logging
import os
import json
import yaml
import aiofiles
import asyncio
from urllib.parse import quote, unquote, urlparse
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..abstractions.rag_system import RAGSystem, DocumentMetadata

logger = logging.getLogger(__name__)

class FileSystemStorage(RAGSystem):
    """File system-based implementation of RAGSystem for local storage."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the File System Storage.
        
        Args:
            config: Configuration dictionary that should contain:
                - root_path OR storage_path: Base directory for storing documents
                - kb_name: Knowledge base name (used for subdirectory)
                - create_dirs: (Optional) Whether to create directories if they don't exist (default: True)
                - preserve_structure: (Optional) Whether to preserve directory structure (default: False)
                - metadata_format: (Optional) Format for metadata files ('json' or 'yaml', default: 'json')
                
        Environment variables:
            - DOCUMENT_LOADER_STORAGE_PATH: Default storage path if not provided in config
        """
        super().__init__(config)
        
        if config is None:
            config = {}
        
        # Support both root_path and storage_path for compatibility
        # Also check environment variable as fallback
        base_path = (config.get('root_path') or 
                    config.get('storage_path') or 
                    os.environ.get('DOCUMENT_LOADER_STORAGE_PATH'))
                    
        if not base_path:
            raise ValueError("root_path or storage_path is required (can also use DOCUMENT_LOADER_STORAGE_PATH env var)")
            
        self.storage_path = Path(base_path)
        self.kb_name = config.get('kb_name', 'default')
        self.create_dirs = config.get('create_dirs', True)
        self.preserve_structure = config.get('preserve_structure', False)
        self.metadata_format = config.get('metadata_format', 'json')
        
        # Initialize subdirectories
        # The storage_path already includes the knowledge base path
        self.documents_dir = self.storage_path / "documents"
        self.metadata_dir = self.storage_path / "metadata"
    
    async def initialize(self):
        """Initialize the file system storage and create directories if needed."""
        logger.info(f"Initializing file system storage at: {self.storage_path}")
        
        # Create directories if configured
        if self.create_dirs:
            def make_dirs():
                self.storage_path.mkdir(parents=True, exist_ok=True)
                self.documents_dir.mkdir(parents=True, exist_ok=True)
                self.metadata_dir.mkdir(parents=True, exist_ok=True)
            
            await asyncio.get_event_loop().run_in_executor(None, make_dirs)
        
        # Verify directories exist
        if not self.storage_path.exists():
            raise ValueError(f"Storage path does not exist: {self.storage_path}")
        
        # Create documents directory if it doesn't exist
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.documents_dir.mkdir(parents=True, exist_ok=True)
        )
        
        # Check write permissions
        test_file = self.storage_path / ".write_test"
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, test_file.touch
            )
            await asyncio.get_event_loop().run_in_executor(
                None, test_file.unlink
            )
        except PermissionError:
            raise PermissionError(f"No write permission for: {self.storage_path}")
        
        logger.info("File system storage initialized successfully")
    
    async def upload_document(self, 
                           content: bytes, 
                           filename: str, 
                           metadata: Dict[str, Any]) -> str:
        """
        Save a document to the file system.
        
        Args:
            content: File content as bytes
            filename: UUID filename to use
            metadata: Metadata to save alongside the document
            
        Returns:
            The file URI (e.g., file:///path/to/storage/filename)
        """
        logger.info(f"Saving document to file system: {filename}")
        
        # Determine file path
        if self.preserve_structure:
            # Check for original path/uri in metadata
            original_path = metadata.get('original_path') or metadata.get('original_uri')
            if original_path:
                # Preserve original directory structure
                # Make path relative to root if it's absolute
                original_path_obj = Path(original_path)
                if original_path_obj.is_absolute():
                    # Try to make it relative to some common root
                    try:
                        # Just take the last few components of the path
                        path_parts = original_path_obj.parts[-3:]  # Take last 3 parts
                        relative_path = Path(*path_parts[:-1])  # Exclude the filename
                    except IndexError:
                        relative_path = original_path_obj.parent
                else:
                    relative_path = original_path_obj.parent
                file_path = self.documents_dir / relative_path / filename
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: file_path.parent.mkdir(parents=True, exist_ok=True)
                )
            else:
                file_path = self.documents_dir / filename
        else:
            file_path = self.documents_dir / filename
        
        # Ensure parent directory exists
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: file_path.parent.mkdir(parents=True, exist_ok=True)
        )
        
        # Save content
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Add file size to metadata
        metadata['file_size'] = len(content)
        
        # Save metadata
        metadata_path = self._get_metadata_path(file_path)
        await self._save_metadata(metadata_path, metadata)
        
        # Return file URI
        uri = self._path_to_uri(file_path)
        logger.info(f"Document saved successfully: {uri}")
        return uri
    
    async def update_document(self, 
                           uri: str, 
                           content: bytes, 
                           metadata: Dict[str, Any]):
        """
        Update an existing document in the file system.
        
        Args:
            uri: The file URI to update
            content: New file content
            metadata: New metadata
        """
        logger.info(f"Updating document in file system: {uri}")
        
        file_path = self._uri_to_path(uri)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {uri}")
        
        # Update content
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Update metadata
        metadata['file_size'] = len(content)
        metadata_path = self._get_metadata_path(file_path)
        await self._save_metadata(metadata_path, metadata)
        
        logger.info(f"Document updated successfully: {uri}")
    
    async def delete_document(self, uri: str):
        """
        Delete a document from the file system.
        
        Args:
            uri: The file URI to delete
        """
        logger.info(f"Deleting document from file system: {uri}")
        
        file_path = self._uri_to_path(uri)
        metadata_path = self._get_metadata_path(file_path)
        
        # Delete document
        if file_path.exists():
            await asyncio.get_event_loop().run_in_executor(
                None, file_path.unlink
            )
        
        # Delete metadata
        if metadata_path.exists():
            await asyncio.get_event_loop().run_in_executor(
                None, metadata_path.unlink
            )
        
        # Clean up empty directories if configured
        if self.preserve_structure:
            try:
                # Try to remove the parent directory if empty
                await asyncio.get_event_loop().run_in_executor(
                    None, file_path.parent.rmdir
                )
            except OSError:
                pass  # Directory not empty
        
        logger.info(f"Document deleted successfully: {uri}")
    
    async def get_document(self, uri: str) -> Optional[DocumentMetadata]:
        """
        Get metadata for a document in the file system.
        
        Args:
            uri: The file URI
            
        Returns:
            DocumentMetadata if found, None otherwise
        """
        logger.info(f"Getting document metadata from file system: {uri}")
        
        file_path = self._uri_to_path(uri)
        
        if not file_path.exists():
            return None
        
        # Read metadata
        metadata_path = self._get_metadata_path(file_path)
        metadata = await self._load_metadata(metadata_path)
        
        # Get file stats
        stat = await asyncio.get_event_loop().run_in_executor(
            None, file_path.stat
        )
        
        return DocumentMetadata(
            id=uri,
            name=file_path.name,
            uri=uri,
            size=stat.st_size,
            metadata=metadata
        )
    
    async def list_documents(self, prefix: str = "") -> List[DocumentMetadata]:
        """
        List all documents in the file system storage with optional prefix filter.
        
        Args:
            prefix: Filter documents by path prefix
            
        Returns:
            List of DocumentMetadata objects
        """
        logger.info(f"Listing documents in file system with prefix: {prefix}")
        
        documents = []
        
        # Walk through documents directory
        for root, dirs, files in os.walk(self.documents_dir):
            for file in files:
                file_path = Path(root) / file
                
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
        
        logger.info(f"Found {len(documents)} documents")
        return documents
    
    async def cleanup(self):
        """Clean up file system resources."""
        logger.info("Cleaning up file system storage")
        # Nothing to clean up for file system storage
        pass
    
    # Helper methods
    def _uri_to_path(self, uri: str) -> Path:
        """Convert a URI to a Path object.
        
        Handles both file:// URIs and simple paths.
        For simple paths, treats them as relative to the documents directory.
        """
        parsed = urlparse(uri)
        
        if parsed.scheme == 'file':
            # Handle file:// URI
            path = unquote(parsed.path)
            if os.name == 'nt' and path.startswith('/'):
                # Windows: file:///C:/path -> C:/path
                path = path[1:]
            return Path(path)
        elif parsed.scheme in ('', None):
            # Handle simple paths (no scheme)
            # URI format is expected to be: kb_name/filename
            # Remove the kb_name prefix if present (for backwards compatibility)
            if '/' in uri:
                # Extract just the filename from kb_name/filename format
                filename = uri.split('/', 1)[1]
                return self.documents_dir / filename
            else:
                # Treat as relative to documents directory
                return self.documents_dir / uri
        else:
            raise ValueError(f"Invalid URI scheme: {uri}")
    
    def _path_to_uri(self, path: Path) -> str:
        """Convert a Path object to a URI.
        
        Returns a simple path that matches the database format.
        The database stores URIs as 'kb_name/filename' without the 'documents' folder.
        """
        # If path is inside documents directory, return just kb_name/filename
        if path.is_absolute() and path.is_relative_to(self.documents_dir):
            filename = path.name  # Just the filename, not the full path
            # Return the URI with kb_name prefix to match database format
            return f"{self.kb_name}/{filename}"
        else:
            # Return absolute path as a simple string
            return str(path)
    
    def _get_metadata_path(self, document_path: Path) -> Path:
        """Get the metadata file path for a document."""
        # Use the same name with metadata extension
        metadata_filename = f"{document_path.name}.metadata.{self.metadata_format}"
        
        # Store metadata in parallel directory structure
        relative_path = document_path.relative_to(self.documents_dir)
        metadata_path = self.metadata_dir / relative_path.parent / metadata_filename
        
        return metadata_path
    
    async def _save_metadata(self, path: Path, metadata: Dict[str, Any]):
        """Save metadata to file."""
        # Create parent directory if needed
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: path.parent.mkdir(parents=True, exist_ok=True)
        )
        
        if self.metadata_format == 'json':
            content = json.dumps(metadata, indent=2)
        else:  # yaml
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
            return json.loads(content)
        else:  # yaml
            return yaml.safe_load(content)