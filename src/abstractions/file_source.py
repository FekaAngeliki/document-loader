from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator
from datetime import datetime

@dataclass
class FileMetadata:
    """Metadata for a file."""
    uri: str
    size: int
    created_at: datetime
    modified_at: datetime
    content_type: str

class FileSource(ABC):
    """Abstract interface for file sources."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def initialize(self):
        """Initialize the file source."""
        pass
    
    @abstractmethod
    async def list_files(self, path: str = "") -> List[FileMetadata]:
        """List all files in the source."""
        pass
    
    @abstractmethod
    async def get_file_content(self, uri: str) -> bytes:
        """Get the content of a file."""
        pass
    
    @abstractmethod
    async def get_file_metadata(self, uri: str) -> FileMetadata:
        """Get metadata for a file."""
        pass
    
    @abstractmethod
    async def exists(self, uri: str) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Clean up resources."""
        pass
    
    async def stream_files(self, path: str = "") -> AsyncIterator[FileMetadata]:
        """Stream files for large directories."""
        for file_metadata in await self.list_files(path):
            yield file_metadata