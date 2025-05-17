import asyncio
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..abstractions.file_source import FileSource
from ..core.file_processor import FileProcessor

console = Console()

class FileScanner:
    """Scans files and calculates hashes."""
    
    def __init__(self):
        self.file_processor = FileProcessor()
    
    async def scan_source(self, source: FileSource, path: str = "", show_progress: bool = True, 
                         kb_name: Optional[str] = None, repository = None):
        """Scan files from a source and print information."""
        await source.initialize()
        
        try:
            # If repository is provided, create a sync run
            sync_run_id = None
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
                                                  repository, sync_run_id)
            else:
                await self._scan_files(source, path, kb_name, repository, sync_run_id)
                
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
                                 kb_name: Optional[str] = None, repository = None, sync_run_id = None):
        """Scan files with progress indicator."""
        file_count = 0
        stats = {'total': 0, 'new': 0, 'modified': 0}
        async for file_metadata in source.stream_files(path):
            file_count += 1
            progress.update(task, description=f"Scanning files... [{file_count}]")
            await self._process_file(source, file_metadata, kb_name, repository, sync_run_id)
            stats['total'] += 1
            stats['new'] += 1  # For scan, all files are considered "new"
        
        progress.update(task, description=f"Scan complete. Found {file_count} files.")
        
        # Update sync run with statistics
        if repository and sync_run_id:
            await repository.update_sync_run_stats(sync_run_id, stats)
    
    async def _scan_files(self, source: FileSource, path: str, kb_name: Optional[str] = None, 
                         repository = None, sync_run_id = None):
        """Scan files without progress indicator."""
        file_count = 0
        stats = {'total': 0, 'new': 0, 'modified': 0}
        async for file_metadata in source.stream_files(path):
            file_count += 1
            await self._process_file(source, file_metadata, kb_name, repository, sync_run_id)
            stats['total'] += 1
            stats['new'] += 1  # For scan, all files are considered "new"
        
        console.print(f"\n[green]Scan complete. Found {file_count} files.[/green]")
        
        # Update sync run with statistics
        if repository and sync_run_id:
            await repository.update_sync_run_stats(sync_run_id, stats)
    
    async def _process_file(self, source: FileSource, file_metadata, kb_name: Optional[str] = None, 
                           repository = None, sync_run_id = None):
        """Process a single file and print its information."""
        try:
            # Get file content and calculate hash
            content = await source.get_file_content(file_metadata.uri)
            file_hash = await self.file_processor.calculate_hash(content)
            
            # Generate UUID filename
            uuid_filename = self.file_processor.generate_uuid_filename(file_metadata.uri)
            
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
                    'status': 'scanned'  # Use scanned status for scan runs
                }
                await repository.create_file_record(file_record)
            
            # Print file information with UUID on single line
            size_str = self._format_size(file_metadata.size)
            console.print(
                f"[blue]{file_metadata.uri}[/blue] | "
                f"UUID: [yellow]{uuid_filename}[/yellow] | "
                f"Hash: [green]{file_hash[:16]}...[/green] | "
                f"Size: [cyan]{size_str}[/cyan] | "
                f"Type: [dim]{file_metadata.content_type}[/dim]"
            )
            
        except Exception as e:
            console.print(
                f"[red]Error processing {file_metadata.uri}: {str(e)}[/red]"
            )
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"
    
    async def print_summary_table(self, source: FileSource, path: str = "", kb_name: Optional[str] = None):
        """Print a summary table of all files."""
        await source.initialize()
        
        try:
            files = await source.list_files(path)
            
            if not files:
                console.print("[yellow]No files found.[/yellow]")
                return
            
            table = Table(
                title=f"File Scan Summary ({path or 'root'})",
                style="cyan",
                header_style="bold magenta",
            )
            table.add_column("Path", style="blue", no_wrap=True)
            table.add_column("UUID", style="yellow")
            table.add_column("Size", style="cyan", justify="right")
            table.add_column("Hash", style="green")
            table.add_column("Type", style="dim")
            table.add_column("Modified", style="cyan")
            
            total_size = 0
            for file_metadata in files:
                try:
                    content = await source.get_file_content(file_metadata.uri)
                    file_hash = await self.file_processor.calculate_hash(content)
                    uuid_filename = self.file_processor.generate_uuid_filename(file_metadata.uri)
                    
                    size_str = self._format_size(file_metadata.size)
                    modified_str = file_metadata.modified_at.strftime("%Y-%m-%d %H:%M")
                    
                    table.add_row(
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
            
        finally:
            await source.cleanup()