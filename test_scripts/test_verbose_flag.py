#!/usr/bin/env python3
"""
Test script to verify the --verbose flag functionality
"""
import subprocess
import sys
import tempfile
import json
import os

def run_command(cmd):
    """Run a command and capture output"""
    print(f"\n=== Running: {' '.join(cmd)} ===")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
    return result

def test_verbose_flag():
    """Test the verbose flag in various commands"""
    print("Testing Document Loader --verbose flag")
    print("=" * 50)
    
    # Test 1: Help message without verbose
    print("\nTest 1: Help without verbose")
    run_command(["document-loader", "--help"])
    
    # Test 2: Help message with verbose
    print("\nTest 2: Help with verbose")
    run_command(["document-loader", "--verbose", "--help"])
    
    # Test 3: Check connection without verbose
    print("\nTest 3: Check connection without verbose")
    run_command(["document-loader", "check-connection"])
    
    # Test 4: Check connection with verbose
    print("\nTest 4: Check connection with verbose")
    run_command(["document-loader", "--verbose", "check-connection"])
    
    # Test 5: List knowledge bases without verbose
    print("\nTest 5: List KB without verbose")
    run_command(["document-loader", "list-kb"])
    
    # Test 6: List knowledge bases with verbose
    print("\nTest 6: List KB with verbose")
    run_command(["document-loader", "--verbose", "list-kb"])
    
    # Test 7: Scan with verbose
    print("\nTest 7: Scan with verbose (should show more debug info)")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Test content")
        
        run_command([
            "document-loader", "--verbose", "scan",
            "--path", tmpdir,
            "--source-type", "file_system",
            "--source-config", json.dumps({"root_path": tmpdir})
        ])
    
    print("\n" + "=" * 50)
    print("Verbose flag testing complete!")
    print("Check the output above to see if DEBUG logging is enabled with --verbose")

if __name__ == "__main__":
    test_verbose_flag()