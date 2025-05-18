#!/usr/bin/env python3
"""
Simple test to verify verbose logging
"""
import subprocess
import os

# Change to project directory
os.chdir("/Users/giorgosmarinos/aiwork/IDP/document-loader")

# Activate virtual environment
venv_activate = ". .venv/bin/activate"

# Test 1: Normal output
print("=== Test 1: Normal logging ===")
result = subprocess.run(
    f"{venv_activate} && document-loader list-kb", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print("Exit code:", result.returncode)
print("Output:")
print(result.stderr)
print(result.stdout)

print("\n" + "="*50 + "\n")

# Test 2: Verbose output
print("=== Test 2: Verbose logging (should show DEBUG messages) ===")
result = subprocess.run(
    f"{venv_activate} && document-loader --verbose list-kb", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print("Exit code:", result.returncode)
print("Output:")
print(result.stderr)
print(result.stdout)