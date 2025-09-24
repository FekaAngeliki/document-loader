from typing import Dict, Any
import importlib

from ..abstractions.file_source import FileSource
from ..abstractions.rag_system import RAGSystem

class SourceFactory:
    """Factory for creating file source instances."""
    
    def __init__(self):
        self.sources = {
            "file_system": "src.implementations.file_system_source.FileSystemSource",
            "sharepoint": "src.implementations.sharepoint_source.SharePointSource",
            "enterprise_sharepoint": "src.implementations.enterprise_sharepoint_source.EnterpriseSharePointSource",
            "mixed_source": "src.implementations.mixed_source.MixedSource",
            # Add more source types here as they are implemented
        }
    
    def create(self, source_type: str, config: Dict[str, Any]) -> FileSource:
        """Create a file source instance."""
        if source_type not in self.sources:
            raise ValueError(f"Unknown source type: {source_type}")
        
        module_path, class_name = self.sources[source_type].rsplit('.', 1)
        module = importlib.import_module(module_path)
        source_class = getattr(module, class_name)
        
        return source_class(config)

class RAGFactory:
    """Factory for creating RAG system instances."""
    
    def __init__(self):
        self.systems = {
            "mock": "src.implementations.mock_rag_system.MockRAGSystem",
            "azure_blob": "src.implementations.azure_blob_rag_system.AzureBlobRAGSystem",
            "file_system_storage": "src.implementations.file_system_storage.FileSystemStorage",
            # Add more RAG system types here as they are implemented
        }
    
    def create(self, rag_type: str, config: Dict[str, Any]) -> RAGSystem:
        """Create a RAG system instance."""
        if rag_type not in self.systems:
            raise ValueError(f"Unknown RAG type: {rag_type}")
        
        module_path, class_name = self.systems[rag_type].rsplit('.', 1)
        module = importlib.import_module(module_path)
        rag_class = getattr(module, class_name)
        
        return rag_class(config)

class Factory:
    """Unified factory for creating sources and RAG systems."""
    
    def __init__(self, repository):
        self.repository = repository
        self.source_factory = SourceFactory()
        self.rag_factory = RAGFactory()
    
    async def create_source(self, source_type: str, config: Dict[str, Any]) -> FileSource:
        """Create a file source instance."""
        source = self.source_factory.create(source_type, config)
        
        # Set repository for sources that support delta sync
        if hasattr(source, 'set_repository'):
            source.set_repository(self.repository)
        
        return source
    
    async def create_rag(self, rag_type: str, config: Dict[str, Any]) -> RAGSystem:
        """Create a RAG system instance."""
        return self.rag_factory.create(rag_type, config)