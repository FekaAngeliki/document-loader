I'll help you create the specifications for a RAG (Retrieval-Augmented Generation) document management system with the features you've described. Let's break this down into the specs, high-level architecture, and database design.

# Document Management System for RAG - Specifications

## System Overview
A configurable document management system that collects files from various sources, processes them, uploads them to RAG systems, and maintains a record of all operations in a PostgreSQL database.

## Core Requirements

1. **Source File Collection**
   - Abstract file retrieval interface to support multiple file sources
   - Initial implementations for:
     - Local file system source
     - SharePoint source
   - File metadata collection (original URI, file size, creation date, modification date)

2. **File Processing**
   - Hash calculation for each file to detect changes
   - UUID generation for unique RAG system filenames
- Deleted file tracking: Implement a mechanism to log deleted files during synchronization runs, ensuring that the system can accurately reflect the current state of the document repository.
   - Change detection (new, modified, or deleted files)

3. **RAG System Integration**
   - Abstract interface for RAG systems
   - Support for uploading, updating, and deleting documents
   - Extensible design to add new RAG system implementations

4. **Knowledge Base Management**
   - Organize files into named knowledge bases
   - Support incremental updates to knowledge bases
   - Track run history for each knowledge base

5. **Database Management**
   - Store file metadata (original URI, hash, UUID, timestamps)
- Track deleted files in the `deleted_files` field of the `sync_run` table, allowing for historical analysis of file deletions and their impact on knowledge bases.
   - Track knowledge base configurations
   - Log run history and results

6. **Operational Features**
   - Scheduled or on-demand synchronization
   - Reporting on knowledge base status
   - Error handling and logging

# High-Level Architectural Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Application Core                          │
├─────────────┬─────────────────┬───────────────────┬────────────────┤
│ Batch Runner│ File Processor  │ Change Detector   │ Configuration  │
│             │                 │                   │ Manager        │
└─────────────┴─────────────────┴───────────────────┴────────────────┘
       │                │                │                  │
       ▼                ▼                ▼                  ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐
│ File Source │  │ File Hash   │  │ Database    │  │ Knowledge Base │
│ Abstraction │  │ Calculator  │  │ Repository  │  │ Manager        │
└─────────────┘  └─────────────┘  └─────────────┘  └────────────────┘
       │                                │                  │
       ▼                                ▼                  ▼
┌───────────────────────┐      ┌───────────────┐  ┌────────────────┐
│ Source Implementations│      │  PostgreSQL   │  │  RAG System    │
├───────────────────────┤      │  Database     │  │  Abstraction   │
│ - File System         │      └───────────────┘  └────────────────┘
│ - SharePoint          │                                  │
└───────────────────────┘                                  ▼
                                               ┌────────────────────┐
                                               │RAG Implementations │
                                               │                    │
                                               └────────────────────┘
```

## Core Components

### Application Core
- **Batch Runner**: Manages synchronization runs for knowledge bases
- **File Processor**: Handles file operations (read, hash, rename)
- **Change Detector**: Identifies new, modified, and deleted files
- **Configuration Manager**: Handles system configuration

### Abstractions
- **File Source Abstraction**: Interface for retrieving files from different sources
- **RAG System Abstraction**: Interface for RAG system operations

### Implementations
- **Source Implementations**: 
  - File System implementation
  - SharePoint implementation
- **RAG Implementations**: Extensible implementations for different RAG systems

### Data Management
- **Database Repository**: Handles all database operations
- **Knowledge Base Manager**: Manages knowledge base configurations

# Database Design

## Entity Relationship Diagram
```
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│   KnowledgeBase   │       │   SyncRun         │       │   FileRecord      │
├───────────────────┤       ├───────────────────┤       ├───────────────────┤
│ id (PK)           │       │ id (PK)           │       │ id (PK)           │
│ name              │1     *│ knowledge_base_id │1     *│ sync_run_id       │
│ source_type       ├───────┤ start_time        ├───────┤ original_uri      │
│ source_config     │       │ end_time          │       │ file_hash         │
│ rag_type          │       │ status            │       │ uuid_filename     │
│ rag_config        │       │ total_files       │       │ upload_time       │
│ created_at        │       │ new_files         │       │ file_size         │
│ updated_at        │       │ modified_files    │       │ status            │
└───────────────────┘       │ deleted_files     │       │ error_message     │
                            │ error_message     │       └───────────────────┘
                            └───────────────────┘

┌───────────────────┐       ┌───────────────────┐
│   SourceType      │       │   RagType         │
├───────────────────┤       ├───────────────────┤
│ id (PK)           │       │ id (PK)           │
│ name              │       │ name              │
│ class_name        │       │ class_name        │
│ config_schema     │       │ config_schema     │
└───────────────────┘       └───────────────────┘
```

## Table Definitions

### KnowledgeBase
```sql
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_config JSONB NOT NULL,
    rag_type VARCHAR(50) NOT NULL,
    rag_config JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### SyncRun
```sql
CREATE TABLE sync_run (
    id SERIAL PRIMARY KEY,
    knowledge_base_id INTEGER REFERENCES knowledge_base(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed'
    total_files INTEGER,
    new_files INTEGER,
    modified_files INTEGER,
    deleted_files INTEGER,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### FileRecord
```sql
CREATE TABLE file_record (
    id SERIAL PRIMARY KEY,
    sync_run_id INTEGER REFERENCES sync_run(id),
    original_uri TEXT NOT NULL, -- URI of the uploaded file in the RAG system
    rag_uri TEXT NOT NULL, -- Complete URI of the file in the RAG system
    file_hash VARCHAR(64) NOT NULL,
    uuid_filename VARCHAR(40) NOT NULL,
    upload_time TIMESTAMP NOT NULL,
    file_size BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'new', 'modified', 'unchanged', 'deleted', 'error'
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### SourceType
```sql
CREATE TABLE source_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    class_name VARCHAR(100) NOT NULL,
    config_schema JSONB NOT NULL
);
```

### RagType
```sql
CREATE TABLE rag_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    class_name VARCHAR(100) NOT NULL,
    config_schema JSONB NOT NULL
);
```

### Additional Indexes
```sql
CREATE INDEX idx_file_record_original_uri ON file_record(original_uri);
CREATE INDEX idx_file_record_file_hash ON file_record(file_hash);
CREATE INDEX idx_file_record_sync_run_id ON file_record(sync_run_id);
CREATE INDEX idx_sync_run_knowledge_base_id ON sync_run(knowledge_base_id);
```

## Implementation Recommendations

1. **Technology Stack**:
   - Backend: Python with asyncio for concurrent processing
   - Database: PostgreSQL with appropriate connection pooling
   - Configuration: YAML or JSON for knowledge base and system configuration

2. **File Processing**:
   - Use SHA-256 for file hashing
   - Use UUID v4 for generating unique filenames
   - Implement chunk processing for large files

3. **Extensibility**:
   - Use a plugin architecture for source and RAG implementations
   - Implement a factory pattern for creating source and RAG instances

4. **Operational Considerations**:
- Implement a notification system for deleted files to alert users of changes in the document repository.
   - Implement transaction management for database operations
   - Add comprehensive logging
   - Include monitoring endpoints for system health
   - Develop CLI and/or API interfaces for operations

This design provides a robust, extensible system for managing document synchronization between various sources and RAG systems with complete tracking and auditability.