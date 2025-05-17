import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from ..abstractions.file_source import FileSource
from ..abstractions.rag_system import RAGSystem
from ..data.repository import Repository
from ..data.models import SyncRun, FileRecord, SyncRunStatus, FileStatus
from .change_detector import ChangeDetector, ChangeType
from .file_processor import FileProcessor
from .factory import SourceFactory, RAGFactory

logger = logging.getLogger(__name__)

class BatchRunner:
    """Manages synchronization runs for knowledge bases."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self.change_detector = ChangeDetector(repository)
        self.file_processor = FileProcessor()
        self.source_factory = SourceFactory()
        self.rag_factory = RAGFactory()
    
    async def sync_knowledge_base(self, kb_name: str):
        """Synchronize a knowledge base."""
        try:
            # Get knowledge base configuration
            kb = await self.repository.get_knowledge_base_by_name(kb_name)
            if not kb:
                raise ValueError(f"Knowledge base '{kb_name}' not found")
            
            # Create sync run
            sync_run_id = await self.repository.create_sync_run(kb.id, 'running')
            sync_run = SyncRun(
                id=sync_run_id,
                knowledge_base_id=kb.id,
                start_time=datetime.now(),
                status=SyncRunStatus.RUNNING.value
            )
            
            try:
                # Create source and RAG system instances
                source = self.source_factory.create(kb.source_type, kb.source_config)
                rag = self.rag_factory.create(kb.rag_type, kb.rag_config)
                
                await source.initialize()
                await rag.initialize()
                
                # List files from source
                source_files = await source.list_files()
                logger.info(f"Found {len(source_files)} files in source")
                
                # Detect changes
                changes = await self.change_detector.detect_changes(source_files, kb.id)
                change_summary = self.change_detector.get_change_summary(changes)
                
                logger.info(f"Change summary: {change_summary}")
                
                # Process changes
                processed_count = 0
                error_count = 0
                
                for change in changes:
                    if change.change_type in [ChangeType.NEW, ChangeType.MODIFIED]:
                        try:
                            await self._process_file(
                                source, rag, kb.name, sync_run.id, change
                            )
                            processed_count += 1
                        except Exception as e:
                            logger.error(f"Error processing file {change.uri}: {e}")
                            error_count += 1
                
                # Update sync run with results
                sync_run.end_time = datetime.now()
                sync_run.status = SyncRunStatus.COMPLETED.value
                sync_run.total_files = len(source_files)
                sync_run.new_files = change_summary["new"]
                sync_run.modified_files = change_summary["modified"]
                sync_run.deleted_files = change_summary["deleted"]
                
                await self.repository.update_sync_run(sync_run)
                
                logger.info(f"Sync completed: {processed_count} files processed, {error_count} errors")
                
            except Exception as e:
                # Update sync run with error
                sync_run.end_time = datetime.now()
                sync_run.status = SyncRunStatus.FAILED.value
                sync_run.error_message = str(e)
                await self.repository.update_sync_run(sync_run)
                
                logger.error(f"Sync failed: {e}")
                raise
            
            finally:
                # Clean up resources
                await source.cleanup()
                await rag.cleanup()
        
        except Exception as e:
            logger.error(f"Fatal error in sync: {e}")
            raise
    
    async def _process_file(self, 
                          source: FileSource, 
                          rag: RAGSystem,
                          kb_name: str,
                          sync_run_id: int,
                          change):
        """Process a single file change."""
        try:
            # Get file content
            content = await source.get_file_content(change.uri)
            
            # Process file
            file_hash, uuid_filename, rag_uri = await self.file_processor.process_file(
                content, change.uri, kb_name
            )
            
            # Upload to RAG system
            metadata = {
                "original_uri": change.uri,
                "kb_name": kb_name,
                "file_hash": file_hash,
                "source_modified_at": change.metadata.modified_at.isoformat()
            }
            
            if change.change_type == ChangeType.NEW:
                await rag.upload_document(content, uuid_filename, metadata)
                status = FileStatus.NEW.value
            else:  # MODIFIED
                if change.existing_record and change.existing_record.rag_uri:
                    await rag.update_document(change.existing_record.rag_uri, content, metadata)
                else:
                    await rag.upload_document(content, uuid_filename, metadata)
                status = FileStatus.MODIFIED.value
            
            # Create file record
            file_record = FileRecord(
                sync_run_id=sync_run_id,
                original_uri=change.uri,
                rag_uri=rag_uri,
                file_hash=file_hash,
                uuid_filename=uuid_filename,
                upload_time=datetime.now(),
                file_size=change.metadata.size,
                status=status
            )
            
            await self.repository.create_file_record_original(file_record)
            
            logger.info(f"Processed file {change.uri} ({status})")
            
        except Exception as e:
            # Create error record
            file_record = FileRecord(
                sync_run_id=sync_run_id,
                original_uri=change.uri,
                rag_uri="",
                file_hash="",
                uuid_filename="",
                upload_time=datetime.now(),
                file_size=change.metadata.size if change.metadata else 0,
                status=FileStatus.ERROR.value,
                error_message=str(e)
            )
            
            await self.repository.create_file_record_original(file_record)
            raise