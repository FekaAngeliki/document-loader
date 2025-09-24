#!/usr/bin/env python3
"""
Enterprise SharePoint Setup Example

This script demonstrates how to set up and use the Enterprise SharePoint source
with your clientID, clientSecret, and tenantID for multiple department sites.
"""

import asyncio
import json
import os
from pathlib import Path

# Example of how to create a knowledge base with Enterprise SharePoint
async def create_enterprise_sharepoint_kb():
    """Create an enterprise SharePoint knowledge base."""
    
    # Your enterprise SharePoint configuration
    config = {
        "name": "enterprise-sharepoint-multi-dept",
        "source_type": "enterprise_sharepoint",
        "source_config": {
            # Authentication - use your credentials
            "tenant_id": "your-tenant-id-here",
            "client_id": "your-client-id-here", 
            "client_secret": "your-client-secret-here",
            
            # Multi-site configuration for different departments
            "sites": [
                {
                    "site_url": "https://yourorg.sharepoint.com/sites/hr",
                    "department": "HR",
                    "include_libraries": True,
                    "include_lists": True,
                    "include_site_pages": False,
                    "library_filters": ["Shared Documents", "Policies", "Employee Handbook"],
                    "list_filters": ["Employee Directory", "Training Records", "Benefits"]
                },
                {
                    "site_url": "https://yourorg.sharepoint.com/sites/finance", 
                    "department": "Finance",
                    "include_libraries": True,
                    "include_lists": True,
                    "include_site_pages": False,
                    "library_filters": ["Financial Reports", "Budgets", "Invoices"],
                    "list_filters": ["Expense Reports", "Budget Approvals", "Vendor List"]
                },
                {
                    "site_url": "https://yourorg.sharepoint.com/sites/marketing",
                    "department": "Marketing", 
                    "include_libraries": True,
                    "include_lists": False,
                    "include_site_pages": True,
                    "library_filters": ["Campaign Assets", "Brand Guidelines", "Marketing Materials"]
                },
                {
                    "site_url": "https://yourorg.sharepoint.com/sites/it",
                    "department": "IT",
                    "include_libraries": True,
                    "include_lists": True, 
                    "include_site_pages": False,
                    "library_filters": ["Documentation", "Software", "Licenses"],
                    "list_filters": ["IT Tickets", "Asset Inventory", "Software Licenses"]
                }
            ],
            
            # File filtering
            "include_extensions": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".doc", ".xls", ".ppt"],
            "exclude_extensions": [".tmp", ".log", ".bak", ".old"],
            "exclude_patterns": [
                "~$*",           # Word/Excel temp files
                "*.tmp*",        # Temporary files
                "*/_vti_*",      # SharePoint system folders
                "*/Forms/*",     # SharePoint forms
                "*/_private/*"   # Private folders
            ],
            
            # Processing options
            "recursive": True,
            "batch_size": 50,
            "max_retries": 3,
            "timeout": 30,
            "rate_limit_delay": 1.0
        },
        
        # RAG system configuration (Azure Blob Storage)
        "rag_type": "azure_blob",
        "rag_config": {
            "azure_tenant_id": "your-azure-tenant-id",
            "azure_subscription_id": "your-azure-subscription-id", 
            "azure_client_id": "your-azure-client-id",
            "azure_client_secret": "your-azure-client-secret",
            "azure_resource_group_name": "your-resource-group",
            "azure_storage_account_name": "yourstorageaccount",
            "azure_storage_container_name": "sharepoint-documents"
        }
    }
    
    return config

async def create_single_site_kb():
    """Create a knowledge base for a single SharePoint site."""
    
    config = {
        "name": "hr-sharepoint-kb", 
        "source_type": "enterprise_sharepoint",
        "source_config": {
            "tenant_id": "your-tenant-id-here",
            "client_id": "your-client-id-here",
            "client_secret": "your-client-secret-here",
            
            # Single site configuration
            "sites": [
                {
                    "site_url": "https://yourorg.sharepoint.com/sites/hr",
                    "department": "HR",
                    "include_libraries": True,
                    "include_lists": True,
                    "include_site_pages": False
                }
            ],
            
            "include_extensions": [".pdf", ".docx", ".xlsx"],
            "recursive": True
        },
        
        "rag_type": "azure_blob",
        "rag_config": {
            "azure_storage_container_name": "hr-documents"
        }
    }
    
    return config

def create_env_file():
    """Create environment file with your credentials."""
    
    env_content = """# Enterprise SharePoint Configuration
SHAREPOINT_TENANT_ID=your-tenant-id-here
SHAREPOINT_CLIENT_ID=your-client-id-here  
SHAREPOINT_CLIENT_SECRET=your-client-secret-here

# Azure Storage Configuration
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_SUBSCRIPTION_ID=your-azure-subscription-id
AZURE_CLIENT_ID=your-azure-client-id
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_RESOURCE_GROUP_NAME=your-resource-group
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount

# Database Configuration
DOCUMENT_LOADER_DB_HOST=localhost
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=document_loader
DOCUMENT_LOADER_DB_USER=biks
DOCUMENT_LOADER_DB_PASSWORD=biks2013
DOCUMENT_LOADER_DB_MIN_POOL_SIZE=10
DOCUMENT_LOADER_DB_MAX_POOL_SIZE=20

# Logging
DOCUMENT_LOADER_LOG_LEVEL=INFO
"""
    
    with open('.env.enterprise', 'w') as f:
        f.write(env_content)
    
    print("Created .env.enterprise file - please update with your actual credentials")

if __name__ == "__main__":
    print("Enterprise SharePoint Setup Example")
    print("=" * 50)
    
    # Create example configurations
    multi_dept_config = asyncio.run(create_enterprise_sharepoint_kb())
    single_site_config = asyncio.run(create_single_site_kb())
    
    # Save configurations to files
    with open('enterprise_sharepoint_multi_dept.json', 'w') as f:
        json.dump(multi_dept_config, f, indent=2)
    
    with open('enterprise_sharepoint_single_site.json', 'w') as f:
        json.dump(single_site_config, f, indent=2)
    
    # Create environment file template
    create_env_file()
    
    print("\nCreated configuration files:")
    print("- enterprise_sharepoint_multi_dept.json (multiple departments)")
    print("- enterprise_sharepoint_single_site.json (single site)")
    print("- .env.enterprise (environment variables template)")
    print("\nNext steps:")
    print("1. Update .env.enterprise with your actual credentials")
    print("2. Update site URLs in the JSON config files")
    print("3. Run: document-loader create-kb --config enterprise_sharepoint_multi_dept.json")