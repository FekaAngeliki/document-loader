# Source Configuration Guide

This document provides detailed information about source configurations in the Document Loader system. Sources define where documents are loaded from.

## Overview

Sources are pluggable components that implement the `FileSource` interface. Each source type has its own configuration schema that defines what parameters are needed to connect and retrieve files.

## Available Source Types

### 1. File System Source

The File System source reads files from local or mounted directories.

**Type**: `file_system`

**Class**: `src.implementations.file_system_source.FileSystemSource`

**Configuration Schema**:

```json
{
  "type": "object",
  "properties": {
    "root_path": {
      "type": "string",
      "description": "The base directory path to scan for files",
      "required": true
    },
    "include_patterns": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Glob patterns for files to include",
      "default": ["*"]
    },
    "exclude_patterns": {
      "type": "array", 
      "items": {"type": "string"},
      "description": "Glob patterns for files to exclude",
      "default": []
    },
    "include_extensions": {
      "type": "array",
      "items": {"type": "string"},
      "description": "File extensions to include (e.g., ['.pdf', '.docx']). If specified, only these extensions are included",
      "default": []
    },
    "exclude_extensions": {
      "type": "array",
      "items": {"type": "string"},
      "description": "File extensions to exclude (e.g., ['.tmp', '.log'])",
      "default": []
    }
  }
}
```

**Configuration Examples**:

```json
// Basic configuration - scan all files
{
  "root_path": "/data/documents"
}

// Scan only PDF and Word documents
{
  "root_path": "/data/documents",
  "include_patterns": ["*.pdf", "*.docx"]
}

// Complex configuration with exclusions
{
  "root_path": "/home/user/documents",
  "include_patterns": ["*.pdf", "*.md", "*.txt"],
  "exclude_patterns": ["*.tmp", "~*", ".*", "draft_*"]
}

// Using exclude_extensions for better performance
{
  "root_path": "/home/user/documents",
  "include_patterns": ["*"],
  "exclude_extensions": [".tmp", ".log", ".bak", ".swp", ".DS_Store"]
}

// Using include_extensions to only process specific file types
{
  "root_path": "/home/user/documents",
  "include_extensions": [".pdf", ".docx", ".xlsx"],
  "exclude_extensions": [".tmp", ".log"]
}

// Combining patterns and extensions
{
  "root_path": "/data/files",
  "include_patterns": ["*.pdf", "*.docx", "*.xlsx"],
  "exclude_patterns": ["temp/**", "archive/**"],
  "exclude_extensions": [".tmp", ".temp", ".cache", ".lock"]
}

// Include only specific extensions from specific directories
{
  "root_path": "/data/projects",
  "include_patterns": ["docs/**", "reports/**"],
  "include_extensions": [".pdf", ".md"],
  "exclude_patterns": ["**/drafts/**"]
}

// Recursive patterns
{
  "root_path": "/projects",
  "include_patterns": ["**/*.md", "**/*.pdf"],
  "exclude_patterns": ["**/node_modules/**", "**/.git/**"]
}
```

**Pattern Syntax**:
- `*` - matches any characters in a single path segment
- `**` - matches any number of path segments (recursive)
- `?` - matches a single character
- `[abc]` - matches any character in brackets
- `[!abc]` - matches any character not in brackets

### 2. SharePoint Source

The SharePoint source reads files from SharePoint Online document libraries.

**Type**: `sharepoint`

**Class**: `src.implementations.sharepoint_source.SharePointSource`

**Configuration Schema**:

```json
{
  "type": "object",
  "properties": {
    "site_url": {
      "type": "string",
      "description": "SharePoint site URL",
      "required": true
    },
    "path": {
      "type": "string",
      "description": "Path within SharePoint to scan",
      "required": true
    },
    "username": {
      "type": "string",
      "description": "SharePoint username/email",
      "required": true
    },
    "password": {
      "type": "string",
      "description": "SharePoint password",
      "required": true
    },
    "recursive": {
      "type": "boolean",
      "description": "Whether to scan subfolders",
      "default": true
    }
  }
}
```

**Configuration Examples**:

```json
// Basic SharePoint configuration
{
  "site_url": "https://company.sharepoint.com",
  "path": "/sites/TeamSite/Shared Documents",
  "username": "user@company.com",
  "password": "secure_password"
}

// Non-recursive scan (only top-level)
{
  "site_url": "https://contoso.sharepoint.com",
  "path": "/sites/HR/Policies",
  "username": "hr.user@contoso.com",
  "password": "${SHAREPOINT_PASSWORD}",
  "recursive": false
}

// Specific document library
{
  "site_url": "https://myorg.sharepoint.com",
  "path": "/sites/Engineering/Technical Docs",
  "username": "eng_service@myorg.com",
  "password": "${SP_SERVICE_ACCOUNT_PWD}",
  "recursive": true
}
```

