#!/usr/bin/env python3
"""
Test script to demonstrate RAG configuration structures for different RAG types
"""
import json
import subprocess
import sys

def create_kb_with_file_system_storage():
    """Create a knowledge base with file system storage"""
    
    print("=== Creating Knowledge Base with File System Storage ===\n")
    
    source_config = {
        "root_path": "/tmp/test-documents",
        "include_patterns": ["*.txt", "*.pdf", "*.md"]
    }
    
    rag_config = {
        "storage_path": "/tmp/rag-storage",
        "kb_name": "test-fs-storage",
        "create_dirs": True,
        "preserve_structure": False,
        "metadata_format": "json"
    }
    
    cmd = [
        "document-loader", "create-kb",
        "--name", "test-fs-storage",
        "--source-type", "file_system",
        "--source-config", json.dumps(source_config),
        "--rag-type", "file_system_storage",
        "--rag-config", json.dumps(rag_config)
    ]
    
    print("Command:")
    print(" ".join(cmd))
    print("\nRAG Configuration:")
    print(json.dumps(rag_config, indent=2))
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("\n✓ Knowledge base created successfully!")
    else:
        print(f"\n✗ Error: {result.stderr}")

def create_kb_with_azure_blob():
    """Create a knowledge base with Azure Blob storage"""
    
    print("\n=== Creating Knowledge Base with Azure Blob Storage ===\n")
    
    source_config = {
        "root_path": "/tmp/test-documents",
        "include_patterns": ["*.txt", "*.pdf", "*.md"]
    }
    
    # Using empty config to demonstrate environment variable usage
    rag_config = {}
    
    cmd = [
        "document-loader", "create-kb",
        "--name", "test-azure-blob",
        "--source-type", "file_system",
        "--source-config", json.dumps(source_config),
        "--rag-type", "azure_blob",
        "--rag-config", json.dumps(rag_config)
    ]
    
    print("Command:")
    print(" ".join(cmd))
    print("\nRAG Configuration:")
    print("Using environment variables:")
    print("- AZURE_TENANT_ID")
    print("- AZURE_SUBSCRIPTION_ID")
    print("- AZURE_CLIENT_ID")
    print("- AZURE_CLIENT_SECRET")
    print("- AZURE_RESOURCE_GROUP_NAME")
    print("- AZURE_STORAGE_ACCOUNT_NAME")
    print("- AZURE_STORAGE_CONTAINER_NAME")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("\n✓ Knowledge base created successfully!")
    else:
        print(f"\n✗ Error: {result.stderr}")

def create_kb_with_azure_blob_explicit():
    """Create a knowledge base with Azure Blob storage using explicit config"""
    
    print("\n=== Creating Knowledge Base with Azure Blob Storage (Explicit Config) ===\n")
    
    source_config = {
        "root_path": "/tmp/test-documents",
        "include_patterns": ["*.txt", "*.pdf", "*.md"]
    }
    
    rag_config = {
        "azure_tenant_id": "your-tenant-id",
        "azure_subscription_id": "your-subscription-id",
        "azure_client_id": "your-client-id",
        "azure_client_secret": "your-client-secret",
        "azure_resource_group_name": "your-resource-group",
        "azure_storage_account_name": "yourstorageaccount",
        "azure_storage_container_name": "your-container"
    }
    
    cmd = [
        "document-loader", "create-kb",
        "--name", "test-azure-explicit",
        "--source-type", "file_system",
        "--source-config", json.dumps(source_config),
        "--rag-type", "azure_blob",
        "--rag-config", json.dumps(rag_config)
    ]
    
    print("Command:")
    print(" ".join(cmd))
    print("\nRAG Configuration:")
    print(json.dumps(rag_config, indent=2))
    
    print("\n⚠ Note: This example uses placeholder values. Replace with actual Azure credentials.")

def show_help():
    """Show the help text for create-kb command"""
    
    print("\n=== Command Help ===\n")
    
    result = subprocess.run(
        ["document-loader", "create-kb", "--help"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)

def main():
    """Main demonstration function"""
    
    print("RAG Configuration Examples")
    print("=" * 50)
    
    # Show help first
    show_help()
    
    # Demonstrate different configurations
    create_kb_with_file_system_storage()
    create_kb_with_azure_blob()
    create_kb_with_azure_blob_explicit()
    
    print("\n" + "=" * 50)
    print("Configuration Summary")
    print("=" * 50)
    
    print("\nFile System Storage Configuration Fields:")
    print("- storage_path: Base directory for storing documents")
    print("- kb_name: Subdirectory name for this knowledge base")
    print("- create_dirs: Auto-create directories if they don't exist")
    print("- preserve_structure: Keep original directory structure")
    print("- metadata_format: Format for metadata files ('json' or 'yaml')")
    
    print("\nAzure Blob Storage Configuration Fields:")
    print("- azure_tenant_id: Azure AD tenant ID")
    print("- azure_subscription_id: Azure subscription ID")
    print("- azure_client_id: Service principal client ID")
    print("- azure_client_secret: Service principal client secret")
    print("- azure_resource_group_name: Resource group name")
    print("- azure_storage_account_name: Storage account name")
    print("- azure_storage_container_name: Blob container name")
    print("\nNote: All Azure fields can be provided via environment variables")

if __name__ == "__main__":
    main()