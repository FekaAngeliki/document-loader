import logging
from typing import Dict, Any, List, Optional

from ..abstractions.rag_system import RAGSystem, DocumentMetadata

logger = logging.getLogger(__name__)

class MockRAGSystem(RAGSystem):
    """Mock implementation of RAGSystem for testing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.documents = {}
    
    async def initialize(self):
        """Initialize the mock RAG system."""
        logger.info("Initializing mock RAG system")
    
    async def upload_document(self, 
                           content: bytes, 
                           filename: str, 
                           metadata: Dict[str, Any]) -> str:
        """Upload a document to the mock RAG system."""
        uri = f"/mock/{filename}"
        self.documents[uri] = {
            "content": content,
            "filename": filename,
            "metadata": metadata
        }
        logger.info(f"Uploaded document: {uri}")
        return uri
    
    async def update_document(self, 
                           uri: str, 
                           content: bytes, 
                           metadata: Dict[str, Any]):
        """Update an existing document."""
        if uri in self.documents:
            self.documents[uri]["content"] = content
            self.documents[uri]["metadata"] = metadata
            logger.info(f"Updated document: {uri}")
        else:
            raise ValueError(f"Document not found: {uri}")
    
    async def delete_document(self, uri: str):
        """Delete a document from the mock RAG system."""
        if uri in self.documents:
            del self.documents[uri]
            logger.info(f"Deleted document: {uri}")
        else:
            raise ValueError(f"Document not found: {uri}")
    
    async def get_document(self, uri: str) -> Optional[DocumentMetadata]:
        """Get metadata for a document."""
        if uri in self.documents:
            doc = self.documents[uri]
            return DocumentMetadata(
                id=uri,
                name=doc["filename"],
                uri=uri,
                size=len(doc["content"]),
                metadata=doc["metadata"]
            )
        return None
    
    async def list_documents(self, prefix: str = "") -> List[DocumentMetadata]:
        """List all documents in the mock RAG system."""
        docs = []
        for uri, doc in self.documents.items():
            if uri.startswith(prefix):
                docs.append(DocumentMetadata(
                    id=uri,
                    name=doc["filename"],
                    uri=uri,
                    size=len(doc["content"]),
                    metadata=doc["metadata"]
                ))
        return docs
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up mock RAG system")