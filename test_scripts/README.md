# Test Scripts

This directory contains various test scripts used to verify and debug the document-loader application operations.

## Scripts Overview

### Core Test Scripts

#### run_all_tests.py
Comprehensive test runner that executes the main test scenarios including directory structure, URI mapping, and file operations.

### File System Storage Tests

#### test_deletion.py
Tests the file deletion functionality in FileSystemStorage. Verifies that files are correctly deleted from the storage location when given a database URI.

#### test_new_structure.py
Tests the updated directory structure (without the unnecessary "default" subdirectories). Creates a temporary directory to verify that files are stored directly under `documents/` and `metadata/` folders.

#### test_actual_storage.py
Tests with the actual storage path configuration. Verifies URI conversion and checks the current directory structure.

#### test_file_system_storage.py
Basic tests for the FileSystemStorage implementation.

#### test_filesystem_storage_fix.py
Tests for fixes applied to the FileSystemStorage implementation.

### URI and Path Management Tests

#### test_uri_mapping.py
Tests the URI mapping between database format and file system paths. Verifies that:
- Database URIs (`test-docs/filename.md`) are correctly converted to file paths
- File paths are correctly converted back to database URIs
- Upload and deletion operations work with the correct paths

#### test_consistent_rag_uri.py
Tests RAG URI consistency across the system.

#### test_consistent_uris.py
General URI consistency tests.

#### test_database_full_path.py
Tests full path handling in database operations.

#### test_full_path_preservation.py
Tests that full paths are preserved correctly throughout the system.

### UUID and Identification Tests

#### test_uuid_consistency.py
Tests UUID consistency across operations.

#### test_uuid_generation.py
Tests UUID generation logic.

### Synchronization and Change Detection Tests

#### test_sync_consistency.py
Tests synchronization consistency between source and RAG storage.

#### test_change_detection.py
Tests the change detection mechanism for identifying new, modified, and deleted files.

#### test_change_detector_direct.py
Direct tests for the change detector component.

#### test_hash_detection.py
Tests file change detection using hash comparison.

#### test_delete_reappear.py
Tests scenarios where deleted files might reappear.

#### test_duplicate_delete.py
Tests handling of duplicate deletion operations.

### Restoration and Recovery Tests

#### test_comprehensive_restore.py
Comprehensive tests for file restoration functionality.

#### test_restore_file.py
Basic file restoration tests.

### Integration Tests

#### test_full_sync.py
Tests the full synchronization functionality including:
- Listing files in the documents directory
- Testing file deletion using database URI format
- Verifying that files are removed from the correct location

#### test_all_fixes.py
Integration tests for all implemented fixes.

### Utility Scripts

#### check_config.py
Checks the configuration structure and current directory layout. Helps understand how the knowledge base configuration is passed to FileSystemStorage.

#### migrate_storage.py
Migration script to move files from the old directory structure (with nested "default" directories) to the new simplified structure.

### Pattern Matching Tests

#### test_match.py
Basic pattern matching tests.

#### test_pattern.py
Advanced pattern matching tests.

## Running the Tests

All test scripts can be run from the project root directory with the virtual environment activated:

```bash
source .venv/bin/activate

# Run all tests
python test_scripts/run_all_tests.py

# Run individual tests
python test_scripts/test_name.py
```

Note: Some scripts may require database connectivity or actual storage paths to exist.

## Test Categories

1. **Storage Tests**: Focus on file system operations
2. **URI Tests**: Verify URI/path mappings
3. **Sync Tests**: Test synchronization logic
4. **Detection Tests**: Test change detection
5. **Recovery Tests**: Test restoration capabilities
6. **Integration Tests**: Test complete workflows