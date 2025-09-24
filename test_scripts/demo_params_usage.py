#!/usr/bin/env python3
"""
Demonstration of how to use command line parameters from anywhere in the application
"""
import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.params import get_params

def demo_function():
    """Example function showing how to access CLI parameters"""
    params = get_params()
    
    print("Command Line Parameters Demo")
    print("=" * 30)
    print(f"Verbose mode: {params.verbose}")
    print(f"Log level: {params.get_log_level()}")
    print(f"KB name: {params.kb_name}")
    print(f"Path: {params.path}")
    print(f"Source type: {params.source_type}")
    print(f"Recursive: {params.recursive}")
    print("\nRaw arguments:")
    for key, value in params.raw_args.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    # Simulate parameters being set (normally done by the CLI)
    from src.cli.params import update_params
    
    print("Setting demo parameters...")
    update_params(
        verbose=True,
        kb_name="test-kb",
        path="/test/path",
        source_type="file_system",
        recursive=True
    )
    
    print("\nCalling demo function...")
    demo_function()