## Configuration Best Practices

### 1. Security

- **Never hardcode passwords**: Use environment variables
  ```json
  {
    "password": "${SHAREPOINT_PASSWORD}"
  }
  ```

- **Use service accounts** for production SharePoint access
- **Restrict file access** using include/exclude patterns

### 2. Performance

- **Be specific with patterns**: Don't scan unnecessary files
  ```json
  {
    "include_patterns": ["*.pdf", "*.docx"],
    "exclude_patterns": ["archive/**", "temp/**"]
  }
  ```

- **Limit recursion depth** when possible
- **Exclude large binary files** if not needed

### 3. Path Handling

- **Use absolute paths** for file system sources
  ```json
  {
    "root_path": "/opt/documents"  // Good
    // "root_path": "./documents"   // Avoid
  }
  ```

- **Handle spaces** in SharePoint paths
  ```json
  {
    "path": "/sites/My Team/Shared Documents"  // Spaces are OK
  }
  ```

### 4. Extension Filtering

The File System source supports both pattern-based and extension-based filtering for optimal performance and flexibility.

**Filtering Order and Priority**:
1. **exclude_extensions** - Files with these extensions are excluded first
2. **include_extensions** - If specified, only files with these extensions are included
3. **exclude_patterns** - Files matching these patterns are excluded
4. **include_patterns** - Files must match at least one of these patterns

**Extension Filtering Behavior**:
- Extensions are case-insensitive (`.pdf` matches `.PDF`)
- Extensions can be specified with or without the dot (`.pdf` or `pdf`)
- Extension filtering is more performant than pattern matching

**Examples**:

```json
// Include only specific document types
{
  "root_path": "/data/documents",
  "include_extensions": [".pdf", ".docx", ".xlsx", ".pptx"],
  "exclude_extensions": [".tmp", ".log"]
}

// Process all files except certain extensions (DEFAULT behavior)
{
  "root_path": "/home/user/files",
  "exclude_extensions": [".tmp", ".cache", ".log", ".bak"]
  // Note: include_extensions is omitted, so all non-excluded extensions are included
}

// Combine extensions with patterns for precise control
{
  "root_path": "/projects",
  "include_patterns": ["docs/**", "reports/**"],
  "include_extensions": [".pdf", ".md"],
  "exclude_patterns": ["**/drafts/**"],
  "exclude_extensions": [".tmp"]
}

// Complex filtering with multiple rules
{
  "root_path": "/workspace",
  "include_patterns": ["**/*.pdf", "**/*.docx", "**/*.txt"],
  "include_extensions": [".pdf", ".docx", ".txt", ".md"],
  "exclude_patterns": ["temp/**", ".git/**"],
  "exclude_extensions": [".tmp", ".log", ".cache"]
}
```

**Important Notes**:
- If `include_extensions` is empty or omitted, all file extensions are allowed (except those in `exclude_extensions`)
- If `include_extensions` is specified, ONLY files with those extensions will be processed
- Extension filtering happens before pattern matching for better performance

### 5. Pattern Examples

**Common Include Patterns**:
```json
{
  "include_patterns": [
    "*.pdf",              // All PDF files
    "*.doc*",             // Word documents (doc, docx)
    "**/*.md",            // Markdown files in any subdirectory
    "reports/*.xlsx",     // Excel files in reports folder
    "**/README.*"         // README files with any extension
  ]
}
```

**Common Exclude Patterns**:
```json
{
  "exclude_patterns": [
    ".*",                 // Hidden files
    "~*",                 // Temporary files
    "*.tmp",              // Temp files
    "*.bak",              // Backup files
    "__pycache__/**",     // Python cache
    "node_modules/**",    // Node dependencies
    ".git/**",            // Git repository files
    "archive/**",         // Archived content
    "**/test/**"          // Test directories
  ]
}
```

**Common Exclude Extensions**:
```json
{
  "exclude_extensions": [
    ".tmp",               // Temporary files
    ".temp",              // Temporary files
    ".log",               // Log files
    ".bak",               // Backup files
    ".swp",               // Vim swap files
    ".swo",               // Vim swap files
    ".DS_Store",          // macOS system files
    ".pyc",               // Python compiled files
    ".pyo",               // Python optimized files
    ".o",                 // Object files
    ".so",                // Shared libraries
    ".dll",               // Dynamic libraries
    ".exe",               // Executables
    ".class",             // Java class files
    ".cache",             // Cache files
    ".lock",              // Lock files
    ".pid",               // Process ID files
    ".sock",              // Socket files
    ".zip",               // Archive files (if not needed)
    ".gz",                // Compressed files
    ".tar"                // Archive files
  ]
}
```

## Creating Custom Sources

To create a new source type:

