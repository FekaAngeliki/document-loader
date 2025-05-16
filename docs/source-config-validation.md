# Source Configuration Validation Guide

This guide helps you validate and troubleshoot source configurations.

## Configuration Validation Checklist

### File System Source

- [ ] **root_path** exists and is accessible
- [ ] **root_path** is an absolute path
- [ ] User has read permissions on the directory
- [ ] **include_patterns** use valid glob syntax
- [ ] **exclude_patterns** don't conflict with includes
- [ ] Patterns are properly escaped in JSON

### SharePoint Source

- [ ] **site_url** is a valid HTTPS URL
- [ ] **path** starts with /sites/
- [ ] **username** is in email format
- [ ] **password** is not empty (use env vars)
- [ ] **recursive** is a boolean value

## Pattern Validation

### Valid Pattern Examples

✅ **Correct Patterns**:
```json
{
  "include_patterns": [
    "*.pdf",              // Simple extension
    "**/*.docx",          // Recursive search
    "reports/*.xlsx",     // Specific folder
    "2024-*.pdf",         // Date prefix
    "*_v[0-9].pdf"       // Version pattern
  ]
}
```

❌ **Invalid Patterns**:
```json
{
  "include_patterns": [
    "**.pdf",             // Should be **/*.pdf
    "*.{pdf,docx}",       // Brace expansion not supported
    "../*.pdf",           // Parent directory access
    "/absolute/*.pdf"     // Absolute paths in patterns
  ]
}
```

## Common Validation Errors

### 1. JSON Syntax Errors

**Error**: `Invalid JSON in source configuration`

**Common Causes**:
- Single quotes instead of double quotes
- Missing commas between properties
- Trailing commas
- Unescaped characters

**Example Fix**:
```bash
# Bad
--source-config '{'root_path': '/docs'}'

# Good
--source-config '{"root_path": "/docs"}'
```

### 2. Path Errors

**Error**: `Directory does not exist: /path/to/docs`

**Validation Steps**:
```bash
# Check if directory exists
ls -la /path/to/docs

# Check permissions
ls -la /path/to/

# Use absolute path
pwd  # Get current directory
--source-config '{"root_path": "/absolute/path/to/docs"}'
```

### 3. Permission Errors

**Error**: `Permission denied`

**Validation Steps**:
```bash
# Check read permissions
ls -la /path/to/docs

# Check user access
whoami
groups

# Test read access
find /path/to/docs -type f -name "*.pdf" | head -5
```

### 4. Pattern Matching Issues

**Error**: `No files found matching patterns`

**Validation Steps**:
```bash
# Test patterns with find
find /path/to/docs -name "*.pdf"

# Test recursive patterns
find /path/to/docs -path "*/docs/*.md"

# Use scan command to test
document-loader scan --path /path/to/docs \
  --source-config '{"include_patterns": ["*.pdf"]}'
```

## Validation Tools

