#!/usr/bin/env python3
"""
Test script to demonstrate change detection functionality.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from rich.console import Console

from src.core.factory import SourceFactory
from src.core.scanner import FileScanner
from src.data.database import Database
from src.data.repository import Repository
from src.data.models import KnowledgeBase

console = Console()

async def test_change_detection():
    """Test change detection with a temporary directory."""
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        console.print(f"[bold blue]Testing change detection in: {temp_dir}[/bold blue]\n")
        
        # Create test files
        test_files = {
            "file1.txt": "This is file 1 content",
            "file2.txt": "This is file 2 content",
            "file3.txt": "This is file 3 content"
        }
        
        for filename, content in test_files.items():
            file_path = Path(temp_dir) / filename
            file_path.write_text(content)
        
        # Initialize database (in-memory for testing)
        db = Database("postgresql://user:pass@localhost/test_db")
        repository = Repository(db)
        
        # Create a test knowledge base
        kb = KnowledgeBase(
            name="test-kb",
            source_type="file_system",
            source_config={"root_path": temp_dir},
            rag_type="mock",
            rag_config={}
        )
        
        # Create scanner and source
        scanner = FileScanner()
        source_factory = SourceFactory()
        source = source_factory.create("file_system", {"root_path": temp_dir})
        
        console.print("[bold]First scan - all files should be new:[/bold]")
        await scanner.scan_source(source, kb_name="test-kb", repository=repository)
        
        console.print("\n[bold]Second scan - all files should be unchanged:[/bold]")
        source = source_factory.create("file_system", {"root_path": temp_dir})
        await scanner.scan_source(source, kb_name="test-kb", repository=repository)
        
        # Modify a file
        console.print("\n[bold]Modifying file2.txt...[/bold]")
        file2_path = Path(temp_dir) / "file2.txt"
        file2_path.write_text("This is MODIFIED file 2 content")
        
        console.print("\n[bold]Third scan - file2.txt should be modified:[/bold]")
        source = source_factory.create("file_system", {"root_path": temp_dir})
        await scanner.scan_source(source, kb_name="test-kb", repository=repository)
        
        # Add a new file
        console.print("\n[bold]Adding file4.txt...[/bold]")
        file4_path = Path(temp_dir) / "file4.txt"
        file4_path.write_text("This is file 4 content")
        
        console.print("\n[bold]Fourth scan - file4.txt should be new:[/bold]")
        source = source_factory.create("file_system", {"root_path": temp_dir})
        await scanner.scan_source(source, kb_name="test-kb", repository=repository)
        
        # Delete a file
        console.print("\n[bold]Deleting file1.txt...[/bold]")
        file1_path = Path(temp_dir) / "file1.txt"
        file1_path.unlink()
        
        console.print("\n[bold]Fifth scan - file1.txt should be detected as deleted:[/bold]")
        source = source_factory.create("file_system", {"root_path": temp_dir})
        await scanner.scan_source(source, kb_name="test-kb", repository=repository)

if __name__ == "__main__":
    # Note: This is a simplified test that demonstrates the concept
    # In reality, you'd need a running database and proper setup
    console.print("[yellow]Note: This is a demonstration script.[/yellow]")
    console.print("[yellow]For actual testing, you'll need a running PostgreSQL database.[/yellow]\n")
    
    # Show example output
    console.print("[bold]Example output with change detection:[/bold]\n")
    
    console.print("[green]+[/green] /test/file1.txt | UUID: abc123... | Hash: def456... | Size: 1.2KB")
    console.print("[green]+[/green] /test/file2.txt | UUID: ghi789... | Hash: jkl012... | Size: 1.5KB")
    console.print("[green]+[/green] /test/file3.txt | UUID: mno345... | Hash: pqr678... | Size: 1.1KB")
    console.print("\n[bold]Change Summary:[/bold]")
    console.print("┌─────────────────┬───────┐")
    console.print("│ New Files       │ 3     │")
    console.print("│ Modified Files  │ 0     │")
    console.print("│ Unchanged Files │ 0     │")
    console.print("└─────────────────┴───────┘")