1. **Implement the FileSource interface**:
```python
from src.abstractions.file_source import FileSource
from typing import AsyncIterator

class MyCustomSource(FileSource):
    def __init__(self, config: dict):
        self.config = config
    
    async def list_files(self) -> AsyncIterator[FileInfo]:
        # Implement file listing logic
        pass
    
    async def get_file_content(self, uri: str) -> bytes:
        # Implement file reading logic
        pass
```

2. **Define configuration schema**:
```json
{
  "type": "object",
  "properties": {
    "api_url": {"type": "string"},
    "api_key": {"type": "string"},
    "folder_id": {"type": "string"}
  }
}
```

3. **Register in database**:
```sql
INSERT INTO source_type (name, class_name, config_schema) 
VALUES (
  'my_custom_source',
  'my_module.MyCustomSource',
  '{"type": "object", "properties": {...}}'
);
```

## Troubleshooting Source Configurations

### Common Issues

1. **Invalid JSON**
   ```bash
   # Error: Invalid JSON in source config
   # Fix: Use proper JSON syntax
   --source-config '{"root_path": "/docs"}'  # Correct
   ```

2. **Path not found**
   ```json
   // Error: Directory does not exist
   // Fix: Verify path exists
   {
     "root_path": "/valid/path/to/documents"
   }
   ```

3. **Permission denied**
   - Ensure the user has read access to the directory
   - For SharePoint, verify credentials and permissions

4. **Pattern not matching**
   ```json
   // If no files are found, check patterns
   {
     "include_patterns": ["*.pdf"],  // Case sensitive!
     "exclude_patterns": []
   }
   ```

### Debug Tips

1. **Test patterns first**:
   ```bash
   # Use the scan command to test
   document-loader scan --path /test/path \
     --source-config '{"include_patterns": ["*.pdf"]}'
   ```

2. **Start simple**:
   - Begin with basic configuration
   - Add patterns incrementally
   - Test after each change

3. **Check logs**:
   - Enable debug logging for detailed information
   - Look for pattern matching details

## Source Configuration Reference

### FileSystem Source Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| root_path | string | Yes | - | Base directory to scan |
| include_patterns | array | No | ["*"] | Files to include (glob patterns) |
| exclude_patterns | array | No | [] | Files to exclude (glob patterns) |
| include_extensions | array | No | [] | File extensions to include (takes precedence) |
| exclude_extensions | array | No | [] | File extensions to exclude |

### Pattern vs. Extension Filtering

**include_patterns**: Uses glob pattern matching, very flexible
- Example: `"docs/*.pdf"` matches PDF files only in docs directory
- Can match complex patterns: `"2024-*.pdf"` matches files by date

**include_extensions**: Direct extension matching for allowed types
- Example: `[".pdf", ".docx"]` only allows PDF and Word files
- If specified, only files with these extensions are processed
- Takes precedence: file must match both include_extensions AND patterns
- Case-insensitive matching

**exclude_patterns**: Uses glob pattern matching, flexible exclusion
- Example: `"*.tmp"` matches any file ending with .tmp
- Can match partial names: `"temp_*"` matches temp_file.pdf

**exclude_extensions**: Direct extension matching, faster performance
- Example: `".tmp"` only matches files with .tmp extension
- More efficient for excluding specific file types
- Applied after include_extensions check
- Case-insensitive matching

### SharePoint Source Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| site_url | string | Yes | - | SharePoint site URL |
| path | string | Yes | - | Path within SharePoint |
| username | string | Yes | - | SharePoint username |
| password | string | Yes | - | SharePoint password |
| recursive | boolean | No | true | Scan subfolders |

## Examples by Use Case

### 1. Document Management System
```json
{
  "root_path": "/company/documents",
  "include_patterns": [
    "*.pdf",
    "*.docx",
    "*.xlsx",
    "*.pptx"
  ],
  "exclude_patterns": [
    "drafts/**",
    "archive/**",
    "*.tmp"
  ]
}
```

### 2. Code Documentation
```json
{
  "root_path": "/projects/myapp",
  "include_patterns": [
    "**/*.md",
    "**/README*",
    "docs/**/*"
  ],
  "exclude_patterns": [
    "**/node_modules/**",
    "**/.git/**",
    "**/build/**"
  ]
}
```

### 3. SharePoint Team Site
```json
{
  "site_url": "https://company.sharepoint.com",
  "path": "/sites/Marketing/Campaigns",
  "username": "marketing_bot@company.com",
  "password": "${MARKETING_BOT_PWD}",
  "recursive": true
}
```

### 4. Mixed Content Library
```json
{
  "root_path": "/shared/library",
  "include_patterns": [
    "**/*.pdf",
    "**/*.epub",
    "**/*.mobi",
    "metadata/*.json"
  ],
  "exclude_patterns": [
    "temp/**",
    "processing/**",
    "*.part"
  ]
}
```