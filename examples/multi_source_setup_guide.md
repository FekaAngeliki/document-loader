# Multi-Source Knowledge Base Setup Guide

This guide shows you how to create a **single Knowledge Base that aggregates multiple sources into one RAG system** (single blob container).

## 🎯 Your Requirement

- **Multiple Sources**: Enterprise SharePoint + File System + OneDrive
- **Single RAG**: One Azure Blob Container 
- **Single KB**: Unified knowledge base with source tagging

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Knowledge Base: "company-docs"             │
│  ┌─────────────────────────────────────────────────────┤
│  │ Sources: [sharepoint_hr, sharepoint_finance,       │
│  │          network_archive, executive_onedrive]      │
│  └─────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │ SharePoint  │ │File System │ │  OneDrive   │      │
│  │ HR + Finance│ │   Archive   │ │  Executive  │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
│           │              │              │              │
│           └──────────────┼──────────────┘              │
│                          ▼                             │
│         ┌──────────────────────────────────┐           │
│         │    Azure Blob Container          │           │
│         │    "company-documents"           │           │
│         │                                  │           │
│         │ /sharepoint_hr/HR/*.pdf         │           │
│         │ /sharepoint_finance/Finance/*.xlsx │         │
│         │ /network_archive/Archive/*.txt   │           │
│         │ /executive_onedrive/Executive/*.docx │       │
│         └──────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Setup

### Step 1: Create Configuration File

```bash
# Generate template for your setup
document-loader multi-source create-template company-docs \
  --sharepoint-sites "https://yourorg.sharepoint.com/sites/hr" \
  --sharepoint-sites "https://yourorg.sharepoint.com/sites/finance" \
  --file-paths "/mnt/company/archive" \
  --onedrive-users "ceo@yourorg.com" \
  --container-name "company-documents"
```

This creates `company-docs_multi_source_config.json`

### Step 2: Update Configuration

Edit the generated file with your actual credentials and settings:

```json
{
  "name": "company-knowledge-base",
  "rag_config": {
    "azure_storage_container_name": "company-documents"
  },
  "sources": [
    {
      "source_id": "sharepoint_hr",
      "source_type": "enterprise_sharepoint",
      "source_config": {
        "tenant_id": "your-actual-tenant-id",
        "client_id": "your-actual-client-id",
        "client_secret": "your-actual-client-secret",
        "site_url": "https://yourorg.sharepoint.com/sites/hr"
      }
    }
  ]
}
```

### Step 3: Create Multi-Source Knowledge Base

```bash
# Validate configuration first
document-loader multi-source create-multi-kb \
  --config-file company-docs_multi_source_config.json \
  --validate-only

# Create the knowledge base
document-loader multi-source create-multi-kb \
  --config-file company-docs_multi_source_config.json
```

### Step 4: Sync All Sources

```bash
# Sync all sources in parallel (recommended)
document-loader multi-source sync-multi-kb \
  --config-file company-docs_multi_source_config.json \
  --sync-mode parallel

# Or sync specific sources only
document-loader multi-source sync-multi-kb \
  --config-file company-docs_multi_source_config.json \
  --sources "sharepoint_hr,network_archive"

# Or sync sequentially (slower but safer)
document-loader multi-source sync-multi-kb \
  --config-file company-docs_multi_source_config.json \
  --sync-mode sequential
```

### Step 5: Monitor Status

```bash
# Check sync status
document-loader multi-source status-multi-kb \
  --config-file company-docs_multi_source_config.json
```

## 📁 File Organization in Blob Container

Files are organized with source identification:

```
company-documents/
├── sharepoint_hr/HR/
│   ├── 12345678-abcd-1234-efgh-123456789012.pdf
│   └── 87654321-dcba-4321-hgfe-210987654321.docx
├── sharepoint_finance/Finance/  
│   ├── 11111111-2222-3333-4444-555555555555.xlsx
│   └── 66666666-7777-8888-9999-000000000000.pdf
├── network_archive/Archive/
│   ├── aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.txt
│   └── ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj.md
└── executive_onedrive/Executive/
    ├── 99999999-8888-7777-6666-555555555555.docx
    └── 44444444-3333-2222-1111-000000000000.pptx
```

## 🏷️ File Metadata and Tagging

Each file gets rich metadata for tracking:

```json
{
  "kb_name": "company-knowledge-base",
  "source_id": "sharepoint_hr",
  "source_type": "enterprise_sharepoint", 
  "department": "HR",
  "source_system": "sharepoint",
  "content_type": "hr_documents",
  "original_uri": "https://yourorg.sharepoint.com/sites/hr/Shared%20Documents/policy.pdf",
  "file_hash": "sha256:abc123...",
  "upload_timestamp": "2024-01-15T10:30:00Z"
}
```

## ⚡ Sync Strategies

### Parallel Sync (Default - Fastest)
```bash
--sync-mode parallel
```
- All sources sync simultaneously
- Fastest completion time
- Higher resource usage
- Best for normal operations

### Sequential Sync (Safest)
```bash
--sync-mode sequential  
```
- Sources sync one after another
- Safer for large datasets
- Lower resource usage
- Best for initial setup or large volumes

### Selective Sync (Targeted)
```bash
--sources "sharepoint_hr,executive_onedrive"
```
- Sync only specified sources
- Perfect for testing or urgent updates
- Maintains other sources unchanged

## 🔄 Scheduling and Automation

Each source can have independent schedules:

```json
{
  "source_id": "sharepoint_hr",
  "sync_schedule": "0 2 * * *",    // Daily at 2 AM
  "source_id": "network_archive", 
  "sync_schedule": "0 4 * * 0"     // Weekly on Sunday at 4 AM
}
```

Set up cron jobs:
```bash
# Daily sync of SharePoint sources
0 2 * * * /path/to/document-loader multi-source sync-multi-kb --config-file /path/to/config.json --sources "sharepoint_hr,sharepoint_finance"

# Weekly sync of file system archive  
0 4 * * 0 /path/to/document-loader multi-source sync-multi-kb --config-file /path/to/config.json --sources "network_archive"
```

## 🔍 Searching and Querying

Since all sources feed into one blob container, you get unified search:

```python
# Your RAG system can search across all sources
search_results = rag_system.search("employee handbook")

# Results include source metadata:
for result in search_results:
    print(f"Found in {result.metadata['source_id']}: {result.filename}")
    print(f"Department: {result.metadata['department']}")
    print(f"Source: {result.metadata['source_system']}")
```

## 🛡️ Security and Permissions

- Each source maintains its own authentication
- Files are tagged with source and department for access control
- Blob container can have unified security policies
- Source-specific metadata preserved for compliance

## ⚠️ Current Implementation Notes

The current implementation creates **individual KBs for each source** that share the same RAG container. This provides:

✅ **Backward compatibility** with existing architecture
✅ **Independent sync runs** per source  
✅ **Shared RAG storage** (your requirement)
✅ **Source isolation** for error handling
✅ **Easy source management** (enable/disable sources)

Future enhancement will provide native multi-source KB support with a single sync run across all sources.

## 🔧 Troubleshooting

### Configuration Issues
```bash
# Validate configuration
document-loader multi-source create-multi-kb --config-file config.json --validate-only
```

### Sync Issues
```bash
# Check individual source status
document-loader status company-knowledge-base_sharepoint_hr

# Dry run to see what would be synced
document-loader multi-source sync-multi-kb --config-file config.json --dry-run
```

### Blob Container Issues
- Ensure all sources use the same `azure_storage_container_name`
- Check Azure permissions for the service principal
- Verify container exists and is accessible

This setup gives you exactly what you requested: **multiple sources feeding into a single RAG system (blob container)** with proper source tagging and organization!