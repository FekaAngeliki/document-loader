import asyncio
from pathlib import Path
from typing import Optional, Dict
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from ..abstractions.file_source import FileSource
from ..core.file_processor import FileProcessor
from ..core.change_detector import ChangeDetector, ChangeType

console = Console()

class FileScanner:
    """Scans files and calculates hashes, with change detection support."""
    
    def __init__(self):
        self.file_processor = FileProcessor()
    
    async def scan_source(self, source: FileSource, path: str = "", show_progress: bool = True, 
                         kb_name: Optional[str] = None, repository = None):
        """Scan files from a source and compare against previous scans."""
        await source.initialize()
        
        try:
            # If repository is provided, create a sync run
            sync_run_id = None
            kb = None
            if repository and kb_name:
                kb = await repository.get_knowledge_base_by_name(kb_name)
                if kb:
                    sync_run_id = await repository.create_sync_run(kb.id, "scan_running")
            
            if show_progress:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Scanning files...", total=None)
                    await self._scan_with_progress(source, path, progress, task, kb_name, 
                                                  repository, sync_run_id, kb)
            else:
                await self._scan_files(source, path, kb_name, repository, sync_run_id, kb)
                
            # If repository is provided, update sync run as completed
            if repository and sync_run_id:
                await repository.update_sync_run_status(sync_run_id, "scan_completed")
        except Exception as e:
            # If repository is provided, update sync run as failed
            if repository and sync_run_id:
                await repository.update_sync_run_status(sync_run_id, "scan_failed", str(e))
            raise
        finally:
            await source.cleanup()
    
    async def _scan_with_progress(self, source: FileSource, path: str, progress: Progress, task,
                                 kb_name: Optional[str] = None, repository = None, sync_run_id = None, kb = None):
        """Scan files with progress indicator and change detection."""
        file_count = 0
        changes = {}
        stats = {'total': 0, 'new': 0, 'modified': 0, 'unchanged': 0}
        
        # Initialize change detector if we have a repository and knowledge base
        change_detector = None
        if repository and kb:
            change_detector = ChangeDetector(repository)
        
        async for file_metadata in source.stream_files(path):
            file_count += 1
            progress.update(task, description=f"Scanning files... [{file_count}]")
            
            # Process file and detect changes
            change_info = await self._process_file_with_change_detection(
                source, file_metadata, kb_name, repository, sync_run_id, kb, change_detector
            )
            
            if change_info:
                changes[file_metadata.uri] = change_info
                stats['total'] += 1
                stats[change_info['change_type']] += 1
        
        progress.update(task, description=f"Scan complete. Found {file_count} files.")
        
        # Display change summary
        if changes:
            console.print("\n[bold]Change Summary:[/bold]")
            self._display_change_summary(stats)
        
        # Update sync run with statistics
        if repository and sync_run_id:
            await repository.update_sync_run_stats(sync_run_id, stats)
    
    async def _scan_files(self, source: FileSource, path: str, kb_name: Optional[str] = None, 
                         repository = None, sync_run_id = None, kb = None):
        """Scan files without progress indicator but with change detection."""
        file_count = 0
        changes = {}
        stats = {'total': 0, 'new': 0, 'modified': 0, 'unchanged': 0}
        
        # Initialize change detector if we have a repository and knowledge base
        change_detector = None
        if repository and kb:
            change_detector = ChangeDetector(repository)
        
        async for file_metadata in source.stream_files(path):
            file_count += 1
            
            # Process file and detect changes
            change_info = await self._process_file_with_change_detection(
                source, file_metadata, kb_name, repository, sync_run_id, kb, change_detector
            )
            
            if change_info:
                changes[file_metadata.uri] = change_info
                stats['total'] += 1
                stats[change_info['change_type']] += 1
        
        console.print(f"\n[green]Scan complete. Found {file_count} files.[/green]")
        
        # Display change summary
        if changes:
            console.print("\n[bold]Change Summary:[/bold]")
            self._display_change_summary(stats)
        
        # Update sync run with statistics
        if repository and sync_run_id:
            await repository.update_sync_run_stats(sync_run_id, stats)
    
    async def _process_file_with_change_detection(self, source: FileSource, file_metadata, 
                                                kb_name: Optional[str] = None, repository = None, 
                                                sync_run_id = None, kb = None, change_detector = None):
        """Process a file and detect changes compared to previous scans."""
        try:
            # Get file content and calculate hash
            content = await source.get_file_content(file_metadata.uri)
            file_hash = await self.file_processor.calculate_hash(content)
            
            # Check for existing record and get existing UUID
            existing_uuid = None
            change_type = "new"
            previous_hash = None
            
            if change_detector and kb:
                # Get existing record
                existing_record = await repository.get_file_record_by_uri(file_metadata.uri, kb.id)
                
                if existing_record:
                    existing_uuid = existing_record.uuid_filename
                    previous_hash = existing_record.file_hash
                    if file_hash == previous_hash:
                        change_type = "unchanged"
                    else:
                        change_type = "modified"
            
            # Generate UUID filename - use existing if available
            uuid_filename = self.file_processor.generate_uuid_filename(
                file_metadata.uri, 
                existing_uuid=existing_uuid
            )
            
            # Generate RAG URI if kb_name is provided
            rag_uri = None
            if kb_name:
                rag_uri = self.file_processor.generate_rag_uri(kb_name, uuid_filename)
            
            # Update database if repository is provided
            if repository and sync_run_id:
                file_record = {
                    'sync_run_id': sync_run_id,
                    'original_uri': file_metadata.uri,
                    'rag_uri': rag_uri,
                    'file_hash': file_hash,
                    'uuid_filename': uuid_filename,
                    'size': file_metadata.size,
                    'status': 'scanned'
                }
                await repository.create_file_record(file_record)
            
            # Print file information with change status
            size_str = self._format_size(file_metadata.size)
            change_indicator = self._get_change_indicator(change_type)
            
            console.print(
                f"{change_indicator} [{self._get_change_color(change_type)}]{file_metadata.uri}[/{self._get_change_color(change_type)}] | "
                f"UUID: [yellow]{uuid_filename}[/yellow] | "
                f"Hash: [green]{file_hash[:16]}...[/green] | "
                f"Size: [cyan]{size_str}[/cyan] | "
                f"Type: [dim]{file_metadata.content_type}[/dim]"
            )
            
            return {
                'change_type': change_type,
                'file_hash': file_hash,
                'previous_hash': previous_hash,
                'uuid_filename': uuid_filename,
                'rag_uri': rag_uri
            }
            
        except Exception as e:
            console.print(
                f"[red]Error processing {file_metadata.uri}: {str(e)}[/red]"
            )
            return None
    
    def _get_change_indicator(self, change_type: str) -> str:
        """Get visual indicator for change type."""
        indicators = {
            'new': '[green]+[/green]',
            'modified': '[yellow]~[/yellow]',
            'unchanged': '[dim]=[/dim]',
            'deleted': '[red]-[/red]'
        }
        return indicators.get(change_type, ' ')
    
    def _get_change_color(self, change_type: str) -> str:
        """Get color for change type."""
        colors = {
            'new': 'green',
            'modified': 'yellow',
            'unchanged': 'dim',
            'deleted': 'red'
        }
        return colors.get(change_type, 'white')
    
    def _display_change_summary(self, stats: Dict[str, int]):
        """Display a summary of detected changes."""
        table = Table(box=box.ROUNDED)
        table.add_column("Change Type", style="bold")
        table.add_column("Count", style="bold", justify="right")
        
        if stats.get('new', 0) > 0:
            table.add_row("[green]New Files[/green]", f"[green]{stats['new']}[/green]")
        if stats.get('modified', 0) > 0:
            table.add_row("[yellow]Modified Files[/yellow]", f"[yellow]{stats['modified']}[/yellow]")
        if stats.get('unchanged', 0) > 0:
            table.add_row("[dim]Unchanged Files[/dim]", f"[dim]{stats['unchanged']}[/dim]")
        
        table.add_row("", "")
        table.add_row("[bold]Total Files[/bold]", f"[bold]{stats['total']}[/bold]")
        
        console.print(table)
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"
    
    async def print_summary_table(self, source: FileSource, path: str = "", kb_name: Optional[str] = None,
                                 repository = None):
        """Print a summary table of all files with change detection."""
        await source.initialize()
        
        try:
            files = await source.list_files(path)
            
            if not files:
                console.print("[yellow]No files found.[/yellow]")
                return
            
            # Get knowledge base if repository is provided
            kb = None
            change_detector = None
            if repository and kb_name:
                kb = await repository.get_knowledge_base_by_name(kb_name)
                if kb:
                    change_detector = ChangeDetector(repository)
            
            table = Table(
                title=f"File Scan Summary ({path or 'root'})",
                style="cyan",
                header_style="bold magenta",
                box=box.ROUNDED
            )
            table.add_column("Status", style="bold", width=8)
            table.add_column("Path", style="blue", no_wrap=True)
            table.add_column("UUID", style="yellow")
            table.add_column("Size", style="cyan", justify="right")
            table.add_column("Hash", style="green")
            table.add_column("Type", style="dim")
            table.add_column("Modified", style="cyan")
            
            total_size = 0
            stats = {'new': 0, 'modified': 0, 'unchanged': 0}
            
            for file_metadata in files:
                try:
                    content = await source.get_file_content(file_metadata.uri)
                    file_hash = await self.file_processor.calculate_hash(content)
                    
                    # Check for existing UUID
                    existing_uuid = None
                    change_type = "new"
                    if change_detector and kb:
                        existing_record = await repository.get_file_record_by_uri(file_metadata.uri, kb.id)
                        if existing_record:
                            existing_uuid = existing_record.uuid_filename
                            if file_hash == existing_record.file_hash:
                                change_type = "unchanged"
                            else:
                                change_type = "modified"
                    
                    stats[change_type] += 1
                    
                    # Use existing UUID if available
                    uuid_filename = self.file_processor.generate_uuid_filename(
                        file_metadata.uri,
                        existing_uuid=existing_uuid
                    )
                    
                    size_str = self._format_size(file_metadata.size)
                    modified_str = file_metadata.modified_at.strftime("%Y-%m-%d %H:%M")
                    
                    # Add status indicator and color
                    status_indicator = self._get_change_indicator(change_type)
                    
                    table.add_row(
                        status_indicator,
                        file_metadata.uri,
                        uuid_filename[:16] + "...",
                        size_str,
                        file_hash[:16] + "...",
                        file_metadata.content_type,
                        modified_str
                    )
                    
                    total_size += file_metadata.size
                    
                except Exception as e:
                    table.add_row(
                        "[red]![/red]",
                        file_metadata.uri,
                        "Error",
                        "Error",
                        "Error",
                        file_metadata.content_type,
                        file_metadata.modified_at.strftime("%Y-%m-%d %H:%M")
                    )
            
            console.print(table)
            console.print(f"\n[bold]Total files:[/bold] {len(files)}")
            console.print(f"[bold]Total size:[/bold] {self._format_size(total_size)}")
            
            # Display change summary if we have change detection
            if change_detector and kb:
                console.print("\n[bold]Change Summary:[/bold]")
                self._display_change_summary(stats)
            
        finally:
            await source.cleanup()