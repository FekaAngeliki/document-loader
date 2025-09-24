# Logging Configuration Guide

## Overview

The Document Loader application provides configurable logging with special handling for Azure SDK messages. By default, Azure SDK HTTP request/response logs are suppressed to keep the output clean. Use the `--verbose` flag to see detailed debug information.

## Logging Levels

### Default Mode (without --verbose)
- Application logs: INFO level
- Azure SDK logs: WARNING level (suppresses HTTP request/response details)
- Shows only important operational messages

### Verbose Mode (with --verbose)
- Application logs: DEBUG level
- Azure SDK logs: DEBUG level (shows HTTP request/response details)
- Shows detailed information for troubleshooting

## Azure Logging Configuration

Azure SDK logging is now managed directly in the `azure_blob_rag_system` module to keep Azure dependencies centralized. This means:
- Azure logging configuration is only loaded when using Azure Blob storage
- Other RAG systems don't need to handle Azure-specific logging
- Keeps the core CLI free from Azure-specific dependencies

When using Azure Blob storage, the following Azure SDK loggers are configured:
- `azure.core.pipeline.policies.http_logging_policy`
- `azure.identity._universal`
- `azure.identity.get_token_mixin`
- `azure.mgmt`
- `azure.storage.blob`
- And other related Azure loggers

## Usage Examples

### Normal Operation (Clean Output)
```bash
document-loader sync --kb-name azure-docs
```

Output will show:
- Progress indicators
- Change detection summary
- Processing results
- Final sync statistics

### Verbose Operation (Detailed Debug)
```bash
document-loader --verbose sync --kb-name azure-docs
```

Output will include:
- All normal output
- Azure HTTP request/response details
- Authentication token requests
- Storage account operations
- Detailed debug messages

## Environment Variables

You can also control logging via environment variable:
```bash
export DOCUMENT_LOADER_LOG_LEVEL=DEBUG
```

However, the `--verbose` flag takes precedence and provides better control over Azure SDK logging.

## Custom Logging Configuration

The logging configuration is managed in:
- `src/core/logging_config.py` - Application logging configuration
- `src/implementations/azure_blob_rag_system.py` - Azure-specific logging configuration
- `document_loader/cli.py` - CLI integration

### Architecture

The logging configuration follows the principle of keeping dependencies localized:
1. **Application logging** is configured in `logging_config.py`
2. **Azure-specific logging** is configured within the Azure Blob RAG system
3. **CLI** only handles general logging setup

### Adding New RAG Systems

When adding a new RAG system that has its own SDK with verbose logging:
1. Configure the SDK's logging within the RAG implementation
2. Use the `verbose` parameter passed to the RAG system to control logging levels
3. Keep SDK-specific dependencies within the implementation

## Troubleshooting

If you still see unwanted Azure logs:
1. Use `--verbose` flag to see all logs
2. Identify the logger name in the output
3. Add it to the Azure logging configuration in `azure_blob_rag_system.py`
4. The Azure logging configuration is in the `configure_azure_logging()` method

## Best Practices

1. Use default mode for normal operations
2. Use `--verbose` only when debugging issues
3. Check log files for persistent issues
4. Configure specific loggers as needed

## Examples

### Clean Sync Output
```bash
$ document-loader sync --kb-name azure-docs

Synchronizing knowledge base: azure-docs
Found 6 files in source
Change Detection Summary:
  New Files: 2
  Modified Files: 0
  Unchanged Files: 4
  Deleted Files: 0

Processing 2 files...
✓ Successfully synchronized 'azure-docs'
```

### Verbose Sync Output
```bash
$ document-loader --verbose sync --kb-name azure-docs

[Shows all the above plus:]
DEBUG: Azure authentication details
DEBUG: HTTP requests to Azure services
DEBUG: Storage operations
DEBUG: Token acquisition
...
```