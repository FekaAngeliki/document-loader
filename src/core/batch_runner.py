import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box

from ..abstractions.file_source import FileSource
from ..abstractions.rag_system import RAGSystem
from ..data.repository import Repository
from ..data.models import SyncRun, FileRecord, SyncRunStatus, FileStatus
from .change_detector import ChangeDetector, ChangeType
from .file_processor import FileProcessor
from .factory import Factory

logger = logging.getLogger(__name__)
console = Console()

class BatchRunner:
    """Orchestrates the batch processing of files."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self.change_detector = ChangeDetector(repository)
        self.file_processor = FileProcessor()
        self.factory = Factory(repository)
    
    async def sync_knowledge_base(self, 
                                 kb_name: str, 
                                 progress_callback: Optional[Callable] = None):
        """Synchronize a knowledge base."""
        console.print(f"\n[bold cyan]Starting synchronization for knowledge base: {kb_name}[/bold cyan]")
        
        source = None
        rag = None
        sync_run = None
        
        try:
            # Get knowledge base
            kb = await self.repository.get_knowledge_base_by_name(kb_name)
            if not kb:
                raise ValueError(f"Knowledge base '{kb_name}' not found")
            
            # Create sync run
            sync_run = SyncRun(
                id=await self.repository.create_sync_run(kb.id),
                knowledge_base_id=kb.id,
                start_time=datetime.now(),
                status=SyncRunStatus.RUNNING.value
            )
            
            # Initialize source and RAG systems
            source = await self.factory.create_source(kb.source_type, kb.source_config)
            rag = await self.factory.create_rag(kb.rag_type, kb.rag_config)
            
            try:
                # List source files
                console.print("[cyan]Listing files from source...[/cyan]")
                source_files = await source.list_files()
                logger.info(f"Found {len(source_files)} files in source")
                
                # Detect changes
                console.print("[cyan]Detecting changes...[/cyan]")
                changes = await self.change_detector.detect_changes(source_files, kb.id)
                
                # Process changes
                processed_count = 0
                error_count = 0
                
                # First pass: calculate hashes for all existing files to determine actual changes
                actual_changes = []
                for change in changes:
                    if change.change_type == ChangeType.NEW:
                        actual_changes.append(change)
                    elif change.change_type == ChangeType.MODIFIED:
                        # Calculate hash to verify if file actually changed
                        try:
                            content = await source.get_file_content(change.uri)
                            file_hash = await self.file_processor.calculate_hash(content)
                            
                            if file_hash != change.existing_record.file_hash:
                                # Content actually changed
                                change.new_hash = file_hash  # Store hash to avoid recalculation
                                actual_changes.append(change)
                                logger.info(f"File {change.uri} content changed (hash mismatch)")
                            else:
                                # Content is the same, mark as unchanged
                                change.change_type = ChangeType.UNCHANGED
                                logger.info(f"File {change.uri} content unchanged (hash match)")
                        except Exception as e:
                            logger.error(f"Error calculating hash for {change.uri}: {e}")
                            # If we can't calculate hash, assume it's modified to be safe
                            actual_changes.append(change)
                    elif change.change_type == ChangeType.DELETED:
                        # Include deleted files for processing
                        actual_changes.append(change)
                        logger.info(f"File {change.uri} marked for deletion")
                
                # Filter to only process files with actual changes
                changes_to_process = actual_changes
                
                # Update change summary after hash verification
                change_summary = self.change_detector.get_change_summary(changes)
                
                # Display change summary
                self._display_change_summary(change_summary, len(source_files))
                
                logger.info(f"Change summary after hash verification: {change_summary}")
                
                if changes_to_process:
                    console.print(f"\n[bold]Processing {len(changes_to_process)} files...[/bold]")
                    
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn(),
                        console=console
                    ) as progress:
                        task = progress.add_task(
                            f"Uploading files to {kb.rag_type}...", 
                            total=len(changes_to_process)
                        )
                        
                        for i, change in enumerate(changes_to_process):
                            try:
                                # Update progress description
                                progress.update(
                                    task, 
                                    description=f"Processing: {change.uri} ({change.change_type.value})"
                                )
                                
                                await self._process_file(
                                    source, rag, kb.name, sync_run.id, change
                                )
                                processed_count += 1
                                
                                # Update progress
                                progress.update(task, advance=1)
                                
                                # Call progress callback if provided
                                if progress_callback:
                                    await progress_callback(i + 1, len(changes_to_process), change.uri)
                                    
                            except Exception as e:
                                logger.error(f"Error processing file {change.uri}: {e}")
                                error_count += 1
                                console.print(f"[red]Error processing {change.uri}: {e}[/red]")
                else:
                    console.print("[green]No files need processing (all files are unchanged)[/green]")
                
                # Update sync run with results
                sync_run.end_time = datetime.now()
                sync_run.status = SyncRunStatus.COMPLETED.value
                sync_run.total_files = len(source_files)
                sync_run.new_files = change_summary["new"]
                sync_run.modified_files = change_summary["modified"]
                sync_run.deleted_files = change_summary["deleted"]
                
                await self.repository.update_sync_run(sync_run)
                
                # Display final results
                self._display_sync_results(
                    sync_run, processed_count, error_count, change_summary
                )
                
                logger.info(f"Sync completed: {processed_count} files processed, {error_count} errors")
                
            except Exception as e:
                # Update sync run status on error
                if sync_run:
                    sync_run.end_time = datetime.now()
                    sync_run.status = SyncRunStatus.FAILED.value
                    sync_run.error_message = str(e)
                    await self.repository.update_sync_run(sync_run)
                
                logger.error(f"Sync failed: {e}")
                console.print(f"[red bold]Sync failed: {e}[/red bold]")
                raise
            
            finally:
                # Clean up resources
                if source:
                    await source.cleanup()
                if rag:
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
            # Handle deleted files separately
            if change.change_type == ChangeType.DELETED:
                await self._process_deleted_file(rag, kb_name, sync_run_id, change)
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
            
            # Generate UUID filename
            uuid_filename = self.file_processor.generate_uuid_filename(
                Path(change.uri).name, existing_uuid, change.uri
            )
            
            # Create RAG URI
            rag_uri = f"{kb_name}/{uuid_filename}"
            
            # Determine status based on change type (already verified by hash)
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
                    "kb_name": kb_name,
                    "file_hash": file_hash,
                    "source_modified_at": change.metadata.modified_at.isoformat()
                }
                
                if change.change_type == ChangeType.NEW:
                    await rag.upload_document(content, uuid_filename, metadata)
                else:  # MODIFIED
                    if change.existing_record and change.existing_record.rag_uri:
                        await rag.update_document(change.existing_record.rag_uri, content, metadata)
                    else:
                        await rag.upload_document(content, uuid_filename, metadata)
            
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
            
            logger.info(f"Processed file {change.uri} ({status}) with UUID: {uuid_filename}")
            
        except Exception as e:
            # Create error record - need to provide a dummy RAG URI since it's required
            error_rag_uri = f"{kb_name}/error-{datetime.now().timestamp()}"
            error_record = FileRecord(
                sync_run_id=sync_run_id,
                original_uri=change.uri,
                rag_uri=error_rag_uri,  # Provide a dummy value since it's required
                file_hash="",  # Empty string instead of None
                uuid_filename="",  # Empty string instead of None
                upload_time=datetime.now(),
                file_size=0,
                status=FileStatus.ERROR.value,
                error_message=str(e)
            )
            await self.repository.create_file_record_original(error_record)
            raise
    
    async def _process_deleted_file(self, 
                                   rag: RAGSystem,
                                   kb_name: str,
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
            
            # Create file record marking it as deleted
            file_record = FileRecord(
                sync_run_id=sync_run_id,
                original_uri=change.uri,
                rag_uri=change.existing_record.rag_uri,
                file_hash=change.existing_record.file_hash,
                uuid_filename=change.existing_record.uuid_filename,
                upload_time=datetime.now(),
                file_size=change.existing_record.file_size,
                status=FileStatus.DELETED.value
            )
            
            await self.repository.create_file_record_original(file_record)
            
            logger.info(f"Marked file as deleted in database: {change.uri}")
            
        except Exception as e:
            logger.error(f"Error processing deleted file {change.uri}: {e}")
            # Create error record - need to provide a dummy RAG URI since it's required
            error_rag_uri = change.existing_record.rag_uri if change.existing_record else f"{kb_name}/error-{datetime.now().timestamp()}"
            error_record = FileRecord(
                sync_run_id=sync_run_id,
                original_uri=change.uri,
                rag_uri=error_rag_uri,  # Provide a value since it's required
                file_hash="",  # Empty string instead of None
                uuid_filename="",  # Empty string instead of None
                upload_time=datetime.now(),
                file_size=0,
                status=FileStatus.ERROR.value,
                error_message=str(e)
            )
            await self.repository.create_file_record_original(error_record)
            raise
    
    def _display_change_summary(self, change_summary: Dict[str, int], total_files: int):
        """Display a summary of detected changes."""
        table = Table(
            title="Change Detection Summary",
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
        
        console.print("\n")
        console.print(table)
    
    def _display_sync_results(self, 
                            sync_run: SyncRun, 
                            processed_count: int, 
                            error_count: int,
                            change_summary: Dict[str, int]):
        """Display final synchronization results."""
        table = Table(
            title="Synchronization Results",
            box=box.ROUNDED
        )
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="bold", justify="right")
        
        # Add sync run details
        duration = sync_run.end_time - sync_run.start_time
        table.add_row("Duration", f"{duration.total_seconds():.1f} seconds")
        table.add_row("Status", f"[green]{sync_run.status}[/green]")
        table.add_section()
        
        # Add file processing details
        table.add_row("Files Processed", f"{processed_count}")
        table.add_row("Errors", f"[red]{error_count}[/red]" if error_count > 0 else "0")
        table.add_section()
        
        # Add change details
        table.add_row("New Files", f"[green]{change_summary['new']}[/green]")
        table.add_row("Modified Files", f"[yellow]{change_summary['modified']}[/yellow]")
        table.add_row("Unchanged Files", f"[dim]{change_summary['unchanged']}[/dim]")
        table.add_row("Deleted Files", f"[red]{change_summary['deleted']}[/red]")
        
        console.print("\n")
        console.print(table)
        
        if error_count > 0:
            console.print(f"\n[yellow]Warning: {error_count} files failed to process[/yellow]")
    
    async def list_sync_runs(self, kb_name: str, limit: int = 10):
        """List recent sync runs for a knowledge base."""
        kb = await self.repository.get_knowledge_base_by_name(kb_name)
        if not kb:
            console.print(f"[red]Knowledge base '{kb_name}' not found[/red]")
            return
        
        # This would require adding a new repository method to list sync runs
        # For now, we'll just show a placeholder
        console.print(f"[yellow]Listing sync runs not yet implemented[/yellow]")