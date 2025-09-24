#!/usr/bin/env python3
"""
Example showing how to integrate CommandLineParams into existing modules
"""
import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.params import get_params


# Example 1: Simple function in a module
def process_files(file_list):
    """Process files with optional verbose output"""
    params = get_params()
    
    for file in file_list:
        if params.verbose:
            print(f"DEBUG: Processing {file}")
        # Process file here
        print(f"Processing: {file}")


# Example 2: Existing class with minimal modification
class FileProcessor:
    def __init__(self, config):
        self.config = config
        # Add params access
        self.params = get_params()
    
    def process(self, filepath):
        if self.params.verbose:
            print(f"DEBUG: FileProcessor starting for {filepath}")
            print(f"DEBUG: Config: {self.config}")
        
        # Original processing logic
        print(f"Processing file: {filepath}")
        
        # Use params to control behavior
        if self.params.update_db:
            print("Updating database...")
        else:
            print("Skipping database update (dry run)")


# Example 3: Utility function to check verbose mode
def log_debug(message):
    """Log a debug message if verbose mode is enabled"""
    params = get_params()
    if params.verbose:
        print(f"DEBUG: {message}")


# Example 4: Decorator pattern for verbose logging
def with_verbose_logging(func):
    """Decorator that adds verbose logging to a function"""
    def wrapper(*args, **kwargs):
        params = get_params()
        if params.verbose:
            print(f"DEBUG: Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        result = func(*args, **kwargs)
        
        if params.verbose:
            print(f"DEBUG: {func.__name__} returned: {result}")
        
        return result
    return wrapper


@with_verbose_logging
def calculate_hash(filepath):
    """Example function with verbose logging decorator"""
    # Simulate hash calculation
    return f"hash_of_{filepath}"


# Example 5: Class that conditionally enables features based on params
class SmartProcessor:
    def __init__(self):
        self.params = get_params()
        
        # Enable features based on params
        self.enable_caching = not self.params.verbose  # Disable cache in verbose mode
        self.batch_size = 1 if self.params.verbose else 100  # Smaller batches in verbose
    
    def process_batch(self, items):
        if self.params.verbose:
            print(f"DEBUG: Processing batch of {len(items)} items")
            print(f"DEBUG: Caching: {self.enable_caching}")
            print(f"DEBUG: Batch size: {self.batch_size}")
        
        for item in items:
            self._process_item(item)
    
    def _process_item(self, item):
        if self.params.verbose:
            print(f"DEBUG: Processing item: {item}")
        # Process item
        print(f"Processed: {item}")


if __name__ == "__main__":
    from src.cli.params import update_params
    
    # Set parameters for demo
    print("=== Demo with verbose=False ===")
    update_params(verbose=False, update_db=True)
    
    # Test simple function
    process_files(["file1.txt", "file2.txt"])
    
    # Test class
    processor = FileProcessor({"key": "value"})
    processor.process("test.txt")
    
    # Test decorated function
    result = calculate_hash("document.pdf")
    print(f"Hash: {result}")
    
    print("\n=== Demo with verbose=True ===")
    update_params(verbose=True, update_db=False)
    
    # Test simple function with verbose
    process_files(["file1.txt", "file2.txt"])
    
    # Test class with verbose
    processor = FileProcessor({"key": "value"})
    processor.process("test.txt")
    
    # Test decorated function with verbose
    result = calculate_hash("document.pdf")
    
    # Test smart processor
    smart = SmartProcessor()
    smart.process_batch(["item1", "item2", "item3"])