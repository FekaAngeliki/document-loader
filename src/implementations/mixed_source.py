from typing import List, Dict, Any, AsyncIterator
from datetime import datetime

from ..abstractions.file_source import FileSource, FileMetadata
from ..core.factory import SourceFactory


class MixedSource(FileSource):
    """Mixed source implementation that combines multiple file sources."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.sources_config = config.get('sources', [])
        self.sources: List[FileSource] = []
        self.source_factory = SourceFactory()
        
        # Global exclusion settings
        self.exclude_extensions = config.get('exclude_extensions', [])
        self.exclude_patterns = config.get('exclude_patterns', [])
        
        # Processing pipeline for excluded files
        self.processing_pipeline = None
        if 'processing_pipeline' in config:
            from ..core.processing_pipeline import ProcessingPipeline
            self.processing_pipeline = ProcessingPipeline(config['processing_pipeline'])
        
        if not self.sources_config:
            raise ValueError("Mixed source requires at least one source configuration")
    
    async def initialize(self):
        """Initialize all configured sources."""
        for source_config in self.sources_config:
            source_type = source_config.get('type')
            source_settings = source_config.get('config', {})
            
            if not source_type:
                raise ValueError("Each source in mixed_source must specify a 'type'")
            
            try:
                source = self.source_factory.create(source_type, source_settings)
                await source.initialize()
                self.sources.append(source)
            except Exception as e:
                raise ValueError(f"Failed to initialize source '{source_type}': {e}")
    
    async def list_files(self, path: str = "") -> List[FileMetadata]:
        """List all files from all sources."""
        all_files = []
        
        for i, source in enumerate(self.sources):
            try:
                source_files = await source.list_files(path)
                # Add source index to URI to make them unique across sources
                for file_metadata in source_files:
                    # Check if file should be excluded before processing
                    if self._should_exclude_file(file_metadata.uri):
                        continue
                    
                    # Prefix URI with source index to ensure uniqueness
                    file_metadata.uri = f"source_{i}://{file_metadata.uri}"
                    all_files.append(file_metadata)
            except Exception as e:
                # Log error but continue with other sources
                print(f"Warning: Failed to list files from source {i}: {e}")
                continue
        
        return all_files
    
    async def get_file_content(self, uri: str) -> bytes:
        """Get the content of a file from the appropriate source."""
        source_index, original_uri = self._parse_mixed_uri(uri)
        source = self.sources[source_index]
        return await source.get_file_content(original_uri)
    
    async def get_file_metadata(self, uri: str) -> FileMetadata:
        """Get metadata for a file from the appropriate source."""
        source_index, original_uri = self._parse_mixed_uri(uri)
        source = self.sources[source_index]
        metadata = await source.get_file_metadata(original_uri)
        # Restore the mixed URI
        metadata.uri = uri
        return metadata
    
    async def exists(self, uri: str) -> bool:
        """Check if a file exists in the appropriate source."""
        try:
            source_index, original_uri = self._parse_mixed_uri(uri)
            source = self.sources[source_index]
            return await source.exists(original_uri)
        except (ValueError, IndexError):
            return False
    
    async def cleanup(self):
        """Clean up all sources."""
        for source in self.sources:
            try:
                await source.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup source: {e}")
    
    async def stream_files(self, path: str = "") -> AsyncIterator[FileMetadata]:
        """Stream files from all sources."""
        for i, source in enumerate(self.sources):
            try:
                async for file_metadata in source.stream_files(path):
                    # Check if file should be excluded before processing
                    if self._should_exclude_file(file_metadata.uri):
                        continue
                    
                    # Prefix URI with source index
                    file_metadata.uri = f"source_{i}://{file_metadata.uri}"
                    yield file_metadata
            except Exception as e:
                print(f"Warning: Failed to stream files from source {i}: {e}")
                continue
    
    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if a file should be excluded based on exclusion rules."""
        import os
        from pathlib import Path
        import fnmatch
        
        # Check extension exclusions
        if self.exclude_extensions:
            file_ext = Path(file_path).suffix.lower()
            if file_ext in [ext.lower() for ext in self.exclude_extensions]:
                return True
        
        # Check pattern exclusions
        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                    return True
        
        return False
    
    async def process_excluded_files(self) -> List[FileMetadata]:
        """Process files that were excluded but can be processed with external tools."""
        if not self.processing_pipeline:
            return []
        
        processed_files = []
        
        for i, source in enumerate(self.sources):
            try:
                # Get all files from source (including excluded ones)
                all_files = await source.list_files()
                
                for file_metadata in all_files:
                    # Check if this file was excluded but should be processed
                    if (self._should_exclude_file(file_metadata.uri) and 
                        self.processing_pipeline.should_process(file_metadata.uri)):
                        
                        # Get file content for processing
                        content = await source.get_file_content(file_metadata.uri)
                        
                        # Queue for processing
                        await self.processing_pipeline.queue_file(file_metadata, content)
                
            except Exception as e:
                print(f"Warning: Failed to collect excluded files from source {i}: {e}")
                continue
        
        # Process the queue and get processed files
        if self.processing_pipeline.processing_queue:
            print(f"Processing {len(self.processing_pipeline.processing_queue)} excluded files...")
            processed = await self.processing_pipeline.process_queue()
            
            # Add source prefixes to processed files
            for file_metadata in processed:
                file_metadata.uri = f"processed://{file_metadata.uri}"
                processed_files.append(file_metadata)
        
        return processed_files
    
    async def list_files_with_processing(self, path: str = "") -> List[FileMetadata]:
        """List files including both normal and processed files."""
        # Get normally included files
        normal_files = await self.list_files(path)
        
        # Get processed files from excluded extensions
        processed_files = await self.process_excluded_files()
        
        # Combine both lists
        all_files = normal_files + processed_files
        
        return all_files
    
    def _parse_mixed_uri(self, uri: str) -> tuple[int, str]:
        """Parse a mixed URI to extract source index and original URI."""
        if not uri.startswith("source_"):
            raise ValueError(f"Invalid mixed source URI format: {uri}")
        
        try:
            # Format: source_N://original_uri
            parts = uri.split("://", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid mixed source URI format: {uri}")
            
            source_part = parts[0]  # source_N
            original_uri = parts[1]
            
            source_index = int(source_part.replace("source_", ""))
            
            if source_index >= len(self.sources):
                raise ValueError(f"Source index {source_index} out of range")
            
            return source_index, original_uri
            
        except (ValueError, IndexError) as e:
            raise ValueError(f"Failed to parse mixed source URI '{uri}': {e}")
    
    def get_source_info(self) -> List[Dict[str, Any]]:
        """Get information about all configured sources."""
        return [
            {
                "index": i,
                "type": config.get("type"),
                "config": config.get("config", {})
            }
            for i, config in enumerate(self.sources_config)
        ]