### 1. Configuration Tester Script

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def validate_config(config_json):
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return False
    
    # Validate file_system config
    if 'root_path' in config:
        path = Path(config['root_path'])
        if not path.exists():
            print(f"Path does not exist: {path}")
            return False
        if not path.is_dir():
            print(f"Path is not a directory: {path}")
            return False
        if not path.is_absolute():
            print(f"Path is not absolute: {path}")
            return False
    
    # Validate patterns
    if 'include_patterns' in config:
        if not isinstance(config['include_patterns'], list):
            print("include_patterns must be a list")
            return False
    
    if 'exclude_patterns' in config:
        if not isinstance(config['exclude_patterns'], list):
            print("exclude_patterns must be a list")
            return False
    
    print("Configuration is valid!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        validate_config(sys.argv[1])
    else:
        print("Usage: validate_config.py '<json_config>'")
```

### 2. Pattern Testing Script

```bash
#!/bin/bash
# test_patterns.sh

ROOT_PATH=$1
PATTERN=$2

echo "Testing pattern: $PATTERN in $ROOT_PATH"
echo "------------------------"

# Using find
echo "Using find:"
find "$ROOT_PATH" -name "$PATTERN" | head -10

# Using document-loader scan
echo -e "\nUsing document-loader:"
document-loader scan --path "$ROOT_PATH" \
  --source-config "{\"include_patterns\": [\"$PATTERN\"]}" \
  --table | head -20
```

### 3. SharePoint Validation

```bash
#!/bin/bash
# validate_sharepoint.sh

SITE_URL=$1
USERNAME=$2
PASSWORD=$3

echo "Validating SharePoint connection..."

# Test with curl
curl -s -u "$USERNAME:$PASSWORD" \
  "$SITE_URL/_api/web/title" \
  -H "Accept: application/json"

# Check response
if [ $? -eq 0 ]; then
    echo "Connection successful!"
else
    echo "Connection failed!"
fi
```

## Pre-flight Validation

Before creating a knowledge base, validate:

### 1. Test with Scan Command
```bash
document-loader scan \
  --path "/your/path" \
  --source-type "file_system" \
  --source-config '{"include_patterns": ["*.pdf"]}' \
  --table
```

### 2. Check File Count
```bash
# Count matching files
find /your/path -name "*.pdf" | wc -l
```

### 3. Verify Permissions
```bash
# Test read access
find /your/path -name "*.pdf" -exec file {} \; | head -5
```

## Pattern Validation Examples

### Testing Include Patterns

```bash
# Test simple pattern
find /docs -name "*.pdf"

# Test recursive pattern
find /docs -path "**/*.pdf"

# Test complex pattern
find /docs -regex ".*2024.*\.pdf"
```

### Testing Exclude Patterns

```bash
# Find files that would be excluded
find /docs -name "*.tmp"
find /docs -path "*/archive/*"
find /docs -name ".*"
```

## SharePoint Validation

### 1. Validate Credentials
```bash
# Set environment variables
export SP_USER="user@company.com"
export SP_PASS="password"

# Test authentication
curl -u "$SP_USER:$SP_PASS" \
  "https://company.sharepoint.com/_api/web" \
  -H "Accept: application/json"
```

### 2. Validate Path
```bash
# List folders
curl -u "$SP_USER:$SP_PASS" \
  "https://company.sharepoint.com/_api/web/GetFolderByServerRelativeUrl('/sites/TeamSite/Shared%20Documents')/Folders" \
  -H "Accept: application/json"
```

## Debugging Configuration Issues

### 1. Enable Debug Logging
```bash
export DOCUMENT_LOADER_LOG_LEVEL=DEBUG
document-loader sync --kb-name "test"
```

### 2. Test Incrementally
1. Start with root path only
2. Add one include pattern
3. Add exclude patterns one by one
4. Test after each change

### 3. Common Fixes

**Pattern Not Matching**:
- Check case sensitivity
- Use `**` for recursive search
- Escape special characters

**Path Issues**:
- Use absolute paths
- Check for symbolic links
- Verify mount points

**Permission Issues**:
- Run as correct user
- Check group permissions
- Verify ACLs

## Validation Best Practices

1. **Always test patterns first** using scan command
2. **Start with simple configurations** and add complexity
3. **Use environment variables** for sensitive data
4. **Document your patterns** for team members
5. **Version control** your configurations
6. **Regular validation** of existing configs

## Automated Validation

### GitHub Action Example
```yaml
name: Validate KB Configs
on: [push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Validate JSON
        run: |
          jq '.' config/kb-configs/*.json
      
      - name: Test Patterns
        run: |
          ./scripts/validate_patterns.sh
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Validate all KB config files
for config in config/kb-configs/*.json; do
    if ! jq '.' "$config" > /dev/null 2>&1; then
        echo "Invalid JSON in $config"
        exit 1
    fi
done
```