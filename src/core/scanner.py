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
    
    async def scan_source(self, source: FileSource, path: str = "", show_progress: bool = True):
        """Scan files from a source and print information."""
        await source.initialize()
        
        try:
            if show_progress:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Scanning files...", total=None)
                    await self._scan_with_progress(source, path, progress, task)
            else:
                await self._scan_files(source, path)
        finally:
            await source.cleanup()
    
    async def _scan_with_progress(self, source: FileSource, path: str, progress: Progress, task):
        """Scan files with progress indicator."""
        file_count = 0
        async for file_metadata in source.stream_files(path):
            file_count += 1
            progress.update(task, description=f"Scanning files... [{file_count}]")
            await self._process_file(source, file_metadata)
        
        progress.update(task, description=f"Scan complete. Found {file_count} files.")
    
    async def _scan_files(self, source: FileSource, path: str):
        """Scan files without progress indicator."""
        file_count = 0
        async for file_metadata in source.stream_files(path):
            file_count += 1
            await self._process_file(source, file_metadata)
        
        console.print(f"\n[green]Scan complete. Found {file_count} files.[/green]")
    
    async def _process_file(self, source: FileSource, file_metadata):
        """Process a single file and print its information."""
        try:
            # Get file content and calculate hash
            content = await source.get_file_content(file_metadata.uri)
            file_hash = await self.file_processor.calculate_hash(content)
            
            # Print file information
            size_str = self._format_size(file_metadata.size)
            console.print(
                f"[blue]{file_metadata.uri}[/blue] | "
                f"[yellow]{size_str}[/yellow] | "
                f"[green]{file_hash[:16]}...[/green] | "
                f"[dim]{file_metadata.content_type}[/dim]"
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
    
    async def print_summary_table(self, source: FileSource, path: str = ""):
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
            table.add_column("Size", style="yellow", justify="right")
            table.add_column("Hash", style="green")
            table.add_column("Type", style="dim")
            table.add_column("Modified", style="cyan")
            
            total_size = 0
            for file_metadata in files:
                try:
                    content = await source.get_file_content(file_metadata.uri)
                    file_hash = await self.file_processor.calculate_hash(content)
                    
                    size_str = self._format_size(file_metadata.size)
                    modified_str = file_metadata.modified_at.strftime("%Y-%m-%d %H:%M")
                    
                    table.add_row(
                        file_metadata.uri,
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
                        file_metadata.content_type,
                        file_metadata.modified_at.strftime("%Y-%m-%d %H:%M")
                    )
            
            console.print(table)
            console.print(f"\n[bold]Total files:[/bold] {len(files)}")
            console.print(f"[bold]Total size:[/bold] {self._format_size(total_size)}")
            
        finally:
            await source.cleanup()