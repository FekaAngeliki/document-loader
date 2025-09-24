# Source Configuration Examples

This file contains practical, real-world examples of source configurations for common use cases.

## Table of Contents
1. [Basic Examples](#basic-examples)
2. [Advanced Patterns](#advanced-patterns)
3. [Industry-Specific Examples](#industry-specific-examples)
4. [Performance-Optimized Configs](#performance-optimized-configs)
5. [Security-Focused Configs](#security-focused-configs)

## Basic Examples

### 1. Simple Document Directory
```bash
document-loader create-kb \
  --name "company-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/home/user/Documents"
  }'
```

### 2. PDF-Only Directory
```bash
document-loader create-kb \
  --name "pdf-library" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/data/pdfs",
    "include_patterns": ["*.pdf"]
  }'
```

### 3. Basic SharePoint
```bash
document-loader create-kb \
  --name "team-sharepoint" \
  --source-type "sharepoint" \
  --source-config '{
    "site_url": "https://company.sharepoint.com",
    "path": "/sites/TeamSite/Shared Documents",
    "username": "user@company.com",
    "password": "password"
  }'
```

### 4. Include Only Specific Extensions
```bash
document-loader create-kb \
  --name "office-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/data/office",
    "include_extensions": [".pdf", ".docx", ".xlsx", ".pptx"]
  }'
```

### 5. Include Extensions with Patterns
```bash
document-loader create-kb \
  --name "filtered-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/data/documents",
    "include_patterns": ["2024/**", "reports/**"],
    "include_extensions": [".pdf", ".md"],
    "exclude_patterns": ["**/drafts/**"]
  }'
```

## Advanced Patterns

### 1. Multi-Format Documentation
```bash
document-loader create-kb \
  --name "technical-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/opt/documentation",
    "include_patterns": [
      "*.pdf",
      "*.md",
      "*.rst",
      "*.docx",
      "**/*.html"
    ],
    "exclude_patterns": [
      "drafts/**",
      "archive/**",
      "*.tmp",
      "~*",
      ".*"
    ]
  }'
```

### 2. Source Code Documentation
```bash
document-loader create-kb \
  --name "codebase-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/projects/myapp",
    "include_patterns": [
      "**/*.md",
      "**/README*",
      "docs/**/*",
      "**/LICENSE*",
      "**/*.rst"
    ],
    "exclude_patterns": [
      "**/node_modules/**",
      "**/.git/**",
      "**/venv/**",
      "**/__pycache__/**",
      "**/dist/**",
      "**/build/**",
      "**/*.pyc",
      "**/.env"
    ]
  }'
```

### 3. Nested SharePoint Folders
```bash
document-loader create-kb \
  --name "project-docs" \
  --source-type "sharepoint" \
  --source-config '{
    "site_url": "https://contoso.sharepoint.com",
    "path": "/sites/Engineering/Shared Documents/Projects/2024",
    "username": "eng_bot@contoso.com",
    "password": "${SHAREPOINT_BOT_PWD}",
    "recursive": true
  }'
```

## Industry-Specific Examples

### 1. Legal Document Management
```bash
document-loader create-kb \
  --name "legal-repository" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/mnt/legal/documents",
    "include_patterns": [
      "contracts/*.pdf",
      "agreements/*.pdf",
      "policies/*.docx",
      "templates/*.docx",
      "case_files/*/*.pdf"
    ],
    "exclude_patterns": [
      "confidential/**",
      "draft_*",
      "expired/**",
      "*.tmp",
      "~$*"
    ]
  }'
```

### 2. Medical Records System
```bash
document-loader create-kb \
  --name "medical-records" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/secure/medical/records",
    "include_patterns": [
      "patients/*/*.pdf",
      "reports/*/*.pdf",
      "lab_results/*/*.pdf",
      "imaging/*/*.dcm"
    ],
    "exclude_patterns": [
      "temp/**",
      "processing/**",
      "archived/**",
      "*.bak"
    ]
  }'
```

### 3. Academic Research Papers
```bash
document-loader create-kb \
  --name "research-papers" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/research/papers",
    "include_patterns": [
      "published/*.pdf",
      "preprints/*.pdf",
      "dissertations/*.pdf",
      "references/*.bib",
      "datasets/*.csv"
    ],
    "exclude_patterns": [
      "reviews/**",
      "rejected/**",
      "*.tmp",
      "~*"
    ]
  }'
```

## Performance-Optimized Configs

### 1. Large Directory with Specific Files
```bash
document-loader create-kb \
  --name "optimized-scan" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/massive/storage",
    "include_patterns": [
      "2024/*.pdf",
      "reports/Q4/*.xlsx",
      "summaries/*.md"
    ],
    "exclude_patterns": [
      "backup/**",
      "temp/**",
      "cache/**",
      "logs/**"
    ]
  }'
```

### 2. Extension-Based Filtering (More Efficient)
```bash
document-loader create-kb \
  --name "extension-filter" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/massive/storage",
    "include_extensions": [".pdf", ".docx", ".xlsx"],
    "exclude_patterns": [
      "backup/**",
      "temp/**",
      "cache/**"
    ]
  }'
```

### 3. Combined Extension and Pattern Filtering
```bash
document-loader create-kb \
  --name "combined-filter" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/data/documents",
    "include_patterns": ["2024/**", "current/**"],
    "include_extensions": [".pdf", ".md"],
    "exclude_extensions": [".tmp", ".draft"]
  }'
```

### 2. Shallow Directory Scan
```bash
document-loader create-kb \
  --name "quick-scan" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/data/current",
    "include_patterns": [
      "*.pdf",
      "*.docx"
    ],
    "exclude_patterns": [
      "**/*"
    ]
  }'
```

### 3. Time-Based Pattern
```bash
document-loader create-kb \
  --name "recent-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/documents/inbox",
    "include_patterns": [
      "2024-11-*.pdf",
      "2024-12-*.pdf",
      "weekly_report_*.docx"
    ],
    "exclude_patterns": [
      "2023-*",
      "archive/**"
    ]
  }'
```

## Security-Focused Configs

### 1. Restricted Access Pattern
```bash
document-loader create-kb \
  --name "public-docs-only" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/shared/documents",
    "include_patterns": [
      "public/*.pdf",
      "public/*.md",
      "releases/*.pdf"
    ],
    "exclude_patterns": [
      "private/**",
      "confidential/**",
      "internal/**",
      "*.key",
      "*.pem",
      "*.env"
    ]
  }'
```

### 2. SharePoint with Environment Variables
```bash
# Set environment variables first
export SP_SITE_URL="https://company.sharepoint.com"
export SP_USERNAME="service_account@company.com"
export SP_PASSWORD="secure_password_here"

# Create KB with secure config
document-loader create-kb \
  --name "secure-sharepoint" \
  --source-type "sharepoint" \
  --source-config "{
    \"site_url\": \"${SP_SITE_URL}\",
    \"path\": \"/sites/SecureTeam/Documents\",
    \"username\": \"${SP_USERNAME}\",
    \"password\": \"${SP_PASSWORD}\",
    \"recursive\": true
  }"
```

### 3. Audit Trail Configuration
```bash
document-loader create-kb \
  --name "audit-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/compliance/audit",
    "include_patterns": [
      "approved/*.pdf",
      "signed/*.pdf",
      "reports/*_final.pdf"
    ],
    "exclude_patterns": [
      "drafts/**",
      "pending/**",
      "rejected/**",
      "*.tmp",
      "*.unsigned"
    ]
  }'
```

## Complex Real-World Examples

### 1. Multi-Department Organization
```bash
document-loader create-kb \
  --name "org-wide-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/corporate/shared",
    "include_patterns": [
      "HR/policies/*.pdf",
      "HR/forms/*.docx",
      "Finance/reports/2024/*.xlsx",
      "Finance/budgets/approved/*.xlsx",
      "IT/documentation/*.md",
      "IT/procedures/*.pdf",
      "Marketing/campaigns/*/final/*.pdf",
      "Legal/contracts/signed/*.pdf"
    ],
    "exclude_patterns": [
      "**/drafts/**",
      "**/temp/**",
      "**/private/**",
      "**/*.tmp",
      "**/.git/**",
      "**/archive/**"
    ]
  }'
```

### 2. Multi-Site SharePoint
```bash
# For multiple SharePoint sites, create separate KBs
# Site 1: Engineering
document-loader create-kb \
  --name "engineering-sp" \
  --source-type "sharepoint" \
  --source-config '{
    "site_url": "https://company.sharepoint.com",
    "path": "/sites/Engineering/Shared Documents",
    "username": "eng_bot@company.com",
    "password": "${ENG_BOT_PWD}",
    "recursive": true
  }'

# Site 2: Marketing
document-loader create-kb \
  --name "marketing-sp" \
  --source-type "sharepoint" \
  --source-config '{
    "site_url": "https://company.sharepoint.com",
    "path": "/sites/Marketing/Campaigns",
    "username": "mkt_bot@company.com",
    "password": "${MKT_BOT_PWD}",
    "recursive": true
  }'
```

### 3. Development Environment
```bash
document-loader create-kb \
  --name "dev-docs" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/workspace",
    "include_patterns": [
      "**/README.md",
      "**/docs/**/*.md",
      "**/API.md",
      "**/CHANGELOG.md",
      "**/wiki/**/*.md",
      "**/*.rst",
      "specifications/*.pdf"
    ],
    "exclude_patterns": [
      "**/node_modules/**",
      "**/venv/**",
      "**/env/**",
      "**/.git/**",
      "**/dist/**",
      "**/build/**",
      "**/target/**",
      "**/__pycache__/**",
      "**/*.pyc",
      "**/.pytest_cache/**",
      "**/coverage/**"
    ]
  }'
```

## Testing and Debugging Configs

### 1. Test Configuration
```bash
# Test with a small subset first
document-loader scan \
  --path "/test/directory" \
  --source-type "file_system" \
  --source-config '{
    "include_patterns": ["*.pdf"],
    "exclude_patterns": []
  }' \
  --table
```

### 2. Debug Pattern Matching
```bash
# Use very specific patterns to debug
document-loader create-kb \
  --name "debug-patterns" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/test",
    "include_patterns": [
      "test.pdf",
      "docs/manual.pdf",
      "reports/2024/q4.pdf"
    ],
    "exclude_patterns": []
  }'
```

### 3. Progressive Configuration
```bash
# Start simple
document-loader create-kb \
  --name "test-1" \
  --source-type "file_system" \
  --source-config '{"root_path": "/test"}'

# Add include patterns
document-loader create-kb \
  --name "test-2" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/test",
    "include_patterns": ["*.pdf"]
  }'

# Add exclude patterns
document-loader create-kb \
  --name "test-3" \
  --source-type "file_system" \
  --source-config '{
    "root_path": "/test",
    "include_patterns": ["*.pdf"],
    "exclude_patterns": ["draft*", "temp/**"]
  }'
```