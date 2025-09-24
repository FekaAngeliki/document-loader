#!/usr/bin/env python3
"""
Test to verify the correct order of verbose flag
"""
import subprocess
import os

os.chdir("/Users/giorgosmarinos/aiwork/IDP/document-loader")
venv_activate = ". .venv/bin/activate"

print("=== Test 1: CORRECT - Verbose flag BEFORE subcommand ===")
result = subprocess.run(
    f"{venv_activate} && document-loader --verbose sync --kb-name azure-docs --run-once", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print("Exit code:", result.returncode)
print("Output (first 10 lines):")
output_lines = (result.stdout + result.stderr).splitlines()
for line in output_lines[:10]:
    print(line)

print("\n" + "="*50 + "\n")

print("=== Test 2: INCORRECT - Verbose flag AFTER subcommand ===")
result = subprocess.run(
    f"{venv_activate} && document-loader sync --kb-name azure-docs --verbose", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print("Exit code:", result.returncode)
print("Output:")
print(result.stderr)
print(result.stdout)