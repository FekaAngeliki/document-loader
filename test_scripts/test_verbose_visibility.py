#!/usr/bin/env python3
"""
Test to verify verbose flag visibility in help messages
"""
import subprocess
import os

os.chdir("/Users/giorgosmarinos/aiwork/IDP/document-loader")
venv_activate = ". .venv/bin/activate"

print("=== Test 1: Plain help command ===")
result = subprocess.run(
    f"{venv_activate} && document-loader --help", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print("Exit code:", result.returncode)
print("\nShowing OPTIONS section:")
output_lines = result.stdout.splitlines()
in_options = False
for line in output_lines:
    if "OPTIONS:" in line:
        in_options = True
    elif in_options and line.strip() and not line.startswith("  "):
        in_options = False
    if in_options:
        print(line)

print("\n" + "="*50 + "\n")

print("=== Test 2: Quickstart command ===")
result = subprocess.run(
    f"{venv_activate} && document-loader quickstart", 
    shell=True, 
    capture_output=True, 
    text=True,
    executable='/bin/bash'
)
print("Exit code:", result.returncode)
print("\nShowing Getting Help section:")
output_lines = result.stdout.splitlines()
in_getting_help = False
for line in output_lines:
    if "Getting Help" in line:
        in_getting_help = True
    elif in_getting_help and line.strip() and not line.startswith(" "):
        if "─" not in line and "━" not in line and "┃" not in line:
            in_getting_help = False
    if in_getting_help:
        print(line)