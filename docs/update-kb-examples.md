# Update Knowledge Base Examples

This document provides practical examples of using the `update-kb` command to modify knowledge base configurations.

## Basic Updates

### 1. Update Source Path

```bash
# Change the root path for a file system source
document-loader update-kb --name "my-docs" \
  --source-config '{"root_path": "/new/documents/path"}'
```

### 2. Update File Patterns

```bash
# Change which files to include
document-loader update-kb --name "my-docs" \
  --source-config '{
    "root_path": "/documents",
    "include_patterns": ["*.pdf", "*.docx", "*.xlsx"],
    "exclude_patterns": ["draft_*", "temp_*"]
  }'
```

### 3. Update SharePoint Credentials

```bash
# Update SharePoint password (use environment variable)
document-loader update-kb --name "sharepoint-docs" \
  --source-config '{
    "site_url": "https://company.sharepoint.com",
    "path": "/sites/TeamSite/Documents",
    "username": "service@company.com",
    "password": "${NEW_SP_PASSWORD}"
  }'
```

## Type Changes

### 1. Switch from File System to SharePoint

```bash
document-loader update-kb --name "docs" \
  --source-type "sharepoint" \
  --source-config '{
    "site_url": "https://company.sharepoint.com",
    "path": "/sites/IT/Documentation",
    "username": "it_bot@company.com",
    "password": "${IT_BOT_PWD}",
    "recursive": true
  }'
```

### 2. Change RAG System

```bash
# Switch from mock to a real RAG system
document-loader update-kb --name "docs" \
  --rag-type "openai" \
  --rag-config '{
    "api_key": "${OPENAI_API_KEY}",
    "model": "gpt-4",
    "chunk_size": 1000,
    "overlap": 200
  }'
```

## Complex Updates

### 1. Complete Configuration Overhaul

```bash
document-loader update-kb --name "legacy-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/archive/2024",
    "include_patterns": ["**/*.pdf", "**/*.md"],
    "exclude_patterns": ["**/drafts/**", "**/temp/**"]
  }' \
  --rag-type "custom-rag" \
  --rag-config '{
    "endpoint": "https://rag.company.com/api",
    "api_key": "${CUSTOM_RAG_KEY}",
    "timeout": 30
  }'
```

### 2. Partial Updates with Environment Variables

```bash
# Set environment variables first
export SP_NEW_URL="https://newsite.sharepoint.com"
export SP_NEW_PATH="/sites/NewTeam/Documents"
export SP_NEW_USER="newbot@company.com"
export SP_NEW_PASS="secure_password"

# Update with environment variables
document-loader update-kb --name "team-docs" \
  --source-config "{
    \"site_url\": \"${SP_NEW_URL}\",
    \"path\": \"${SP_NEW_PATH}\",
    \"username\": \"${SP_NEW_USER}\",
    \"password\": \"${SP_NEW_PASS}\",
    \"recursive\": true
  }"
```

## Update Workflow Examples

### 1. Incremental Pattern Updates

```bash
# Step 1: View current configuration
document-loader info my-docs

# Step 2: Add new file pattern
document-loader update-kb --name "my-docs" \
  --source-config '{
    "root_path": "/docs",
    "include_patterns": ["*.pdf", "*.docx", "*.txt"]
  }'

# Step 3: Verify change
document-loader info my-docs

# Step 4: Test with sync
document-loader sync --kb-name "my-docs"
```

### 2. Safe RAG System Migration

```bash
# Step 1: Create a test KB with new RAG config
document-loader create-kb --name "test-rag" \
  --source-type "file_system" \
  --source-config '{"root_path": "/test/docs"}' \
  --rag-type "new-rag" \
  --rag-config '{"api_key": "test-key"}'

# Step 2: Test the configuration
document-loader sync --kb-name "test-rag"

# Step 3: If successful, update production KB
document-loader update-kb --name "prod-docs" \
  --rag-type "new-rag" \
  --rag-config '{"api_key": "${PROD_RAG_KEY}"}'
```

## Validation Examples

### 1. Invalid JSON Error

```bash
# This will fail - invalid JSON
document-loader update-kb --name "docs" \
  --source-config '{"root_path": /bad/json}'

# Error: Error parsing source config JSON: ...
```

### 2. Invalid Type Error

```bash
# This will fail - invalid source type
document-loader update-kb --name "docs" \
  --source-type "invalid-type"

# Error: Invalid source type: 'invalid-type'
# Valid source types: file_system, sharepoint
```

### 3. Confirmation Prompt

```bash
document-loader update-kb --name "important-docs" \
  --source-config '{"root_path": "/critical/path"}'

# Current Configuration
# Name: important-docs
# Source Type: file_system
# RAG Type: mock
#
# Proposed Changes:
#   Source Config: Updated
#   {
#     "root_path": "/critical/path"
#   }
#
# Do you want to apply these changes? [y/N]:
```

## Best Practices

### 1. Always Backup Configuration

```bash
# Save current config before updating
document-loader info my-kb > my-kb-backup.json

# Update configuration
document-loader update-kb --name "my-kb" \
  --source-config '{"root_path": "/new/path"}'
```

### 2. Test Changes on Non-Production First

```bash
# Create a test KB
document-loader create-kb --name "test-config" \
  --source-type "file_system" \
  --source-config '{"root_path": "/test"}' \
  --rag-type "mock"

# Test configuration changes
document-loader update-kb --name "test-config" \
  --source-config '{"root_path": "/new/test/path"}'

# Verify it works
document-loader sync --kb-name "test-config"

# Apply to production
document-loader update-kb --name "production" \
  --source-config '{"root_path": "/new/prod/path"}'
```

### 3. Use Environment Variables for Secrets

```bash
# Bad - hardcoded password
document-loader update-kb --name "secure-kb" \
  --source-config '{"password": "actual_password"}'

# Good - environment variable
export SECURE_PASSWORD="actual_password"
document-loader update-kb --name "secure-kb" \
  --source-config '{"password": "${SECURE_PASSWORD}"}'
```

## Rollback Strategy

If an update causes issues:

1. Keep a backup of the original configuration
2. Use the update command to revert:

```bash
# Revert to original configuration
document-loader update-kb --name "my-kb" \
  --source-config '{"root_path": "/original/path", "include_patterns": ["*.pdf"]}'
```

3. Or restore from backup:

```bash
# If you saved the configuration
document-loader update-kb --name "my-kb" \
  --source-config "$(cat my-kb-backup.json | jq .source_config)"
```

## Automation Examples

### 1. Bulk Updates with Script

```bash
#!/bin/bash
# update_all_kbs.sh

# Update all KBs to use new RAG endpoint
for kb in "kb1" "kb2" "kb3"; do
    echo "Updating $kb..."
    document-loader update-kb --name "$kb" \
      --rag-config '{"endpoint": "https://new-rag.company.com"}'
done
```

### 2. Configuration Management

```yaml
# kb_configs.yaml
knowledge_bases:
  - name: docs-prod
    source_config:
      root_path: /prod/documents
      include_patterns: ["*.pdf", "*.docx"]
    rag_config:
      api_key: ${PROD_API_KEY}
  
  - name: docs-staging
    source_config:
      root_path: /staging/documents
      include_patterns: ["*.pdf"]
    rag_config:
      api_key: ${STAGING_API_KEY}

# Script to apply configurations
#!/bin/bash
yq eval '.knowledge_bases[] | 
  "document-loader update-kb --name \(.name) " +
  "--source-config '" + (.source_config | to_json) + "' " +
  "--rag-config '" + (.rag_config | to_json) + "'"' kb_configs.yaml | bash
```