#!/usr/bin/env python3
"""
Test Azure logging suppression
"""
import subprocess
import os

os.chdir("/Users/giorgosmarinos/aiwork/IDP/document-loader")
venv_activate = ". .venv/bin/activate"

print("=== Test 1: Normal sync (Azure logs should be suppressed) ===")
result = subprocess.run(
    f"{venv_activate} && document-loader sync --kb-name azure-docs 2>&1 | grep -E '(Request URL|Response status|ClientSecretCredential)' | wc -l", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print(f"Number of Azure log lines found: {result.stdout.strip()}")
print("(Should be 0 or very few)\n")

print("=== Test 2: Verbose sync (Azure logs should be shown) ===")
result = subprocess.run(
    f"{venv_activate} && document-loader --verbose sync --kb-name azure-docs 2>&1 | grep -E '(Request URL|Response status|ClientSecretCredential)' | wc -l", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print(f"Number of Azure log lines found: {result.stdout.strip()}")
print("(Should be many)\n")

# Show a sample of output
print("=== Sample output without verbose ===")
result = subprocess.run(
    f"{venv_activate} && document-loader sync --kb-name azure-docs 2>&1 | head -30", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print(result.stdout[:1000] + "..." if len(result.stdout) > 1000 else result.stdout)