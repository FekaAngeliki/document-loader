# Source Configuration Diagrams

## Source Type Hierarchy

```mermaid
graph TD
    FS[FileSource Interface]
    FS --> FSS[FileSystemSource]
    FS --> SPS[SharePointSource]
    FS --> CUSTOM[Custom Sources...]
    
    FSS --> FSC[File System Config]
    SPS --> SPC[SharePoint Config]
    
    FSC --> ROOT[root_path]
    FSC --> INC[include_patterns]
    FSC --> EXC[exclude_patterns]
    
    SPC --> URL[site_url]
    SPC --> PATH[path]
    SPC --> USER[username]
    SPC --> PASS[password]
    SPC --> REC[recursive]
    
    style FS fill:#f9f,stroke:#333,stroke-width:4px
    style FSS fill:#bbf,stroke:#333,stroke-width:2px
    style SPS fill:#bbf,stroke:#333,stroke-width:2px
    style FSC fill:#dfd,stroke:#333,stroke-width:2px
    style SPC fill:#ffd,stroke:#333,stroke-width:2px
```

## File System Source Pattern Matching

```mermaid
graph LR
    ROOT["/documents"]
    ROOT --> PDF["*.pdf"]
    ROOT --> MD["*.md"]
    ROOT --> SUB["**/*.docx"]
    
    PDF --> F1["report.pdf ✓"]
    PDF --> F2["draft.pdf ✓"]
    PDF --> F3["data.csv ✗"]
    
    MD --> F4["README.md ✓"]
    MD --> F5["notes.md ✓"]
    MD --> F6["script.py ✗"]
    
    SUB --> F7["docs/manual.docx ✓"]
    SUB --> F8["archive/old.docx ✓"]
    SUB --> F9["test.pdf ✗"]
    
    style ROOT fill:#ff9,stroke:#333,stroke-width:2px
    style F1 fill:#9f9,stroke:#333,stroke-width:1px
    style F2 fill:#9f9,stroke:#333,stroke-width:1px
    style F3 fill:#f99,stroke:#333,stroke-width:1px
    style F4 fill:#9f9,stroke:#333,stroke-width:1px
    style F5 fill:#9f9,stroke:#333,stroke-width:1px
    style F6 fill:#f99,stroke:#333,stroke-width:1px
    style F7 fill:#9f9,stroke:#333,stroke-width:1px
    style F8 fill:#9f9,stroke:#333,stroke-width:1px
    style F9 fill:#f99,stroke:#333,stroke-width:1px
```

## SharePoint Source Structure

```mermaid
graph TD
    SP[SharePoint Site]
    SP --> SITES[/sites]
    SITES --> TEAM[/TeamSite]
    TEAM --> SHARED[/Shared Documents]
    SHARED --> FOLDER1[/Projects]
    SHARED --> FOLDER2[/Policies]
    SHARED --> FILE1[report.pdf]
    SHARED --> FILE2[guidelines.docx]
    
    FOLDER1 --> PROJ1[/ProjectA]
    FOLDER1 --> PROJ2[/ProjectB]
    PROJ1 --> FILE3[specs.pdf]
    PROJ1 --> FILE4[design.docx]
    
    FOLDER2 --> FILE5[hr_policy.pdf]
    FOLDER2 --> FILE6[it_policy.pdf]
    
    style SP fill:#f9f,stroke:#333,stroke-width:4px
    style SHARED fill:#9ff,stroke:#333,stroke-width:2px
    style FOLDER1 fill:#ff9,stroke:#333,stroke-width:2px
    style FOLDER2 fill:#ff9,stroke:#333,stroke-width:2px
```

## Configuration Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Factory
    participant Source
    participant Files
    
    User->>CLI: create-kb with source config
    Note over User: {<br/>  "root_path": "/docs",<br/>  "include_patterns": ["*.pdf"]<br/>}
    
    CLI->>Factory: Create source(type, config)
    Factory->>Source: Initialize FileSystemSource(config)
    Source->>Source: Validate configuration
    Source-->>Factory: Source instance
    Factory-->>CLI: Ready to scan
    
    User->>CLI: sync --kb-name "docs"
    CLI->>Source: list_files()
    Source->>Files: Scan directory
    Files-->>Source: File list
    Source->>Source: Apply patterns
    Source-->>CLI: Filtered files
    
    loop For each file
        CLI->>Source: get_file_content(uri)
        Source->>Files: Read file
        Files-->>Source: File bytes
        Source-->>CLI: Content
    end
```

## Pattern Examples

### Include Pattern Matching

```
Pattern: *.pdf
Matches:
  ✓ document.pdf
  ✓ report.pdf
  ✗ document.docx
  ✗ folder/document.pdf

Pattern: **/*.pdf
Matches:
  ✓ document.pdf
  ✓ folder/document.pdf
  ✓ deep/folder/structure/file.pdf
  ✗ document.docx

Pattern: docs/*.md
Matches:
  ✓ docs/README.md
  ✓ docs/guide.md
  ✗ README.md
  ✗ docs/subfolder/guide.md

Pattern: **/README.*
Matches:
  ✓ README.md
  ✓ README.txt
  ✓ docs/README.md
  ✓ src/components/README.tsx
```

### Exclude Pattern Matching

```
Pattern: .*
Excludes:
  ✓ .gitignore
  ✓ .env
  ✗ README.md

Pattern: **/node_modules/**
Excludes:
  ✓ node_modules/package/file.js
  ✓ src/node_modules/lib/index.js
  ✗ src/index.js

Pattern: *.tmp
Excludes:
  ✓ document.tmp
  ✓ ~$document.docx
  ✗ document.pdf
```

## Configuration Matrix

| Source Type | Required Fields | Optional Fields | Default Values |
|-------------|----------------|-----------------|----------------|
| file_system | root_path | include_patterns<br>exclude_patterns | include: ["*"]<br>exclude: [] |
| sharepoint | site_url<br>path<br>username<br>password | recursive | recursive: true |

## Common Configuration Patterns

### 1. Document Processing
```json
{
  "root_path": "/documents",
  "include_patterns": [
    "*.pdf",
    "*.doc*",
    "*.xls*",
    "*.ppt*"
  ],
  "exclude_patterns": [
    "~$*",
    "*.tmp",
    "draft_*"
  ]
}
```

### 2. Code Documentation
```json
{
  "root_path": "/project",
  "include_patterns": [
    "**/*.md",
    "**/README*",
    "docs/**"
  ],
  "exclude_patterns": [
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**"
  ]
}
```

### 3. Media Library
```json
{
  "root_path": "/media",
  "include_patterns": [
    "**/*.jpg",
    "**/*.png",
    "**/*.mp4",
    "**/*.pdf"
  ],
  "exclude_patterns": [
    "**/.thumbnails/**",
    "**/temp/**"
  ]
}
```

### 4. SharePoint Team Site
```json
{
  "site_url": "https://company.sharepoint.com",
  "path": "/sites/Marketing/Shared Documents",
  "username": "service_account@company.com",
  "password": "${SP_PASSWORD}",
  "recursive": true
}
```