#!/usr/bin/env python3
"""
Test script to demonstrate UUID consistency functionality.
"""

import asyncio
from pathlib import Path
from rich.console import Console

from src.core.file_processor import FileProcessor

console = Console()

async def test_uuid_consistency():
    """Test UUID consistency with the file processor."""
    
    console.print("[bold blue]Testing UUID Consistency[/bold blue]\n")
    
    file_processor = FileProcessor()
    original_filename = "/data/documents/report.pdf"
    
    # First time - no existing UUID
    console.print("[bold]First scan/upload - new file:[/bold]")
    uuid_filename_1 = file_processor.generate_uuid_filename(original_filename)
    console.print(f"Original: {original_filename}")
    console.print(f"UUID:     {uuid_filename_1}")
    console.print(f"RAG URI:  {file_processor.generate_rag_uri('my-kb', uuid_filename_1)}\n")
    
    # Second time - use existing UUID
    console.print("[bold]Second scan/upload - file modified:[/bold]")
    uuid_filename_2 = file_processor.generate_uuid_filename(original_filename, existing_uuid=uuid_filename_1)
    console.print(f"Original: {original_filename}")
    console.print(f"UUID:     {uuid_filename_2}")
    console.print(f"RAG URI:  {file_processor.generate_rag_uri('my-kb', uuid_filename_2)}")
    
    # Verify they're the same
    if uuid_filename_1 == uuid_filename_2:
        console.print("\n[green]✓ UUID remained consistent![/green]")
    else:
        console.print("\n[red]✗ UUID changed (this shouldn't happen)[/red]")
    
    # Test with different file extension
    console.print("\n[bold]Testing with different extension:[/bold]")
    different_file = "/data/documents/report.docx"
    uuid_filename_3 = file_processor.generate_uuid_filename(different_file, existing_uuid=uuid_filename_1)
    console.print(f"Original: {different_file}")
    console.print(f"UUID:     {uuid_filename_3}")
    console.print("Note: Same UUID base, different extension")
    
    # Extract UUID parts for comparison
    uuid_base_1 = uuid_filename_1.split('.')[0]
    uuid_base_3 = uuid_filename_3.split('.')[0]
    
    if uuid_base_1 == uuid_base_3:
        console.print("[green]✓ UUID base remained consistent![/green]")
    else:
        console.print("[red]✗ UUID base changed[/red]")

if __name__ == "__main__":
    console.print("[cyan]UUID Consistency Test[/cyan]")
    console.print("[dim]This demonstrates how UUIDs remain consistent across operations[/dim]\n")
    
    asyncio.run(test_uuid_consistency())
    
    console.print("\n[bold]Key Points:[/bold]")
    console.print("• Once assigned, a UUID stays with the file")
    console.print("• Modified files keep their original UUID")
    console.print("• RAG URIs remain stable for updates")
    console.print("• File extensions are preserved correctly")