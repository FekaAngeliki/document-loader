# SharePoint Discovery Guide

This guide explains how to use the SharePoint discovery functionality to easily configure SharePoint sources for your RAG system without needing to know site IDs, list IDs, or other technical details.

## Overview

The SharePoint discovery tools allow you to:

1. **Discover site information** from just a SharePoint URL
2. **Browse available content** (libraries, lists, pages) 
3. **Generate configurations** automatically
4. **Create knowledge bases** with minimal manual setup

## Prerequisites

### Required Packages

The SharePoint discovery functionality requires the `Office365-REST-Python-Client` package:

```bash
# Install the required package
uv add Office365-REST-Python-Client

# Or with pip:
pip install Office365-REST-Python-Client
```

### Authentication

You'll need one of these authentication methods:

#### Option 1: Service Principal (Recommended for production)

```bash
# Set environment variables
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id" 
export AZURE_CLIENT_SECRET="your-client-secret"
```

#### Option 2: User Credentials (For testing/development)

You can provide username and password directly in commands.

## Basic Usage

### Step 1: Discover SharePoint Site

Use the `discover-sharepoint` command to analyze a SharePoint site:

```bash
# Using service principal authentication (from environment variables)
document-loader discover-sharepoint "https://company.sharepoint.com/sites/marketing"

# Using explicit service principal credentials
document-loader discover-sharepoint \
  "https://company.sharepoint.com/sites/marketing" \
  --tenant-id "your-tenant-id" \
  --client-id "your-client-id" \
  --client-secret "your-client-secret"

# Using username/password
document-loader discover-sharepoint \
  "https://company.sharepoint.com/sites/marketing" \
  --username "user@company.com" \
  --password "your-password"

# Save discovery results to file
document-loader discover-sharepoint \
  "https://company.sharepoint.com/sites/marketing" \
  --output "marketing-site-discovery.json"

# Get detailed information
document-loader discover-sharepoint \
  "https://company.sharepoint.com/sites/marketing" \
  --verbose
```

### Step 2: Generate Configuration

Use the `generate-sharepoint-config` command to create a knowledge base configuration:

```bash
# Generate config for all document libraries
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/marketing" \
  --kb-name "marketing-docs" \
  --output "marketing-config.json"

# Generate config for specific libraries only
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/marketing" \
  --libraries "Documents,Presentations,Templates" \
  --kb-name "marketing-docs" \
  --rag-type "azure_blob" \
  --output "marketing-config.json"

# Include lists and pages too
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/marketing" \
  --libraries "Documents,Presentations" \
  --lists "Marketing Calendar,Contact List" \
  --include-pages \
  --kb-name "marketing-everything" \
  --output "marketing-full-config.json"
```

### Step 3: Create Knowledge Base

Once you have a configuration file, create the knowledge base:

```bash
# Create knowledge base from generated config
document-loader create-kb \
  --name "marketing-docs" \
  --source-type "sharepoint" \
  --source-config @marketing-config.json \
  --rag-type "mock"

# Or use the exact command shown in the config generation output
```

### Step 4: Initialize and Sync

```bash
# Initialize Azure resources (if using azure_blob RAG)
document-loader init-azure --kb-name "marketing-docs"

# Sync the documents
document-loader sync --kb-name "marketing-docs"
```

## Command Reference

### discover-sharepoint

Analyzes a SharePoint site and discovers available content.

**Syntax:**
```bash
document-loader discover-sharepoint <site_url> [options]
```

**Options:**
- `--tenant-id`: Azure tenant ID (or use `AZURE_TENANT_ID` env var)
- `--client-id`: Azure client ID (or use `AZURE_CLIENT_ID` env var)  
- `--client-secret`: Azure client secret (or use `AZURE_CLIENT_SECRET` env var)
- `--username`: SharePoint username
- `--password`: SharePoint password
- `--output`: Save discovery results to JSON file
- `--verbose`: Show detailed information

**Examples:**
```bash
# Basic discovery
document-loader discover-sharepoint "https://company.sharepoint.com/sites/hr"

# With detailed output
document-loader discover-sharepoint "https://company.sharepoint.com/sites/hr" --verbose

# Save results
document-loader discover-sharepoint "https://company.sharepoint.com/sites/hr" --output "hr-discovery.json"
```

### generate-sharepoint-config

Generates a complete knowledge base configuration from SharePoint site discovery.

**Syntax:**
```bash
document-loader generate-sharepoint-config <site_url> [options]
```

**Options:**
- Authentication options (same as `discover-sharepoint`)
- `--libraries`: Comma-separated list of library names to include (default: all)
- `--lists`: Comma-separated list of list names to include (default: none)
- `--include-pages`: Include site pages
- `--output`: Output file for generated configuration
- `--kb-name`: Knowledge base name for the configuration
- `--rag-type`: RAG system type (default: mock)

**Examples:**
```bash
# All libraries with mock RAG
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/hr" \
  --kb-name "hr-documents" \
  --output "hr-config.json"

# Specific libraries with Azure Blob RAG
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/hr" \
  --libraries "Documents,Policies,Forms" \
  --kb-name "hr-documents" \
  --rag-type "azure_blob" \
  --output "hr-config.json"

# Everything including lists and pages
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/hr" \
  --libraries "Documents,Policies" \
  --lists "Employee Directory,Training Calendar" \
  --include-pages \
  --kb-name "hr-everything" \
  --output "hr-full-config.json"
```

## Configuration Examples

### Generated Configuration Structure

A generated configuration will look like this:

