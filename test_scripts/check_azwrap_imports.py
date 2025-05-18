#!/usr/bin/env python3
"""
Check what's available in the azwrap package
"""
import sys
import importlib
import inspect

def investigate_azwrap():
    """Check what's available in azwrap"""
    print("=== Investigating azwrap package ===\n")
    
    try:
        import azwrap
        print(f"azwrap module location: {azwrap.__file__}")
        print(f"azwrap version: {getattr(azwrap, '__version__', 'unknown')}")
        
        print("\nAvailable items in azwrap:")
        for name in dir(azwrap):
            if not name.startswith('_'):
                item = getattr(azwrap, name)
                print(f"  - {name}: {type(item)}")
        
        # Check if BlobContainer is in a submodule
        print("\nChecking for BlobContainer in submodules...")
        
        # Common patterns for Azure SDK
        possible_modules = [
            'azwrap.storage',
            'azwrap.blob',
            'azwrap.containers',
            'azwrap.storage_account',
        ]
        
        for module_name in possible_modules:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, 'BlobContainer'):
                    print(f"  ✓ Found BlobContainer in {module_name}")
                    break
            except ImportError:
                print(f"  - Module {module_name} not found")
        
        # Check StorageAccount class for blob container methods
        print("\nChecking StorageAccount class methods:")
        if hasattr(azwrap, 'StorageAccount'):
            storage_account_class = azwrap.StorageAccount
            methods = [method for method in dir(storage_account_class) if not method.startswith('_')]
            for method in methods:
                if 'blob' in method.lower() or 'container' in method.lower():
                    print(f"  - {method}")
        
    except ImportError as e:
        print(f"Error importing azwrap: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    investigate_azwrap()