#!/usr/bin/env python3
"""
Comprehensive diagnostic script for azwrap
"""
import sys
import inspect
import pkgutil

def diagnose_azwrap():
    """Comprehensive diagnostic of azwrap package"""
    print("=== AZWRAP DIAGNOSTIC ===\n")
    
    try:
        import azwrap
        print(f"✓ azwrap imported successfully")
        print(f"  Location: {azwrap.__file__}")
        print(f"  Version: {getattr(azwrap, '__version__', 'not specified')}")
        
        # List all attributes
        print("\n1. All attributes in azwrap:")
        for name in sorted(dir(azwrap)):
            obj = getattr(azwrap, name)
            if not name.startswith('_'):
                print(f"  {name}: {type(obj)}")
        
        # Check for submodules
        print("\n2. Checking for submodules:")
        if hasattr(azwrap, '__path__'):
            for importer, modname, ispkg in pkgutil.iter_modules(azwrap.__path__, azwrap.__name__ + "."):
                print(f"  {modname} (package: {ispkg})")
        
        # Inspect StorageAccount class
        print("\n3. StorageAccount class inspection:")
        if hasattr(azwrap, 'StorageAccount'):
            sa = azwrap.StorageAccount
            methods = [m for m in dir(sa) if not m.startswith('_') and callable(getattr(sa, m, None))]
            print("  Methods:")
            for method in sorted(methods):
                print(f"    - {method}")
                # Get method signature if possible
                try:
                    sig = inspect.signature(getattr(sa, method))
                    print(f"      {sig}")
                except:
                    pass
        
        # Check for blob/container related functionality
        print("\n4. Container-related methods in StorageAccount:")
        if hasattr(azwrap, 'StorageAccount'):
            sa = azwrap.StorageAccount
            container_methods = [m for m in dir(sa) if ('container' in m.lower() or 'blob' in m.lower()) and not m.startswith('_')]
            for method in sorted(container_methods):
                print(f"  - {method}")
                try:
                    sig = inspect.signature(getattr(sa, method))
                    print(f"    Signature: {sig}")
                except:
                    pass
        
        # Try to find the actual container class
        print("\n5. Looking for container classes:")
        for name in dir(azwrap):
            obj = getattr(azwrap, name)
            if 'container' in name.lower() or (hasattr(obj, '__name__') and 'container' in obj.__name__.lower()):
                print(f"  Found: {name} - {type(obj)}")
        
    except ImportError as e:
        print(f"✗ Error importing azwrap: {e}")
        print("\nMake sure azwrap is installed: pip install azwrap")
        return
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_azwrap()
    
    print("\n=== RECOMMENDATIONS ===")
    print("Based on the diagnostic, you should:")
    print("1. Check if BlobContainer is returned by StorageAccount.get_blob_container()")
    print("2. Use the container object returned by these methods, not import BlobContainer")
    print("3. Consider using the official Azure SDK if azwrap doesn't meet your needs")
    print("\nRun this script in your environment to see the actual structure of azwrap")