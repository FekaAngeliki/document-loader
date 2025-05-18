from dotenv import load_dotenv
load_dotenv()

import logging
from typing import Dict, Any, List, Optional

from ..abstractions.rag_system import RAGSystem, DocumentMetadata

logger = logging.getLogger(__name__)

import os
AZURE_TENANT_ID= os.getenv('AZURE_TENANT_ID')
AZURE_SUBSCRIPTION_ID= os.getenv('AZURE_SUBSCRIPTION_ID') 
AZURE_CLIENT_ID= os.getenv('AZURE_CLIENT_ID') 
AZURE_CLIENT_SECRET= os.getenv('AZURE_CLIENT_SECRET') 
AZURE_RESOURCE_LOCATION= os.getenv('AZURE_RESOURCE_LOCATION')
AZURE_RESOURCE_GROUP_NAME= os.getenv('AZURE_RESOURCE_GROUP_NAME')

AZURE_STORAGE_ACCOUNT_NAME= os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
AZURE_STORAGE_CONTAINER_NAME= os.getenv('AZURE_STORAGE_CONTAINER_NAME')

from azwrap import Identity, Subscription, ResourceGroup, StorageAccount, BlobContainer
class AzureBlobRAGSystem(RAGSystem):
    """Azure Blob Storage implementation of RAGSystem."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Azure Blob RAG system.
        
        Args:
            config: Configuration dictionary that should contain:
                - azure_tenant_id: Azure tenant ID
                - azure_subscription_id: Azure subscription ID
                - azure_client_id: Azure client ID
                - azure_client_secret: Azure client secret
                - azure_resource_location: Azure resource location
                - azure_resource_group_name: Azure resource group name
                - azure_storage_account_name: Azure storage account name
                - azure_storage_container_name: Azure storage container name
        """
        super().__init__(config)
        # TODO: Initialize Azure SDK clients

        if config is None:
            config = {} 
        self.azure_tenant_id = config.get('azure_tenant_id') | AZURE_TENANT_ID
        self.azure_subscription_id = config.get('azure_subscription_id') | AZURE_SUBSCRIPTION_ID
        self.azure_client_id = config.get('azure_client_id') | AZURE_CLIENT_ID
        self.azure_client_secret = config.get('azure_client_secret') | AZURE_CLIENT_SECRET
        self.azure_resource_location = config.get('azure_resource_location') | AZURE_RESOURCE_LOCATION
        self.azure_resource_group_name = config.get('azure_resource_group_name') | AZURE_RESOURCE_GROUP_NAME

        self.azure_storage_account_name = config.get('azure_storage_account_name') | AZURE_STORAGE_ACCOUNT_NAME
        self.azure_storage_container_name = config.get('azure_storage_container_name') | AZURE_STORAGE_CONTAINER_NAME


    
    async def initialize(self):
        """Initialize the Azure Blob RAG system and create container if needed."""
        logger.info("Initializing Azure Blob RAG system")

        identity = Identity( 
            tenant_id=self.azure_tenant_id, 
            subscription_id=self.azure_subscription_id, 
            client_id=self.azure_client_id, 
            client_secret=self.azure_client_secret
        )
        subscription: Subscription = identity.get_subscription(self.azure_subscription_id)
        resource_group: ResourceGroup = subscription.get_resource_group(self.azure_resource_group_name)
        storage_account:StorageAccount = resource_group.get_storage_account(self.azure_storage_account_name)
        if not storage_account.exists():
            logger.info(f"Creating storage account '{self.azure_storage_account_name}'...")
            storage_account = resource_group.create_storage_account(self.azure_storage_account_name, self.azure_resource_location)
            logger.info(f"Storage account '{self.azure_storage_account_name}' created successfully")

        container: BlobContainer = storage_account.get_blob_container(self.azure_storage_container_name)
        if container is None:
            logger.info(f"Creating blob container '{self.azure_storage_container_name}'...")
            container = storage_account.create_blob_container(self.azure_storage_container_name)
            logger.info(f"Blob container '{self.azure_storage_container_name}' created successfully")
        else:
            logger.info(f"Blob container '{self.azure_storage_container_name}' already exists")
        
    
    async def upload_document(self, 
                           content: bytes, 
                           filename: str, 
                           metadata: Dict[str, Any]) -> str:
        """
        Upload a document to Azure Blob Storage.
        
        Args:
            content: File content as bytes
            filename: UUID filename to use in blob storage
            metadata: Metadata to attach to the blob
            
        Returns:
            The blob URI (e.g., https://account.blob.core.windows.net/container/filename)
        """
        logger.info(f"Uploading document to Azure Blob: {filename}")
        # TODO: Implement upload logic
        # - Upload blob to container
        # - Set blob metadata
        # - Optionally index in Azure Search
        # - Return the blob URI
        raise NotImplementedError("Azure Blob upload not implemented")
    
    async def update_document(self, 
                           uri: str, 
                           content: bytes, 
                           metadata: Dict[str, Any]):
        """
        Update an existing document in Azure Blob Storage.
        
        Args:
            uri: The blob URI to update
            content: New file content
            metadata: New metadata
        """
        logger.info(f"Updating document in Azure Blob: {uri}")
        # TODO: Implement update logic
        # - Verify blob exists
        # - Upload new content
        # - Update metadata
        # - Update search index if configured
        raise NotImplementedError("Azure Blob update not implemented")
    
    async def delete_document(self, uri: str):
        """
        Delete a document from Azure Blob Storage.
        
        Args:
            uri: The blob URI to delete
        """
        logger.info(f"Deleting document from Azure Blob: {uri}")
        # TODO: Implement delete logic
        # - Delete blob from container
        # - Remove from search index if configured
        raise NotImplementedError("Azure Blob delete not implemented")
    
    async def get_document(self, uri: str) -> Optional[DocumentMetadata]:
        """
        Get metadata for a document in Azure Blob Storage.
        
        Args:
            uri: The blob URI
            
        Returns:
            DocumentMetadata if found, None otherwise
        """
        logger.info(f"Getting document metadata from Azure Blob: {uri}")
        # TODO: Implement get logic
        # - Get blob properties and metadata
        # - Return DocumentMetadata object
        raise NotImplementedError("Azure Blob get not implemented")
    
    async def list_documents(self, prefix: str = "") -> List[DocumentMetadata]:
        """
        List all documents in Azure Blob Storage with optional prefix filter.
        
        Args:
            prefix: Filter blobs by prefix (e.g., folder path)
            
        Returns:
            List of DocumentMetadata objects
        """
        logger.info(f"Listing documents in Azure Blob with prefix: {prefix}")
        # TODO: Implement list logic
        # - List blobs in container with prefix
        # - Convert to DocumentMetadata objects
        # - Return list
        raise NotImplementedError("Azure Blob list not implemented")
    
    async def cleanup(self):
        """Clean up Azure resources."""
        logger.info("Cleaning up Azure Blob RAG system")
        # TODO: Implement cleanup logic
        # - Close any open connections
        # - Release resources