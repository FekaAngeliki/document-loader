#!/usr/bin/env python3
"""
Example of using include_extensions with FileSystemSource

This example demonstrates how to use the include_extensions configuration
to filter files based on their extensions.
"""

import asyncio
from src.implementations.file_system_source import FileSystemSource

async def main():
    # Example 1: Only include PDF and Word documents
    config_pdf_docx = {
        "root_path": "/path/to/documents",
        "include_extensions": [".pdf", ".docx"]
    }
    
    # Example 2: Include specific extensions and exclude temporary files
    config_filtered = {
        "root_path": "/path/to/documents",
        "include_extensions": [".pdf", ".md", ".txt"],
        "exclude_extensions": [".tmp", ".bak"]
    }
    
    # Example 3: Combine include_extensions with patterns
    config_combined = {
        "root_path": "/path/to/documents",
        "include_patterns": ["docs/**", "reports/**"],
        "include_extensions": [".pdf", ".md"],
        "exclude_patterns": ["**/drafts/**"]
    }
    
    # Example 4: Extension filtering is case-insensitive
    config_case_insensitive = {
        "root_path": "/path/to/documents",
        "include_extensions": [".PDF", ".DOCX", ".md"],  # Will match .pdf, .docx, .MD etc.
    }
    
    # Initialize and use the source
    source = FileSystemSource(config_pdf_docx)
    await source.initialize()
    
    files = await source.list_files()
    for file in files:
        print(f"Found file: {file.uri} (size: {file.size} bytes)")
    
    await source.cleanup()

if __name__ == "__main__":
    asyncio.run(main())