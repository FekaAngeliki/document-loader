import os
import aiofiles
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import mimetypes

from ..abstractions.file_source import FileSource, FileMetadata

class FileSystemSource(FileSource):
    """File system implementation of FileSource."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.root_path = Path(config.get('root_path', '.'))
        self.include_patterns = config.get('include_patterns', ['*'])
        self.exclude_patterns = config.get('exclude_patterns', [])
        self.include_extensions = config.get('include_extensions', [])
        self.exclude_extensions = config.get('exclude_extensions', [])
    
    async def initialize(self):
        """Initialize the file system source."""
        if not self.root_path.exists():
            raise ValueError(f"Root path {self.root_path} does not exist")
    
    async def list_files(self, path: str = "") -> List[FileMetadata]:
        """List all files in the source."""
        files = []
        search_path = self.root_path / path
        
        for file_path in search_path.rglob('*'):
            if file_path.is_file():
                # Check include/exclude patterns
                relative_path = file_path.relative_to(self.root_path)
                if self._should_include(str(relative_path)):
                    metadata = await self._get_file_metadata(file_path)
                    files.append(metadata)
        
        return files
    
    async def get_file_content(self, uri: str) -> bytes:
        """Get the content of a file."""
        file_path = Path(uri)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {uri} not found")
        
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    async def get_file_metadata(self, uri: str) -> FileMetadata:
        """Get metadata for a file."""
        file_path = Path(uri)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {uri} not found")
        
        return await self._get_file_metadata(file_path)
    
    async def exists(self, uri: str) -> bool:
        """Check if a file exists."""
        file_path = Path(uri)
        return file_path.exists() and file_path.is_file()
    
    async def cleanup(self):
        """Clean up resources."""
        pass
    
    def _should_include(self, relative_path: str) -> bool:
        """Check if a file should be included based on patterns and extensions."""
        path = Path(relative_path)
        
        # Check exclude extensions first
        if self.exclude_extensions:
            file_extension = path.suffix.lower()
            for ext in self.exclude_extensions:
                # Normalize the extension (add dot if not present)
                ext = ext.lower()
                if not ext.startswith('.'):
                    ext = '.' + ext
                if file_extension == ext:
                    return False
        
        # Check include extensions - if specified, file must match one
        if self.include_extensions:
            file_extension = path.suffix.lower()
            match_found = False
            for ext in self.include_extensions:
                # Normalize the extension (add dot if not present)
                ext = ext.lower()
                if not ext.startswith('.'):
                    ext = '.' + ext
                if file_extension == ext:
                    match_found = True
                    break
            if not match_found:
                return False
        
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if path.match(pattern):
                return False
        
        # Check include patterns
        for pattern in self.include_patterns:
            if path.match(pattern):
                return True
        
        # If no include patterns defined, include by default
        return len(self.include_patterns) == 0
    
    async def _get_file_metadata(self, file_path: Path) -> FileMetadata:
        """Get metadata for a file path."""
        stat = file_path.stat()
        relative_path = file_path.relative_to(self.root_path)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        return FileMetadata(
            uri=str(file_path.absolute()),
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            content_type=mime_type
        )