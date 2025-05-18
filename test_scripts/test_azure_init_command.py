#!/usr/bin/env python3
"""
Test script to demonstrate using the Azure Blob initialization command
"""
import subprocess
import sys
import os
import json

def create_test_kb():
    """Create a test knowledge base with Azure Blob configuration"""
    
    # Prepare the Azure Blob configuration
    azure_config = {
        # These will fallback to environment variables if not provided
        "azure_tenant_id": os.getenv('AZURE_TENANT_ID'),
        "azure_subscription_id": os.getenv('AZURE_SUBSCRIPTION_ID'),
        "azure_client_id": os.getenv('AZURE_CLIENT_ID'),
        "azure_client_secret": os.getenv('AZURE_CLIENT_SECRET'),
        "azure_resource_location": os.getenv('AZURE_RESOURCE_LOCATION', 'eastus'),
        "azure_resource_group_name": os.getenv('AZURE_RESOURCE_GROUP_NAME'),
        "azure_storage_account_name": os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
        "azure_storage_container_name": os.getenv('AZURE_STORAGE_CONTAINER_NAME')
    }
    
    # Source configuration (local file system for testing)
    source_config = {
        "root_path": "/tmp/test-documents",
        "include_patterns": ["*.txt", "*.pdf", "*.md"]
    }
    
    # Create the knowledge base
    cmd = [
        "document-loader", "create-kb",
        "--name", "azure-test-kb",
        "--source-type", "file_system",
        "--source-config", json.dumps(source_config),
        "--rag-type", "azure_blob",
        "--rag-config", json.dumps(azure_config)
    ]
    
    print("Creating knowledge base with Azure Blob configuration...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error creating knowledge base: {result.stderr}")
        return False
    
    print("Knowledge base created successfully!")
    return True

def init_azure_storage():
    """Initialize Azure storage for the knowledge base"""
    
    cmd = ["document-loader", "init-azure", "--kb-name", "azure-test-kb"]
    
    print("\nInitializing Azure Blob Storage...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error initializing Azure storage: {result.stderr}")
        return False
    
    print("Azure storage initialized successfully!")
    print(result.stdout)
    return True

def list_knowledge_bases():
    """List all knowledge bases to verify creation"""
    
    cmd = ["document-loader", "list-kb"]
    
    print("\nListing knowledge bases...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error listing knowledge bases: {result.stderr}")

def main():
    """Main test function"""
    print("Testing Azure Blob Storage Initialization")
    print("=" * 40)
    
    # Check environment variables
    required_vars = [
        'AZURE_TENANT_ID',
        'AZURE_SUBSCRIPTION_ID',
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET',
        'AZURE_RESOURCE_GROUP_NAME',
        'AZURE_STORAGE_ACCOUNT_NAME',
        'AZURE_STORAGE_CONTAINER_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these environment variables before running this test.")
        sys.exit(1)
    
    print("All required environment variables are set.")
    
    # Run the test
    if create_test_kb():
        if init_azure_storage():
            list_knowledge_bases()
            print("\nTest completed successfully!")
            print("\nYou can now:")
            print("1. Sync the knowledge base: document-loader sync --kb-name azure-test-kb")
            print("2. Check the info: document-loader info azure-test-kb")
        else:
            print("\nAzure initialization failed!")
    else:
        print("\nKnowledge base creation failed!")

if __name__ == "__main__":
    main()