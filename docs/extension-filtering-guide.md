# Extension Filtering Guide

This guide explains how to use the extension filtering features in the Document Loader system.

## Overview

The Document Loader provides two extension-based filtering mechanisms:
- `include_extensions`: Whitelist of file extensions to include
- `exclude_extensions`: Blacklist of file extensions to exclude

These filters work alongside pattern-based filtering for precise file selection.

## How Extension Filtering Works

### Processing Order

1. **Exclude Extensions Check**: Files with excluded extensions are rejected first
2. **Include Extensions Check**: If specified, only files with included extensions proceed
3. **Pattern Matching**: Files that pass extension filtering are then checked against patterns

### Behavior Rules

1. **Default Behavior**: If no `include_extensions` are specified, all extensions are allowed (except those explicitly excluded)
2. **Precedence**: Extension filtering occurs before pattern matching
3. **Case Insensitive**: Extension matching is case-insensitive (`.pdf` matches `.PDF`, `.Pdf`, etc.)
4. **Dot Normalization**: Extensions are normalized to include a dot (`.pdf` and `pdf` both work)

## Examples

### Basic Extension Filtering

```json
{
  "root_path": "/documents",
  "include_extensions": [".pdf", ".docx", ".xlsx"]
}
```
Only PDF, Word, and Excel files will be processed.

### Exclude Specific Extensions

```json
{
  "root_path": "/documents",
  "exclude_extensions": [".tmp", ".bak", ".log"]
}
```
All files except temporary, backup, and log files will be processed.

### Combining Include and Exclude

```json
{
  "root_path": "/documents",
  "include_extensions": [".pdf", ".docx", ".xlsx", ".txt"],
  "exclude_extensions": [".tmp", ".draft"]
}
```
Only PDF, Word, Excel, and text files are included, but temporary and draft files are excluded even if they have allowed extensions.

### Extension Filtering with Patterns

```json
{
  "root_path": "/projects",
  "include_patterns": ["docs/**", "reports/**"],
  "include_extensions": [".pdf", ".md"],
  "exclude_patterns": ["**/archive/**"]
}
```
Only PDF and Markdown files from the docs and reports directories are included, excluding anything in archive directories.

## Common Use Cases

### 1. Document Management System
```json
{
  "root_path": "/company/files",
  "include_extensions": [".pdf", ".docx", ".xlsx", ".pptx"],
  "exclude_extensions": [".tmp", ".lock"]
}
```

### 2. Technical Documentation
```json
{
  "root_path": "/code/docs",
  "include_extensions": [".md", ".rst", ".txt"],
  "exclude_patterns": ["**/node_modules/**", "**/.git/**"]
}
```

### 3. Media Library
```json
{
  "root_path": "/media",
  "include_extensions": [".jpg", ".jpeg", ".png", ".pdf"],
  "exclude_extensions": [".thumb", ".tmp"]
}
```

### 4. Mixed Content Repository
```json
{
  "root_path": "/repository",
  "include_patterns": ["public/**", "shared/**"],
  "include_extensions": [".pdf", ".docx", ".md"],
  "exclude_extensions": [".draft", ".tmp", ".bak"]
}
```

## Performance Considerations

Extension filtering is more efficient than pattern matching because:
1. Direct string comparison is faster than glob pattern matching
2. Extensions are checked early in the filtering process
3. Reduces the number of files that need pattern matching

## Best Practices

1. **Use include_extensions for allowlisting**: When you know exactly which file types you want
2. **Use exclude_extensions for blocklisting**: When you want most files but need to exclude specific types
3. **Combine with patterns for precise control**: Use patterns for directory-based filtering
4. **Consider performance**: Extension filtering is faster than pattern matching for large directories
5. **Be explicit**: It's better to be explicit about what you want than rely on defaults

## Troubleshooting

### Common Issues

1. **No files found**:
   - Check if `include_extensions` is too restrictive
   - Verify extension spelling (`.docx` not `.doc`)
   - Check case sensitivity isn't an issue

2. **Wrong files included**:
   - Add more specific `exclude_extensions`
   - Check if patterns are too broad

3. **Extension not recognized**:
   - Extensions are normalized with dots (use `.pdf` or `pdf`)
   - Check for typos in extension names

### Debug Tips

Test your configuration with the scan command:
```bash
document-loader scan --path /test/path \
  --source-config '{"include_extensions": [".pdf", ".docx"]}'
```

Start with simple configurations and add complexity gradually:
1. First, test with only `include_extensions`
2. Add `exclude_extensions` if needed
3. Finally, add pattern matching

## Extension Reference

### Common Document Extensions
- `.pdf` - Portable Document Format
- `.docx` - Microsoft Word
- `.xlsx` - Microsoft Excel
- `.pptx` - Microsoft PowerPoint
- `.odt` - OpenDocument Text
- `.ods` - OpenDocument Spreadsheet

### Common Text Extensions
- `.txt` - Plain text
- `.md` - Markdown
- `.rst` - reStructuredText
- `.rtf` - Rich Text Format

### Common Archive Extensions (often excluded)
- `.zip` - ZIP archive
- `.tar` - TAR archive
- `.gz` - Gzip compressed
- `.rar` - RAR archive

### Common Temporary Extensions (often excluded)
- `.tmp` - Temporary file
- `.temp` - Temporary file
- `.bak` - Backup file
- `.swp` - Swap file
- `.lock` - Lock file
- `.~$*` - Microsoft Office temp files