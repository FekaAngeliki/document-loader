# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) document management system that:
- Collects files from various sources (local filesystem, SharePoint)
- Processes them with hash calculation and UUID generation
- Uploads them to RAG systems
- Maintains records in a PostgreSQL database

## Core Architecture

The system follows a layered architecture with abstract interfaces:

1. **Application Core**: Batch Runner, File Processor, Change Detector, Configuration Manager
2. **Abstractions**: File Source interface, RAG System interface
3. **Implementations**: Source implementations (File System, SharePoint), RAG implementations
4. **Data Management**: Database Repository, Knowledge Base Manager

## Key Concepts

- **Knowledge Base**: Named collection of documents managed as a unit
- **Sync Run**: Execution of synchronization process for a knowledge base
- **File Record**: Individual file tracked with hash, UUID, and metadata
- **Change Detection**: Identifies new, modified, and deleted files

## Database Schema

Main tables:
- `knowledge_base`: Stores KB configurations with source and RAG settings
- `sync_run`: Tracks synchronization runs with statistics
- `file_record`: Records all files with original URI, RAG URI, hash, and status
- `source_type` & `rag_type`: Registry of available implementations

## Development Instructions

### Python Environment Setup
- All Python code must work under a UV-managed virtual environment
- Always activate the virtual environment: `source .venv/bin/activate`
- Install packages using: `uv add <package>`

### Implementation Guidelines
1. Use abstract interfaces for extensibility (File Source, RAG System)
2. Follow factory pattern for creating source and RAG instances
3. Use SHA-256 for file hashing, UUID v4 for unique filenames
4. Implement comprehensive error handling and logging
5. Use asyncio for concurrent file processing

### Database Operations
- Use PostgreSQL with connection pooling
- Implement proper transaction management
- Use JSONB for flexible configuration storage

### Extensibility Points
- Add new file sources by implementing the File Source interface
- Add new RAG systems by implementing the RAG System interface
- Register implementations in source_type and rag_type tables

### Testing Requirements
- Test change detection logic thoroughly
- Mock external systems (SharePoint, RAG) in tests
- Verify database transaction handling

### Test Script Management
- Create a folder named `test_scripts` to collect and keep all test scripts used to check and confirm application operations

Remember: No version control operations unless explicitly requested.