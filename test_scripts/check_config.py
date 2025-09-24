#!/usr/bin/env python3
"""Check how the configuration is structured"""

import json
from pathlib import Path

# Simulate how the configuration is passed to FileSystemStorage
# Based on the actual usage

print("Current directory structure:")
base_path = Path("/Users/giorgosmarinos/Documents/KBRoot")
test_docs_path = base_path / "test-docs"
default_path = test_docs_path / "default"

print(f"Base path exists: {base_path.exists()}")
print(f"Test-docs path exists: {test_docs_path.exists()}")
print(f"Default path exists: {default_path.exists()}")

if test_docs_path.exists():
    print(f"\nContents of {test_docs_path}:")
    for item in test_docs_path.iterdir():
        print(f"  {item.name}/ (dir)" if item.is_dir() else f"  {item.name}")

# The configuration would typically be:
config = {
    'storage_path': '/Users/giorgosmarinos/Documents/KBRoot/test-docs',
    'kb_name': 'test-docs'  # This is redundant if the path already includes it
}

print(f"\nConfiguration: {json.dumps(config, indent=2)}")