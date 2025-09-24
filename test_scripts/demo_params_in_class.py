#!/usr/bin/env python3
"""
Demonstration of how to use CommandLineParams within a class
"""
import sys
import os
import logging

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.params import get_params
from src.core.scanner import FileScanner
from src.data.repository import Repository


class MyCustomProcessor:
    """Example class that uses command line parameters"""
    
    def __init__(self):
        # Get the command line parameters
        self.params = get_params()
        self.logger = logging.getLogger(__name__)
    
    def process(self):
        """Process files using CLI parameters"""
        # Access verbose flag
        if self.params.verbose:
            self.logger.debug("Verbose mode is enabled")
            self.logger.debug(f"Processing KB: {self.params.kb_name}")
        
        # Access other parameters
        print(f"Knowledge Base: {self.params.kb_name}")
        print(f"Source Type: {self.params.source_type}")
        print(f"Path: {self.params.path}")
        print(f"Recursive: {self.params.recursive}")
        print(f"Table Output: {self.params.table}")
        print(f"Update DB: {self.params.update_db}")
        
        # Use log level
        print(f"Current log level: {self.params.get_log_level()}")
        
        # Check raw arguments
        print("\nRaw arguments available:")
        for key, value in self.params.raw_args.items():
            print(f"  {key}: {value}")


class ExistingModuleAdapter:
    """Example of adapting existing modules to use CLI params"""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self.params = get_params()
    
    async def perform_sync(self):
        """Sync operation that uses CLI params"""
        kb_name = self.params.kb_name or "default-kb"
        
        if self.params.verbose:
            print(f"DEBUG: Starting sync for {kb_name}")
            print(f"DEBUG: Run once mode: {self.params.run_once}")
        
        # Your sync logic here
        print(f"Syncing knowledge base: {kb_name}")
        
        # You can check specific params conditionally
        if self.params.update_db:
            print("Database will be updated")
        else:
            print("Dry run - database will not be updated")


# Real-world example showing integration with existing classes
class EnhancedScanner(FileScanner):
    """Example of extending existing class with CLI params"""
    
    def __init__(self):
        super().__init__()
        self.params = get_params()
    
    async def scan_with_params(self, source):
        """Scan using CLI parameters"""
        if self.params.verbose:
            print("DEBUG: Enhanced scanner starting")
            print(f"DEBUG: Table output: {self.params.table}")
            print(f"DEBUG: Recursive: {self.params.recursive}")
        
        # Use params to control behavior
        if self.params.table:
            print(f"Would display table for KB: {self.params.kb_name}")
        else:
            print(f"Would scan source with progress: {not self.params.verbose}")


if __name__ == "__main__":
    # Example usage
    from src.cli.params import update_params
    
    # Simulate CLI parameters being set
    print("Setting demo parameters...")
    update_params(
        verbose=True,
        kb_name="test-kb",
        path="/test/path",
        source_type="file_system",
        recursive=True,
        table=True,
        update_db=False
    )
    
    # Test custom processor
    print("\n=== Custom Processor Example ===")
    processor = MyCustomProcessor()
    processor.process()
    
    # Test adapter pattern
    print("\n=== Adapter Pattern Example ===")
    # Mock repository for demo
    class MockRepo:
        pass
    
    adapter = ExistingModuleAdapter(MockRepo())
    import asyncio
    asyncio.run(adapter.perform_sync())
    
    # Test inheritance pattern
    print("\n=== Inheritance Pattern Example ===")
    scanner = EnhancedScanner()
    
    # Mock source for demo
    class MockSource:
        pass
    
    asyncio.run(scanner.scan_with_params(MockSource()))