from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class DocumentMetadata:
    """Metadata for a document in the RAG system."""
    id: str
    name: str
    uri: str
    size: int
    metadata: Dict[str, Any]

class RAGSystem(ABC):
    """Abstract interface for RAG systems."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def initialize(self):
        """Initialize the RAG system connection."""
        pass
    
    @abstractmethod
    async def upload_document(self, 
                           content: bytes, 
                           filename: str, 
                           metadata: Dict[str, Any]) -> str:
        """Upload a document to the RAG system.
        
        Returns:
            The URI of the uploaded document.
        """
        pass
    
    @abstractmethod
    async def update_document(self, 
                           uri: str, 
                           content: bytes, 
                           metadata: Dict[str, Any]):
        """Update an existing document."""
        pass
    
    @abstractmethod
    async def delete_document(self, uri: str):
        """Delete a document from the RAG system."""
        pass
    
    @abstractmethod
    async def get_document(self, uri: str) -> Optional[DocumentMetadata]:
        """Get metadata for a document."""
        pass
    
    @abstractmethod
    async def list_documents(self, prefix: str = "") -> List[DocumentMetadata]:
        """List all documents in the RAG system."""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Clean up resources."""
        pass