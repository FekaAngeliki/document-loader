# Verbose Flag and Command Line Parameters Guide

## Overview

The Document Loader CLI now supports a global `--verbose` flag that enables DEBUG level logging across all commands. Additionally, all command line parameters are now accessible from anywhere in the application through a centralized parameter management system.

## Using the --verbose Flag

The `--verbose` flag is a global option that must be placed **BEFORE** the subcommand to enable detailed debug logging:

```bash
# Normal output
document-loader list-kb

# CORRECT - Verbose flag BEFORE subcommand
document-loader --verbose list-kb
document-loader --verbose sync --kb-name my-kb
document-loader --verbose scan --path /path/to/docs

# INCORRECT - This will not work!
document-loader sync --verbose --kb-name my-kb  # ERROR!
document-loader list-kb --verbose               # ERROR!
```

**Important**: Always place `--verbose` between `document-loader` and the subcommand name.

When the `--verbose` flag is used:
- The logging level is automatically set to DEBUG
- Additional debug messages from libraries and the application are displayed
- Useful for troubleshooting and understanding the internal operations

## Command Line Parameters Class

All command line parameters are now managed through the `CommandLineParams` class located in `src/cli/params.py`.

### Structure

```python
from src.cli.params import get_params, update_params

# Access parameters from anywhere in the application
params = get_params()

# Check if verbose mode is enabled
if params.verbose:
    logging.debug("Debug mode is enabled")

# Get the effective log level
log_level = params.get_log_level()  # Returns "DEBUG" if verbose, otherwise "INFO"

# Access other parameters
kb_name = params.kb_name
source_type = params.source_type
path = params.path
```

### Available Parameters

The `CommandLineParams` class includes:

**Global Flags:**
- `verbose`: Boolean flag for verbose logging
- `log_level`: String representing the log level (INFO or DEBUG)

**Command-specific Parameters:**
- `kb_name`: Knowledge base name
- `source_type`: Source type for documents
- `source_config`: Source configuration dictionary
- `rag_type`: RAG system type
- `rag_config`: RAG configuration dictionary
- `path`: File system path
- `recursive`: Recursive scan flag
- `table`: Table output format flag
- `update_db`: Update database flag
- `limit`: Result limit for queries
- `run_once`: Run once flag
- `no_schema`: Skip schema creation flag
- `create_db`: Create database flag

### Usage in Application Code

Any module in the application can access command line parameters:

```python
from src.cli.params import get_params

def my_function():
    params = get_params()
    
    if params.verbose:
        print("Verbose mode is enabled")
    
    if params.kb_name:
        print(f"Working with knowledge base: {params.kb_name}")
```

### Implementation Details

The parameter system uses:
- Thread-local storage to maintain parameters across function calls
- Automatic extraction from Click context
- Support for parameter updates during command execution

### Environment Variable Fallback

The log level can still be set via environment variable as a fallback:
```bash
export DOCUMENT_LOADER_LOG_LEVEL=DEBUG
```

However, the `--verbose` flag takes precedence over the environment variable.

## Examples

### Basic Usage

```bash
# Enable verbose logging for any command
document-loader --verbose check-connection
document-loader --verbose create-kb --name test-kb --source-type file_system --source-config '{"root_path": "/docs"}'
```

### In Code

```python
from src.cli.params import get_params
import logging

def process_files():
    params = get_params()
    
    if params.verbose:
        logging.debug(f"Processing files for KB: {params.kb_name}")
        logging.debug(f"Source type: {params.source_type}")
        logging.debug(f"Path: {params.path}")
    
    # Your processing logic here
```

## Benefits

1. **Centralized Parameter Management**: All CLI parameters are accessible from a single location
2. **Type Safety**: Parameters are defined with proper types in the dataclass
3. **Easy Debugging**: The verbose flag makes it simple to enable debug logging
4. **Consistent Interface**: All commands support the same verbose flag
5. **Extensible**: New parameters can be easily added to the `CommandLineParams` class

## Future Enhancements

The command line parameter system can be extended to:
- Add more global flags (e.g., `--quiet`, `--no-color`)
- Support configuration file loading
- Add parameter validation
- Include parameter documentation