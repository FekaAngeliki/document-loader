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
            # Add RAG system types here as they are implemented
        }
    
    def create(self, rag_type: str, config: Dict[str, Any]) -> RAGSystem:
        """Create a RAG system instance."""
        if rag_type not in self.systems:
            # For now, return a mock RAG system
            from ..implementations.mock_rag_system import MockRAGSystem
            return MockRAGSystem(config)
        
        module_path, class_name = self.systems[rag_type].rsplit('.', 1)
        module = importlib.import_module(module_path)
        rag_class = getattr(module, class_name)
        
        return rag_class(config)