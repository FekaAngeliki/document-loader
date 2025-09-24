"""
Multi-Source Batch Runner

Orchestrates synchronization of multiple sources into a single Knowledge Base and RAG system.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box

from ..abstractions.file_source import FileSource
from ..abstractions.rag_system import RAGSystem
from ..data.repository import Repository
from ..data.multi_source_models import (
    MultiSourceKnowledgeBase, 
    MultiSourceSyncRun, 
    EnhancedFileRecord,
    SourceSyncStatus,
    SyncMode
)
from .change_detector import ChangeDetector, ChangeType
from .file_processor import FileProcessor
from .factory import Factory

logger = logging.getLogger(__name__)
console = Console()

class MultiSourceBatchRunner:
    """Orchestrates batch processing for multi-source knowledge bases."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self.change_detector = ChangeDetector(repository)
        self.file_processor = FileProcessor()
        self.factory = Factory(repository)
    
    async def sync_multi_source_knowledge_base(self, 
                                             kb_name: str,
                                             sync_mode: SyncMode = SyncMode.PARALLEL,
                                             source_ids: Optional[List[str]] = None,
                                             progress_callback: Optional[Callable] = None):
        """Synchronize a multi-source knowledge base."""
        
        console.print(f"\n[bold cyan]Starting multi-source sync for: {kb_name}[/bold cyan]")
        console.print(f"[dim]Sync mode: {sync_mode.value}[/dim]")
        
        # Load multi-source KB configuration
        multi_kb = await self._load_multi_source_kb(kb_name)
        if not multi_kb:
            raise ValueError(f"Multi-source knowledge base '{kb_name}' not found")
        
        # Filter sources if specified
        sources_to_sync = multi_kb.sources
        if source_ids:
            sources_to_sync = [s for s in multi_kb.sources if s.source_id in source_ids]
            console.print(f"[dim]Syncing selected sources: {', '.join(source_ids)}[/dim]")
        
        # Create sync run
        sync_run = await self._create_multi_source_sync_run(multi_kb, sync_mode, sources_to_sync)
        
        try:
            # Initialize RAG system (shared across all sources)
            rag = await self.factory.create_rag(multi_kb.rag_type, multi_kb.rag_config)
            await rag.initialize()
            
            # Execute sync based on mode
            if sync_mode == SyncMode.PARALLEL:
                await self._sync_sources_parallel(multi_kb, sources_to_sync, rag, sync_run)
            elif sync_mode == SyncMode.SEQUENTIAL:
                await self._sync_sources_sequential(multi_kb, sources_to_sync, rag, sync_run)
            else:
                raise ValueError(f"Unsupported sync mode: {sync_mode}")
            
            # Finalize sync run
            await self._finalize_sync_run(sync_run, success=True)
            
            console.print(f"\n[bold green]✅ Multi-source sync completed successfully[/bold green]")
            
        except Exception as e:
            logger.error(f"Multi-source sync failed: {e}")
            await self._finalize_sync_run(sync_run, success=False, error=str(e))
            console.print(f"\n[bold red]❌ Multi-source sync failed: {e}[/bold red]")
            raise
        finally:
            if 'rag' in locals():
                await rag.cleanup()
    
    async def _sync_sources_parallel(self, 
                                   multi_kb: MultiSourceKnowledgeBase,
                                   sources: List,
                                   rag: RAGSystem,
                                   sync_run: MultiSourceSyncRun):
        """Sync all sources in parallel."""
        
        console.print(f"\n[bold]🔄 Parallel sync of {len(sources)} sources[/bold]")
        
        # Create tasks for each source
        tasks = []
        source_statuses = {}
        
        for source_def in sources:
            status = SourceSyncStatus(source_id=source_def.source_id)
            source_statuses[source_def.source_id] = status
            
            task = asyncio.create_task(
                self._sync_single_source(multi_kb, source_def, rag, sync_run, status)
            )
            tasks.append(task)
        
        # Execute all tasks in parallel with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # Add progress tasks
            progress_tasks = {}
            for source_def in sources:
                task_id = progress.add_task(
                    f"[cyan]{source_def.source_id}[/cyan]", 
                    total=100
                )
                progress_tasks[source_def.source_id] = task_id
            
            # Wait for completion
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update progress to complete
            for source_id, task_id in progress_tasks.items():
                progress.update(task_id, completed=100)
        
        # Process results
        for i, result in enumerate(results):
            source_def = sources[i]
            if isinstance(result, Exception):
                logger.error(f"Source {source_def.source_id} failed: {result}")
                source_statuses[source_def.source_id].error_message = str(result)
        
        # Update sync run with source statistics
        sync_run.source_stats = {
            sid: {
                "files_processed": status.files_processed,
                "files_new": status.files_new,
                "files_modified": status.files_modified,
                "files_deleted": status.files_deleted,
                "files_error": status.files_error
            }
            for sid, status in source_statuses.items()
        }
    
    async def _sync_sources_sequential(self,
                                     multi_kb: MultiSourceKnowledgeBase,
                                     sources: List,
                                     rag: RAGSystem,
                                     sync_run: MultiSourceSyncRun):
        """Sync sources one after another."""
        
        console.print(f"\n[bold]🔄 Sequential sync of {len(sources)} sources[/bold]")
        
        source_statuses = {}
        
        for i, source_def in enumerate(sources, 1):
            console.print(f"\n[cyan]📁 Processing source {i}/{len(sources)}: {source_def.source_id}[/cyan]")
            
            status = SourceSyncStatus(source_id=source_def.source_id)
            source_statuses[source_def.source_id] = status
            
            try:
                await self._sync_single_source(multi_kb, source_def, rag, sync_run, status)
                console.print(f"[green]✅ {source_def.source_id} completed[/green]")
            except Exception as e:
                logger.error(f"Source {source_def.source_id} failed: {e}")
                status.error_message = str(e)
                console.print(f"[red]❌ {source_def.source_id} failed: {e}[/red]")
        
        # Update sync run statistics
        sync_run.source_stats = {
            sid: {
                "files_processed": status.files_processed,
                "files_new": status.files_new,
                "files_modified": status.files_modified,
                "files_deleted": status.files_deleted,
                "files_error": status.files_error
            }
            for sid, status in source_statuses.items()
        }
    
    async def _sync_single_source(self,
                                multi_kb: MultiSourceKnowledgeBase,
                                source_def,
                                rag: RAGSystem,
                                sync_run: MultiSourceSyncRun,
                                status: SourceSyncStatus):
        """Sync a single source within the multi-source knowledge base."""
        
        status.start_time = datetime.utcnow()
        
        try:
            # Create and initialize source
            source = await self.factory.create_source(source_def.source_type, source_def.source_config)
            await source.initialize()
            
            console.print(f"[cyan]  📁 Listing files from source {source_def.source_id}...[/cyan]")
            files = await source.list_files()
            logger.info(f"Source {source_def.source_id}: Found {len(files)} files")
            
            # Use proper change detection with compatible KB ID for existing file lookup
            console.print(f"[cyan]  🔍 Detecting changes for {source_def.source_id}...[/cyan]")
            
            # For multi-source, we need to use the compatible KB ID that actually has file records
            # This enables proper delta sync by finding existing files
            compatible_kb_id = await self._get_compatible_kb_id(multi_kb)
            changes = await self.change_detector.detect_changes(files, compatible_kb_id)
            
            logger.info(f"Using compatible KB ID {compatible_kb_id} for change detection (multi-source KB ID: {multi_kb.id})")
            
            # Process changes similar to simple KB but with source-specific handling
            processed_count = 0
            error_count = 0
            
            # First pass: calculate hashes for all existing files to determine actual changes
            actual_changes = []
            for change in changes:
                if change.change_type == ChangeType.NEW:
                    actual_changes.append(change)
                    status.files_new += 1
                elif change.change_type == ChangeType.MODIFIED:
                    # Fast pre-filtering before expensive hash calculation
                    should_check_hash = True
                    
                    # Quick check 1: File size comparison
                    if (hasattr(change, 'metadata') and change.metadata and 
                        hasattr(change.existing_record, 'file_size') and change.existing_record.file_size):
                        if change.metadata.size != change.existing_record.file_size:
                            logger.info(f"File {change.uri} size changed: {change.existing_record.file_size} -> {change.metadata.size}")
                            # Size changed, definitely modified - skip hash check
                            actual_changes.append(change)
                            status.files_modified += 1
                            should_check_hash = False
                        else:
                            logger.debug(f"File {change.uri} size unchanged: {change.metadata.size} bytes")
                    
                    # Quick check 2: Modification date comparison (if available in DB)
                    if (should_check_hash and hasattr(change, 'metadata') and change.metadata and 
                        hasattr(change.existing_record, 'source_modified_at') and 
                        change.existing_record.source_modified_at):
                        
                        source_modified = change.metadata.modified_at
                        stored_modified = change.existing_record.source_modified_at
                        
                        # Compare modification times (with small tolerance for timezone/precision issues)
                        if abs((source_modified - stored_modified).total_seconds()) <= 2:
                            # Modification times match - likely unchanged
                            change.change_type = ChangeType.UNCHANGED
                            logger.info(f"File {change.uri} modification time unchanged, skipping hash check")
                            should_check_hash = False
                        else:
                            logger.info(f"File {change.uri} modification time changed: {stored_modified} -> {source_modified}")
                    
                    # Expensive hash calculation only when needed
                    if should_check_hash:
                        try:
                            logger.debug(f"Calculating hash for potentially modified file: {change.uri}")
                            content = await source.get_file_content(change.uri)
                            file_hash = await self.file_processor.calculate_hash(content)
                            
                            if file_hash != change.existing_record.file_hash:
                                # Content actually changed
                                change.new_hash = file_hash  # Store hash to avoid recalculation
                                actual_changes.append(change)
                                status.files_modified += 1
                                logger.info(f"File {change.uri} content changed (hash mismatch)")
                            else:
                                # Content is the same, mark as unchanged
                                change.change_type = ChangeType.UNCHANGED
                                logger.info(f"File {change.uri} content unchanged (hash match)")
                        except Exception as e:
                            logger.error(f"Error calculating hash for {change.uri}: {e}")
                            # If we can't calculate hash, assume it's modified to be safe
                            actual_changes.append(change)
                            status.files_error += 1
                elif change.change_type == ChangeType.DELETED:
                    # Include deleted files for processing
                    actual_changes.append(change)
                    status.files_deleted += 1
                    logger.info(f"File {change.uri} marked for deletion")
            
            # Filter to only process files with actual changes
            changes_to_process = actual_changes
            
            # Update change summary after hash verification
            change_summary = self.change_detector.get_change_summary(changes)
            
            # Display change summary for this source
            self._display_source_change_summary(source_def.source_id, change_summary, len(files))
            
            logger.info(f"Source {source_def.source_id} change summary after hash verification: {change_summary}")
            
            status.files_processed = len(files)
            
            if changes_to_process:
                console.print(f"[bold]  📤 Processing {len(changes_to_process)} files for {source_def.source_id}...[/bold]")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task(
                        f"Uploading {source_def.source_id} files...", 
                        total=len(changes_to_process)
                    )
                    
                    for i, change in enumerate(changes_to_process):
                        try:
                            # Update progress description
                            progress.update(
                                task, 
                                description=f"Processing {source_def.source_id}: {change.uri} ({change.change_type.value})"
                            )
                            
                            await self._process_multi_source_file(
                                source, rag, multi_kb, source_def, sync_run.id, change
                            )
                            processed_count += 1
                            
                            # Update progress
                            progress.update(task, advance=1)
                            
                        except Exception as e:
                            logger.error(f"Error processing file {change.uri}: {e}")
                            error_count += 1
                            status.files_error += 1
                            console.print(f"[red]  ❌ Error processing {change.uri}: {e}[/red]")
            else:
                console.print(f"[green]  ✅ No files need processing for {source_def.source_id} (all files are unchanged)[/green]")
            
            # Final status update
            logger.info(f"Source {source_def.source_id}: {processed_count} files processed, {error_count} errors")
            status.end_time = datetime.utcnow()
            
        except Exception as e:
            status.end_time = datetime.utcnow()
            status.error_message = str(e)
            logger.error(f"Source {source_def.source_id} sync failed: {e}")
            raise
        finally:
            if 'source' in locals():
                await source.cleanup()
    
    async def _process_multi_source_file(self, 
                                       source: FileSource, 
                                       rag: RAGSystem,
                                       multi_kb: MultiSourceKnowledgeBase,
                                       source_def,
                                       sync_run_id: int,
                                       change):
        """Process a single file change in multi-source context."""
        try:
            # Handle deleted files separately
            if change.change_type == ChangeType.DELETED:
                await self._process_deleted_multi_source_file(rag, multi_kb, source_def, sync_run_id, change)
                return
            
            # Get file content
            content = await source.get_file_content(change.uri)
            
            # Get existing UUID if this is a modified file
            existing_uuid = None
            if change.existing_record:
                existing_uuid = change.existing_record.uuid_filename
            
            # Use pre-calculated hash if available
            if hasattr(change, 'new_hash') and change.new_hash:
                file_hash = change.new_hash
            else:
                # Calculate hash if not already done
                file_hash = await self.file_processor.calculate_hash(content)
            
            # Generate UUID filename with source organization
            uuid_filename = self._generate_source_filename(
                source_def.source_id, 
                change.uri,
                multi_kb.file_organization
            )
            
            # Create RAG URI with multi-KB name
            rag_uri = f"{multi_kb.name}/{uuid_filename}"
            
            # Determine status based on change type (already verified by hash)
            from ..data.models import FileStatus
            if change.change_type == ChangeType.NEW:
                status = FileStatus.NEW.value
            elif change.change_type == ChangeType.MODIFIED:
                status = FileStatus.MODIFIED.value
            else:
                status = FileStatus.UNCHANGED.value
                # Use existing RAG URI for unchanged files
                if change.existing_record:
                    rag_uri = change.existing_record.rag_uri
            
            # Upload to RAG system only if content changed
            if status != FileStatus.UNCHANGED.value:
                metadata = {
                    "original_uri": change.uri,
                    "kb_name": multi_kb.name,
                    "source_id": source_def.source_id,
                    "source_type": source_def.source_type,
                    "file_hash": file_hash,
                    "source_modified_at": change.metadata.modified_at.isoformat(),
                    **source_def.metadata_tags
                }
                
                if change.change_type == ChangeType.NEW:
                    await rag.upload_document(content, uuid_filename, metadata)
                else:  # MODIFIED
                    if (change.existing_record and change.existing_record.rag_uri and 
                        not change.existing_record.rag_uri.startswith(f"{multi_kb.name}/error-")):
                        # Update existing document only if it's not an error record
                        await rag.update_document(change.existing_record.rag_uri, content, metadata)
                        logger.info(f"Updated existing document: {change.existing_record.rag_uri}")
                    else:
                        # Upload as new document for error records or missing RAG URIs
                        await rag.upload_document(content, uuid_filename, metadata)
                        if change.existing_record and change.existing_record.rag_uri:
                            logger.info(f"Uploading as new document (existing was error record): {change.existing_record.rag_uri} -> {uuid_filename}")
                        else:
                            logger.info(f"Uploading as new document (no existing RAG URI): {uuid_filename}")
            
            # Create enhanced file record
            file_record = EnhancedFileRecord(
                sync_run_id=sync_run_id,
                source_id=source_def.source_id,
                source_type=source_def.source_type,
                source_path=change.uri,
                original_uri=change.uri,
                rag_uri=rag_uri,
                file_hash=file_hash,
                uuid_filename=uuid_filename,
                upload_time=datetime.utcnow(),
                file_size=change.metadata.size,
                content_type=change.metadata.content_type,
                source_created_at=change.metadata.created_at,
                source_modified_at=change.metadata.modified_at,
                source_metadata=source_def.metadata_tags,
                status=status
            )
            
            await self._save_enhanced_file_record(file_record)
            
            logger.info(f"Processed multi-source file {change.uri} ({status}) with UUID: {uuid_filename}")
            
        except Exception as e:
            # Create error record - need to provide a dummy RAG URI since it's required
            error_rag_uri = f"{multi_kb.name}/error-{datetime.utcnow().timestamp()}"
            error_record = EnhancedFileRecord(
                sync_run_id=sync_run_id,
                source_id=source_def.source_id,
                source_type=source_def.source_type,
                source_path=change.uri,
                original_uri=change.uri,
                rag_uri=error_rag_uri,
                file_hash="",
                uuid_filename="",
                upload_time=datetime.utcnow(),
                file_size=0,
                content_type="",
                source_created_at=datetime.utcnow(),
                source_modified_at=datetime.utcnow(),
                source_metadata={},
                status=FileStatus.ERROR.value,
                error_message=str(e)
            )
            await self._save_enhanced_file_record(error_record)
            raise
    
    async def _process_deleted_multi_source_file(self, 
                                               rag: RAGSystem,
                                               multi_kb: MultiSourceKnowledgeBase,
                                               source_def,
                                               sync_run_id: int,
                                               change):
        """Process a deleted file by removing it from RAG and updating database."""
        try:
            if not change.existing_record:
                logger.error(f"No existing record found for deleted file: {change.uri}")
                return
            
            # Delete from RAG system
            if change.existing_record.rag_uri:
                try:
                    await rag.delete_document(change.existing_record.rag_uri)
                    logger.info(f"Deleted file from RAG: {change.existing_record.rag_uri}")
                except Exception as e:
                    logger.error(f"Error deleting file from RAG: {e}")
                    # Continue to update database even if RAG deletion fails
            
            # Create enhanced file record marking it as deleted
            from ..data.models import FileStatus
            file_record = EnhancedFileRecord(
                sync_run_id=sync_run_id,
                source_id=source_def.source_id,
                source_type=source_def.source_type,
                source_path=change.uri,
                original_uri=change.uri,
                rag_uri=change.existing_record.rag_uri,
                file_hash=change.existing_record.file_hash,
                uuid_filename=change.existing_record.uuid_filename,
                upload_time=datetime.utcnow(),
                file_size=change.existing_record.file_size,
                content_type="",
                source_created_at=datetime.utcnow(),
                source_modified_at=datetime.utcnow(),
                source_metadata=source_def.metadata_tags,
                status=FileStatus.DELETED.value
            )
            
            await self._save_enhanced_file_record(file_record)
            
            logger.info(f"Marked multi-source file as deleted in database: {change.uri}")
            
        except Exception as e:
            logger.error(f"Error processing deleted file {change.uri}: {e}")
            # Create error record
            error_rag_uri = change.existing_record.rag_uri if change.existing_record else f"{multi_kb.name}/error-{datetime.utcnow().timestamp()}"
            error_record = EnhancedFileRecord(
                sync_run_id=sync_run_id,
                source_id=source_def.source_id,
                source_type=source_def.source_type,
                source_path=change.uri,
                original_uri=change.uri,
                rag_uri=error_rag_uri,
                file_hash="",
                uuid_filename="",
                upload_time=datetime.utcnow(),
                file_size=0,
                content_type="",
                source_created_at=datetime.utcnow(),
                source_modified_at=datetime.utcnow(),
                source_metadata={},
                status=FileStatus.ERROR.value,
                error_message=str(e)
            )
            await self._save_enhanced_file_record(error_record)
            raise
    
    def _display_source_change_summary(self, source_id: str, change_summary: Dict[str, int], total_files: int):
        """Display a summary of detected changes for a specific source."""
        table = Table(
            title=f"Change Detection Summary - {source_id}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Change Type", style="bold")
        table.add_column("Count", justify="right")
        
        table.add_row("New Files", f"[green]{change_summary['new']}[/green]")
        table.add_row("Modified Files", f"[yellow]{change_summary['modified']}[/yellow]")
        table.add_row("Unchanged Files", f"[dim]{change_summary['unchanged']}[/dim]")
        table.add_row("Deleted Files", f"[red]{change_summary['deleted']}[/red]")
        table.add_section()
        table.add_row("Total Files", f"[bold]{total_files}[/bold]")
        
        console.print(table)
    
    def _generate_source_filename(self, 
                                source_id: str, 
                                original_uri: str,
                                file_organization: Dict[str, Any]) -> str:
        """Generate UUID filename with source organization."""
        import uuid
        from pathlib import Path
        
        # Generate base UUID
        file_uuid = str(uuid.uuid4())
        original_path = Path(original_uri)
        extension = original_path.suffix
        
        # Apply file organization strategy
        naming_convention = file_organization.get("naming_convention", "{uuid}{extension}")
        
        if "{source_id}" in naming_convention:
            filename = naming_convention.format(
                source_id=source_id,
                uuid=file_uuid,
                extension=extension,
                original_name=original_path.stem
            )
        else:
            filename = f"{file_uuid}{extension}"
        
        return filename
    
    async def _load_multi_source_kb(self, kb_name: str) -> Optional[MultiSourceKnowledgeBase]:
        """Load multi-source knowledge base configuration."""
        return await self.repository.get_multi_source_kb_by_name(kb_name)
    
    async def _create_multi_source_sync_run(self, 
                                          multi_kb: MultiSourceKnowledgeBase,
                                          sync_mode: SyncMode,
                                          sources: List) -> MultiSourceSyncRun:
        """Create a new multi-source sync run."""
        
        # For compatibility, create a regular sync run in the existing table
        # and extend it with multi-source information
        from ..data.models import SyncRun, SyncRunStatus
        
        # Find or create a compatible regular KB for the sync_run foreign key
        compatible_kb_id = await self._get_compatible_kb_id(multi_kb)
        
        # Create a regular sync run first to get an ID
        regular_sync_run = SyncRun(
            id=await self.repository.create_sync_run(compatible_kb_id),
            knowledge_base_id=compatible_kb_id,
            start_time=datetime.utcnow(),
            status=SyncRunStatus.RUNNING.value
        )
        
        # Create enhanced multi-source sync run
        sync_run = MultiSourceSyncRun(
            id=regular_sync_run.id,
            knowledge_base_id=multi_kb.id,  # Keep the original multi-source KB ID for logic
            start_time=regular_sync_run.start_time,
            sync_mode=sync_mode.value,
            sources_processed=[s.source_id for s in sources],
            status="running",
            source_stats={}
        )
        
        # Store the compatible KB ID as an attribute (not in __init__)
        sync_run._compatible_kb_id = compatible_kb_id
        
        return sync_run
    
    async def _get_compatible_kb_id(self, multi_kb: MultiSourceKnowledgeBase) -> int:
        """Find or create a compatible regular KB ID for sync_run foreign key constraint."""
        
        # Strategy 1: Look for existing regular KBs that match the multi-source KB name pattern
        # For "PremiumRMs2-kb", look for "PremiumRMs2-kb_*" pattern
        search_pattern = f"{multi_kb.name}_%"
        
        try:
            # Query for existing regular KBs that match the pattern
            query = "SELECT id FROM knowledge_base WHERE name LIKE $1 ORDER BY id LIMIT 1"
            result = await self.repository.db.fetchval(query, search_pattern)
            
            if result:
                logger.info(f"Found compatible regular KB ID {result} for multi-source KB {multi_kb.name}")
                return result
                
        except Exception as e:
            logger.warning(f"Error searching for compatible KB: {e}")
        
        # Strategy 2: Create a placeholder regular KB for compatibility
        logger.info(f"Creating placeholder regular KB for multi-source KB {multi_kb.name}")
        
        from ..data.models import KnowledgeBase
        placeholder_kb = KnowledgeBase(
            name=f"{multi_kb.name}_placeholder",
            source_type="multi_source_placeholder",
            source_config={"placeholder": True, "multi_source_kb_id": multi_kb.id},
            rag_type=multi_kb.rag_type,
            rag_config=multi_kb.rag_config
        )
        
        try:
            placeholder_id = await self.repository.create_knowledge_base(placeholder_kb)
            logger.info(f"Created placeholder KB with ID {placeholder_id}")
            return placeholder_id
            
        except Exception as e:
            logger.error(f"Failed to create placeholder KB: {e}")
            # As a last resort, use the multi-source KB ID and let the constraint fail with a better error
            raise Exception(f"Cannot create compatible KB for sync_run table. Multi-source KB ID {multi_kb.id} "
                          f"is not compatible with the sync_run foreign key constraint. Original error: {e}")
    
    async def _finalize_sync_run(self, 
                               sync_run: MultiSourceSyncRun,
                               success: bool,
                               error: Optional[str] = None):
        """Finalize the sync run with statistics."""
        sync_run.end_time = datetime.utcnow()
        
        if success:
            sync_run.status = "completed"
            # Calculate totals from source stats
            sync_run.total_files = sum(stats.get("files_processed", 0) 
                                     for stats in sync_run.source_stats.values())
            sync_run.new_files = sum(stats.get("files_new", 0) 
                                   for stats in sync_run.source_stats.values())
            sync_run.modified_files = sum(stats.get("files_modified", 0) 
                                        for stats in sync_run.source_stats.values())
            sync_run.deleted_files = sum(stats.get("files_deleted", 0) 
                                       for stats in sync_run.source_stats.values())
        else:
            sync_run.status = "failed"
            sync_run.error_message = error
        
        # Save to existing database structure
        await self._save_sync_run_to_existing_table(sync_run)
        
        # Display summary
        self._display_sync_summary(sync_run)
    
    async def _save_sync_run_to_existing_table(self, sync_run: MultiSourceSyncRun):
        """Save multi-source sync run to existing sync_run table."""
        from ..data.models import SyncRun, SyncRunStatus
        
        # Convert status to enum
        status_enum = SyncRunStatus.COMPLETED if sync_run.status == "completed" else SyncRunStatus.FAILED
        
        # Use the compatible KB ID for database storage (to satisfy foreign key constraint)
        compatible_kb_id = getattr(sync_run, '_compatible_kb_id', sync_run.knowledge_base_id)
        
        # Create a regular sync run for database storage
        regular_sync_run = SyncRun(
            id=sync_run.id,
            knowledge_base_id=compatible_kb_id,  # Use compatible KB ID for foreign key
            start_time=sync_run.start_time,
            end_time=sync_run.end_time,
            status=status_enum.value,
            total_files=sync_run.total_files or 0,
            new_files=sync_run.new_files or 0,
            modified_files=sync_run.modified_files or 0,
            deleted_files=sync_run.deleted_files or 0,
            error_message=getattr(sync_run, 'error_message', None)
        )
        
        # Update the existing sync run record
        await self.repository.update_sync_run(regular_sync_run)
        
        # Log multi-source specific information
        logger.info(f"Multi-source sync run finalized: ID={sync_run.id}")
        logger.info(f"Original multi-source KB ID: {sync_run.knowledge_base_id}")
        logger.info(f"Compatible KB ID used for DB: {compatible_kb_id}")
        logger.info(f"Sync mode: {sync_run.sync_mode}")
        logger.info(f"Sources processed: {sync_run.sources_processed}")
        logger.info(f"Per-source statistics: {sync_run.source_stats}")
    
    def _display_sync_summary(self, sync_run: MultiSourceSyncRun):
        """Display sync run summary with comprehensive results."""
        
        # First, display detailed results similar to simple KB
        results_table = Table(
            title="Multi-Source Synchronization Results",
            box=box.ROUNDED
        )
        results_table.add_column("Metric", style="bold")
        results_table.add_column("Value", style="bold", justify="right")
        
        # Add sync run details
        if sync_run.end_time and sync_run.start_time:
            duration = sync_run.end_time - sync_run.start_time
            results_table.add_row("Duration", f"{duration.total_seconds():.1f} seconds")
        
        results_table.add_row("Status", f"[green]{sync_run.status}[/green]" if sync_run.status == "completed" else f"[red]{sync_run.status}[/red]")
        results_table.add_section()
        
        # Add aggregated totals
        total_processed = sum(stats.get("files_processed", 0) for stats in sync_run.source_stats.values())
        total_errors = sum(stats.get("files_error", 0) for stats in sync_run.source_stats.values())
        
        results_table.add_row("Total Files Processed", f"{total_processed}")
        results_table.add_row("Total Errors", f"[red]{total_errors}[/red]" if total_errors > 0 else "0")
        results_table.add_section()
        
        # Add change details
        results_table.add_row("New Files", f"[green]{sync_run.new_files or 0}[/green]")
        results_table.add_row("Modified Files", f"[yellow]{sync_run.modified_files or 0}[/yellow]")
        results_table.add_row("Deleted Files", f"[red]{sync_run.deleted_files or 0}[/red]")
        
        console.print("\n")
        console.print(results_table)
        
        # Then display per-source breakdown
        source_table = Table(title=f"Per-Source Breakdown", box=box.ROUNDED)
        
        source_table.add_column("Source", style="cyan")
        source_table.add_column("Status", style="green")
        source_table.add_column("Files", justify="right")
        source_table.add_column("New", justify="right", style="green")
        source_table.add_column("Modified", justify="right", style="yellow")
        source_table.add_column("Deleted", justify="right", style="red")
        source_table.add_column("Errors", justify="right", style="red")
        
        for source_id, stats in sync_run.source_stats.items():
            status = "✅ Success" if stats.get("files_error", 0) == 0 else "❌ Errors"
            source_table.add_row(
                source_id,
                status,
                str(stats.get("files_processed", 0)),
                str(stats.get("files_new", 0)),
                str(stats.get("files_modified", 0)),
                str(stats.get("files_deleted", 0)),
                str(stats.get("files_error", 0))
            )
        
        # Add totals row
        source_table.add_section()
        source_table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{'✅ Success' if sync_run.status == 'completed' else '❌ Failed'}[/bold]",
            f"[bold]{total_processed}[/bold]",
            f"[bold]{sync_run.new_files or 0}[/bold]",
            f"[bold]{sync_run.modified_files or 0}[/bold]",
            f"[bold]{sync_run.deleted_files or 0}[/bold]",
            f"[bold]{total_errors}[/bold]"
        )
        
        console.print(source_table)
        
        if total_errors > 0:
            console.print(f"\n[yellow]Warning: {total_errors} files failed to process across all sources[/yellow]")
    
    async def list_sync_runs(self, kb_name: str, limit: int = 10):
        """List recent sync runs for a multi-source knowledge base."""
        multi_kb = await self.repository.get_multi_source_kb_by_name(kb_name)
        if not multi_kb:
            console.print(f"[red]Multi-source knowledge base '{kb_name}' not found[/red]")
            return
        
        # Get recent sync runs (would need to implement in repository)
        console.print(f"[cyan]Recent sync runs for multi-source KB: {kb_name}[/cyan]")
        
        # Create table for sync run history
        table = Table(
            title=f"Sync Run History - {kb_name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Run ID", style="dim")
        table.add_column("Start Time", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Duration", justify="right")
        table.add_column("Sources", justify="right")
        table.add_column("Files", justify="right")
        table.add_column("New", justify="right", style="green")
        table.add_column("Modified", justify="right", style="yellow")
        table.add_column("Errors", justify="right", style="red")
        
        # This would be populated from actual database records
        # For now, show placeholder
        table.add_row(
            "1",
            "2024-01-15 14:30:00",
            "[green]completed[/green]",
            "45.2s",
            "2",
            "150",
            "25",
            "5",
            "0"
        )
        
        console.print(table)
        console.print(f"[yellow]Note: Multi-source sync run history not yet fully implemented[/yellow]")
    
    async def _save_enhanced_file_record(self, file_record: EnhancedFileRecord):
        """Save enhanced file record to database."""
        # For now, save as regular file record to maintain compatibility
        # In a full implementation, this would save to an enhanced table
        from ..data.models import FileRecord, FileStatus
        
        # Convert enhanced record to regular record for database compatibility
        regular_record = FileRecord(
            sync_run_id=file_record.sync_run_id,
            original_uri=file_record.original_uri,
            rag_uri=file_record.rag_uri,
            file_hash=file_record.file_hash,
            uuid_filename=file_record.uuid_filename,
            upload_time=file_record.upload_time,
            file_size=file_record.file_size,
            status=file_record.status,
            error_message=getattr(file_record, 'error_message', None),
            source_id=file_record.source_id,
            source_type=file_record.source_type,
            source_path=file_record.source_path,
            content_type=file_record.content_type,
            source_metadata=file_record.source_metadata,
            source_created_at=file_record.source_created_at,
            source_modified_at=file_record.source_modified_at
        )
        
        await self.repository.create_file_record_original(regular_record)
        
        # Log the source information that would be stored in enhanced table
        logger.info(f"Enhanced file record: source_id={file_record.source_id}, "
                   f"source_type={file_record.source_type}, content_type={file_record.content_type}")
    