```json
{
  "name": "marketing-docs",
  "description": "SharePoint knowledge base for Marketing Team - Include all document libraries",
  "source_type": "sharepoint",
  "source_config": {
    "site_url": "https://company.sharepoint.com/sites/marketing",
    "site_id": "12345678-1234-1234-1234-123456789012",
    "site_name": "Marketing Team",
    "tenant_name": "company",
    "recursive": true,
    "tenant_id": "your-tenant-id",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "sources": [
      {
        "type": "library",
        "id": "lib-001",
        "title": "Documents",
        "url": "/sites/marketing/Documents",
        "item_count": 150
      },
      {
        "type": "library",
        "id": "lib-002", 
        "title": "Presentations",
        "url": "/sites/marketing/Presentations",
        "item_count": 45
      }
    ]
  },
  "rag_type": "mock",
  "rag_config": {}
}
```

### Common Use Cases

#### 1. Document-Only Knowledge Base

```bash
# Discover and generate config for documents only
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/docs" \
  --kb-name "company-documents" \
  --rag-type "azure_blob" \
  --output "docs-config.json"
```

#### 2. Department-Specific Content

```bash
# HR department with specific libraries
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/hr" \
  --libraries "Policies,Forms,Handbooks" \
  --kb-name "hr-knowledge" \
  --output "hr-config.json"
```

#### 3. Complete Site Content

```bash
# Everything from a marketing site
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/marketing" \
  --lists "Campaign Calendar,Lead Tracking" \
  --include-pages \
  --kb-name "marketing-complete" \
  --rag-type "file_system_storage" \
  --output "marketing-complete-config.json"
```

## Troubleshooting

### Authentication Issues

**Service Principal Authentication:**
```bash
# Verify your service principal has access
# The app registration needs:
# - Sites.Read.All or Sites.ReadWrite.All permission
# - Admin consent granted
```

**User Authentication:**
```bash
# Ensure the user has access to the SharePoint site
# Test access by visiting the site in a browser first
```

### Common Errors

**"Office365-REST-Python-Client not available"**
```bash
# Install the required package
uv add Office365-REST-Python-Client
```

**"Authentication required"**
```bash
# Provide authentication using one of these methods:

# Environment variables
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# Or command line options
--tenant-id "your-tenant-id" --client-id "your-client-id" --client-secret "your-secret"

# Or user credentials
--username "user@company.com" --password "your-password"
```

**"Could not extract tenant name from URL"**
```bash
# Ensure the URL is a valid SharePoint URL:
# ✓ https://company.sharepoint.com/sites/sitename
# ✓ https://company.sharepoint.com/teams/teamname
# ✗ https://company.onmicrosoft.com/...
```

### Discovery Results

**Empty libraries/lists:**
- The site may not have any content
- Your authentication may not have sufficient permissions
- Use `--verbose` to see detailed information

**Missing expected libraries:**
- Libraries may be hidden from the API
- Check if you have read permissions to the libraries
- Some system libraries are filtered out automatically

## Integration with Existing Workflows

### Using with Configuration Management

```bash
# Generate and upload config to PostgreSQL
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/marketing" \
  --kb-name "marketing-docs" \
  --output "marketing-config.json"

document-loader upload-config marketing-config.json \
  --name "marketing-sharepoint" \
  --description "Marketing team SharePoint documents"

# Deploy when ready
document-loader deploy-config "marketing-sharepoint"
```

### Batch Processing Multiple Sites

```bash
#!/bin/bash
# Script to process multiple SharePoint sites

sites=(
  "https://company.sharepoint.com/sites/marketing"
  "https://company.sharepoint.com/sites/hr" 
  "https://company.sharepoint.com/sites/engineering"
)

for site in "${sites[@]}"; do
  sitename=$(basename "$site")
  
  echo "Processing $sitename..."
  
  document-loader generate-sharepoint-config \
    "$site" \
    --kb-name "${sitename}-docs" \
    --rag-type "azure_blob" \
    --output "${sitename}-config.json"
    
  document-loader create-kb \
    --name "${sitename}-docs" \
    --source-type "sharepoint" \
    --source-config "@${sitename}-config.json" \
    --rag-type "azure_blob"
done
```

## Best Practices

### 1. Use Service Principal Authentication

For production deployments, always use service principal authentication rather than user credentials:

```bash
# Set up environment variables once
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# Then commands don't need auth parameters
document-loader discover-sharepoint "https://company.sharepoint.com/sites/docs"
```

### 2. Start with Discovery

Always run discovery first to understand what's available:

```bash
# Discover first
document-loader discover-sharepoint "https://company.sharepoint.com/sites/hr" --verbose

# Then generate config based on what you found
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/hr" \
  --libraries "Documents,Policies" \
  --kb-name "hr-docs"
```

### 3. Validate Configurations

Review generated configurations before creating knowledge bases:

```bash
# Generate config to file
document-loader generate-sharepoint-config \
  "https://company.sharepoint.com/sites/marketing" \
  --output "marketing-config.json"

# Review the file before proceeding
cat marketing-config.json | jq '.'

# Then create KB
document-loader create-kb \
  --name "marketing-docs" \
  --source-type "sharepoint" \
  --source-config @marketing-config.json \
  --rag-type "azure_blob"
```

### 4. Use Descriptive Names

Choose descriptive knowledge base names that indicate the source and content:

```bash
# Good names
--kb-name "hr-policies-and-forms"
--kb-name "marketing-campaign-docs" 
--kb-name "engineering-specifications"

# Less clear names
--kb-name "docs"
--kb-name "sharepoint-kb"
--kb-name "site1"
```

This discovery functionality eliminates the need for users to manually determine site IDs, list IDs, and other technical details, making SharePoint integration much more accessible!