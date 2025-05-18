#!/usr/bin/env python3
"""
Script to show all available options in the document-loader CLI
"""
import subprocess
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.factory import SourceFactory, RAGFactory

def show_available_types():
    """Display all available source and RAG types"""
    
    print("=== Document Loader Available Options ===\n")
    
    # Show source types
    source_factory = SourceFactory()
    print("Available Source Types:")
    for source_type in source_factory.sources.keys():
        print(f"  - {source_type}")
    
    print("\nAvailable RAG Types:")
    rag_factory = RAGFactory()
    for rag_type in rag_factory.systems.keys():
        print(f"  - {rag_type}")
    
    print("\n=== Configuration Examples ===\n")
    
    # File System Source
    print("File System Source Configuration:")
    print("""
{
  "root_path": "/path/to/documents",
  "include_patterns": ["**/*.pdf", "**/*.txt", "**/*.md"],
  "exclude_patterns": ["**/temp/*", "**/.git/*"]
}
""")
    
    # SharePoint Source
    print("SharePoint Source Configuration:")
    print("""
{
  "site_url": "https://company.sharepoint.com/sites/docs",
  "folder_path": "/Shared Documents",
  "username": "user@company.com",
  "password": "password"
}
""")
    
    # Azure Blob RAG
    print("Azure Blob RAG Configuration:")
    print("""
{
  "azure_tenant_id": "your-tenant-id",
  "azure_subscription_id": "your-subscription-id",
  "azure_client_id": "your-client-id",
  "azure_client_secret": "your-client-secret",
  "azure_resource_group_name": "your-resource-group",
  "azure_storage_account_name": "your-storage-account",
  "azure_storage_container_name": "your-container"
}

Or leave empty {} to use environment variables:
- AZURE_TENANT_ID
- AZURE_SUBSCRIPTION_ID
- AZURE_CLIENT_ID
- AZURE_CLIENT_SECRET
- AZURE_RESOURCE_GROUP_NAME
- AZURE_STORAGE_ACCOUNT_NAME
- AZURE_STORAGE_CONTAINER_NAME
""")
    
    # File System Storage
    print("File System Storage Configuration:")
    print("""
{
  "storage_path": "/path/to/rag/storage"
}
""")
    
    # Mock RAG
    print("Mock RAG Configuration:")
    print("""
{}  # No configuration required
""")

def show_command_help():
    """Show help for key commands"""
    
    print("\n=== Command Help ===\n")
    
    commands = [
        "create-kb",
        "update-kb",
        "scan",
        "init-azure"
    ]
    
    for cmd in commands:
        print(f"\n--- {cmd} ---")
        result = subprocess.run(
            ["document-loader", cmd, "--help"],
            capture_output=True,
            text=True
        )
        print(result.stdout)

def main():
    """Show all available options"""
    
    print("Document Loader CLI - All Available Options")
    print("=" * 50)
    
    # Show types and configurations
    show_available_types()
    
    # Show command help
    print("\nTo see detailed help for commands, run:")
    print("document-loader create-kb --help")
    print("document-loader update-kb --help")
    print("document-loader scan --help")
    print("document-loader init-azure --help")
    
    print("\nFor more information, see docs/command-line-help.md")

if __name__ == "__main__":
    main()