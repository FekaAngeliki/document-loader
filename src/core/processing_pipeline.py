#!/usr/bin/env python3
"""
Processing Pipeline for External Tool Integration

This module handles files that need external tool processing before inclusion
in the knowledge base (e.g., .ppt/.pptx conversion to text/markdown).
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import subprocess
import json

from ..abstractions.file_source import FileMetadata


class ProcessingPipeline:
    """Manages external tool processing for excluded file types."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.queue_extensions = config.get('queue_extensions', [])
        self.processors = config.get('processors', {})
        self.output_format = config.get('output_format', '.txt')
        self.processing_dir = Path(config.get('processing_dir', tempfile.gettempdir()))
        self.processed_dir = Path(config.get('processed_dir', './processed'))
        self.processing_queue = []
        
        # Ensure directories exist
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def should_process(self, file_path: str) -> bool:
        """Check if a file should be queued for processing."""
        if not self.enabled:
            return False
        
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.queue_extensions
    
    async def queue_file(self, file_metadata: FileMetadata, source_content: bytes) -> bool:
        """Queue a file for processing."""
        if not self.should_process(file_metadata.uri):
            return False
        
        file_ext = Path(file_metadata.uri).suffix.lower()
        processor = self.processors.get(file_ext)
        
        if not processor:
            print(f"Warning: No processor configured for {file_ext}")
            return False
        
        # Create processing entry
        processing_entry = {
            'original_metadata': file_metadata,
            'content': source_content,
            'processor': processor,
            'queued_at': datetime.now(),
            'status': 'queued'
        }
        
        self.processing_queue.append(processing_entry)
        print(f"✓ Queued {file_metadata.uri} for processing with {processor}")
        return True
    
    async def process_queue(self) -> List[FileMetadata]:
        """Process all queued files and return processed file metadata."""
        if not self.processing_queue:
            return []
        
        processed_files = []
        
        for entry in self.processing_queue:
            try:
                entry['status'] = 'processing'
                processed_metadata = await self._process_file(entry)
                
                if processed_metadata:
                    processed_files.append(processed_metadata)
                    entry['status'] = 'completed'
                    print(f"✓ Processed: {entry['original_metadata'].uri}")
                else:
                    entry['status'] = 'failed'
                    print(f"❌ Failed: {entry['original_metadata'].uri}")
                    
            except Exception as e:
                entry['status'] = 'failed'
                print(f"❌ Error processing {entry['original_metadata'].uri}: {e}")
        
        # Clear completed/failed entries
        self.processing_queue = [e for e in self.processing_queue if e['status'] == 'queued']
        
        return processed_files
    
    async def _process_file(self, entry: Dict[str, Any]) -> Optional[FileMetadata]:
        """Process a single file using the configured processor."""
        original_metadata = entry['original_metadata']
        content = entry['content']
        processor = entry['processor']
        
        # Generate unique processing file names
        original_path = Path(original_metadata.uri)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        processing_id = f"{timestamp}_{original_path.stem}"
        
        # Create temporary input file
        input_file = self.processing_dir / f"{processing_id}{original_path.suffix}"
        output_file = self.processed_dir / f"{processing_id}{self.output_format}"
        
        try:
            # Write content to temporary file
            with open(input_file, 'wb') as f:
                f.write(content)
            
            # Process file based on processor type
            success = await self._run_processor(processor, input_file, output_file)
            
            if success and output_file.exists():
                # Create metadata for processed file
                stat = output_file.stat()
                
                processed_metadata = FileMetadata(
                    uri=str(output_file.absolute()),
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    content_type='text/plain' if self.output_format == '.txt' else 'text/markdown'
                )
                
                return processed_metadata
            
        finally:
            # Cleanup temporary input file
            if input_file.exists():
                input_file.unlink()
        
        return None
    
    async def _run_processor(self, processor: str, input_file: Path, output_file: Path) -> bool:
        """Run the specific processor on the input file."""
        try:
            if processor == "ppt_to_text_converter":
                return await self._convert_ppt_to_text(input_file, output_file)
            elif processor == "pptx_to_markdown_converter":
                return await self._convert_pptx_to_markdown(input_file, output_file)
            elif processor == "pdf_to_text_converter":
                return await self._convert_pdf_to_text(input_file, output_file)
            elif processor == "custom_processor":
                return await self._run_custom_processor(input_file, output_file)
            else:
                print(f"Unknown processor: {processor}")
                return False
                
        except Exception as e:
            print(f"Error running processor {processor}: {e}")
            return False
    
    async def _convert_ppt_to_text(self, input_file: Path, output_file: Path) -> bool:
        """Convert PPT to text using custom processor (placeholder)."""
        try:
            # Placeholder implementation - pass through for now
            # Custom package integration would go here
            print(f"✓ PPT processing placeholder: {input_file} -> {output_file}")
            
            # Create placeholder output file for testing flow
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Processed PPT: {input_file.name}\n\nContent would be extracted by custom package.")
            
            return True
            
        except Exception as e:
            print(f"PPT conversion error: {e}")
        
        return False
    
    async def _convert_pptx_to_markdown(self, input_file: Path, output_file: Path) -> bool:
        """Convert PPTX to Markdown using custom processor (placeholder)."""
        try:
            # Placeholder implementation - pass through for now
            # Custom package integration would go here
            print(f"✓ PPTX processing placeholder: {input_file} -> {output_file}")
            
            # Create placeholder output file for testing flow
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Processed PPTX: {input_file.name}\n\nContent would be extracted by custom package and converted to markdown.")
            
            return True
                
        except Exception as e:
            print(f"PPTX to Markdown conversion error: {e}")
        
        return False
    
    async def _convert_pdf_to_text(self, input_file: Path, output_file: Path) -> bool:
        """Convert PDF to text using pdftotext."""
        try:
            cmd = ['pdftotext', str(input_file), str(output_file)]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except FileNotFoundError:
            print("pdftotext not found. Please install poppler-utils for PDF conversion.")
        except Exception as e:
            print(f"PDF conversion error: {e}")
        
        return False
    
    async def _run_custom_processor(self, input_file: Path, output_file: Path) -> bool:
        """Run a custom processing script."""
        try:
            # Example: Run a custom script that takes input and output paths
            script_path = self.config.get('custom_script_path', './process_file.sh')
            
            cmd = [script_path, str(input_file), str(output_file)]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            print(f"Custom processor error: {e}")
        
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current processing queue status."""
        status_counts = {}
        for entry in self.processing_queue:
            status = entry['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_queued': len(self.processing_queue),
            'status_breakdown': status_counts,
            'processors_configured': list(self.processors.keys()),
            'queue_extensions': self.queue_extensions
        }


class ProcessingIntegrator:
    """Integrates processing pipeline with mixed_source."""
    
    def __init__(self, mixed_source_config: Dict[str, Any]):
        self.config = mixed_source_config
        self.pipeline = None
        
        if 'processing_pipeline' in mixed_source_config:
            self.pipeline = ProcessingPipeline(mixed_source_config['processing_pipeline'])
    
    async def process_excluded_files(self, excluded_files: List[Tuple[FileMetadata, bytes]]) -> List[FileMetadata]:
        """Process files that were excluded but need processing."""
        if not self.pipeline:
            return []
        
        processed_files = []
        
        # Queue files for processing
        for file_metadata, content in excluded_files:
            await self.pipeline.queue_file(file_metadata, content)
        
        # Process the queue
        if self.pipeline.processing_queue:
            print(f"Processing {len(self.pipeline.processing_queue)} excluded files...")
            processed = await self.pipeline.process_queue()
            processed_files.extend(processed)
        
        return processed_files
    
    def should_process_excluded(self, file_path: str) -> bool:
        """Check if an excluded file should be processed."""
        return self.pipeline and self.pipeline.should_process(file_path)