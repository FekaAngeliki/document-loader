# Knowledge Base Configuration Diagram

```mermaid
graph TB
    KB[Knowledge Base]
    KB --> NAME[Name: Unique Identifier]
    KB --> SOURCE[Source Configuration]
    KB --> RAG[RAG Configuration]
    
    SOURCE --> STYPE[Source Type]
    SOURCE --> SCONFIG[Source Config JSON]
    
    STYPE --> FS[file_system]
    STYPE --> SP[sharepoint]
    
    FS --> FSCONFIG["{<br/>root_path: '/path',<br/>include_patterns: ['*.pdf'],<br/>exclude_patterns: ['*.tmp']<br/>}"]
    
    SP --> SPCONFIG["{<br/>site_url: 'https://...',<br/>path: '/sites/...',<br/>username: 'user',<br/>password: 'pass',<br/>recursive: true<br/>}"]
    
    RAG --> RTYPE[RAG Type]
    RAG --> RCONFIG[RAG Config JSON]
    
    RTYPE --> MOCK[mock]
    RTYPE --> CUSTOM[custom_rag]
    
    MOCK --> MOCKCONFIG["{}"]
    CUSTOM --> CUSTOMCONFIG["{<br/>api_key: '...',<br/>endpoint: '...'<br/>}"]
    
    style KB fill:#f9f,stroke:#333,stroke-width:4px
    style NAME fill:#9f9,stroke:#333,stroke-width:2px
    style SOURCE fill:#9ff,stroke:#333,stroke-width:2px
    style RAG fill:#ff9,stroke:#333,stroke-width:2px
```

## Configuration Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant DB
    participant Factory
    participant Source
    participant RAG
    
    User->>CLI: create-kb command
    Note over User: Provides name,<br/>source type & config,<br/>rag type & config
    
    CLI->>CLI: Parse JSON configs
    CLI->>DB: Create KnowledgeBase record
    DB-->>CLI: Returns KB ID
    
    CLI->>Factory: Create source instance
    Factory->>Source: Initialize with config
    Source-->>Factory: Source instance
    Factory-->>CLI: Source ready
    
    CLI->>Factory: Create RAG instance
    Factory->>RAG: Initialize with config
    RAG-->>Factory: RAG instance
    Factory-->>CLI: RAG ready
    
    CLI-->>User: Knowledge Base created
```

## Configuration Examples

### File System Configuration

```json
{
  "root_path": "/data/documents",
  "include_patterns": [
    "*.pdf",
    "*.docx",
    "*.md",
    "*.txt"
  ],
  "exclude_patterns": [
    "*.tmp",
    "~*",
    ".*",
    "__pycache__/**",
    ".git/**"
  ]
}
```

### SharePoint Configuration

```json
{
  "site_url": "https://company.sharepoint.com",
  "path": "/sites/ProjectX/Shared Documents",
  "username": "user@company.com",
  "password": "${SHAREPOINT_PWD}",
  "recursive": true
}
```

### Mock RAG Configuration

```json
{}
```

### Future RAG Configuration Examples

```json
// OpenAI RAG
{
  "api_key": "${OPENAI_API_KEY}",
  "model": "gpt-4",
  "chunk_size": 1000,
  "overlap": 200
}

// Custom RAG API
{
  "endpoint": "https://api.company.com/rag",
  "api_key": "${CUSTOM_API_KEY}",
  "timeout": 30,
  "batch_size": 10
}
```