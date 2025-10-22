from dotenv import load_dotenv
load_dotenv()

import logging
from typing import Dict, Any, List, Optional

from ..abstractions.rag_system import RAGSystem, DocumentMetadata

logger = logging.getLogger(__name__)

import os
AZURE_TENANT_ID= os.getenv('DOCUMENT_LOADER_AZURE_TENANT_ID')
AZURE_SUBSCRIPTION_ID= os.getenv('DOCUMENT_LOADER_AZURE_SUBSCRIPTION_ID') 
AZURE_CLIENT_ID= os.getenv('DOCUMENT_LOADER_AZURE_CLIENT_ID') 
AZURE_CLIENT_SECRET= os.getenv('DOCUMENT_LOADER_AZURE_CLIENT_SECRET') 
AZURE_RESOURCE_LOCATION= os.getenv('DOCUMENT_LOADER_AZURE_RESOURCE_LOCATION')
AZURE_RESOURCE_GROUP_NAME= os.getenv('DOCUMENT_LOADER_AZURE_RESOURCE_GROUP_NAME')

AZURE_STORAGE_ACCOUNT_NAME= os.getenv('DOCUMENT_LOADER_AZURE_STORAGE_ACCOUNT_NAME')
AZURE_STORAGE_CONTAINER_NAME= os.getenv('DOCUMENT_LOADER_AZURE_STORAGE_CONTAINER_NAME')

from azure.storage.blob import BlobServiceClient, ContainerProperties, ContainerClient, BlobProperties
from azwrap import Identity, Subscription, ResourceGroup, StorageAccount, Container

# Define ResourceNotFoundError if not available in azwrap
try:
    from azwrap import ResourceNotFoundError
except ImportError:
    class ResourceNotFoundError(Exception):
        """Resource not found error when azwrap doesn't provide it"""
        pass

from ..cli.params import get_params, CommandLineParams
cli_params:CommandLineParams = get_params()

def configure_azure_logging():
    global cli_params
    verbose = cli_params.verbose

    """Configure Azure SDK logging based on verbose flag."""
    # List of Azure SDK loggers to configure
    azure_loggers = [
        'azure',
        'azure.core',
        'azure.core.pipeline',
        'azure.core.pipeline.policies',
        'azure.core.pipeline.policies.http_logging_policy',
        'azure.core.pipeline.policies._universal',
        'azure.identity',
        'azure.identity._internal',
        'azure.identity._credentials',
        'azure.identity._universal', 
        'azure.identity.get_token_mixin',
        'azure.mgmt',
        'azure.storage',
        'azure.storage.blob',
        'azure.storage.blob._blob_client',
        'azure.storage.blob._container_client',
        'azure.storage.blob._blob_service_client',
    ]
    
    # Set logging level based on verbose flag
    log_level = logging.DEBUG if verbose else logging.WARNING
    
    # Configure all Azure loggers
    for logger_name in azure_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
    
    # Also configure urllib3 which Azure SDK uses
    logging.getLogger('urllib3').setLevel(logging.WARNING if not verbose else logging.DEBUG)


configure_azure_logging()

def log_info( message: str):
    global cli_params
    if (cli_params.verbose):
        logger.info(message)
class AzureBlobRAGSystem(RAGSystem):
    """Azure Blob Storage implementation of RAGSystem."""
    
    azure_tenant_id: str = None
    azure_subscription_id : str = None
    azure_client_id : str = None
    azure_client_secret : str = None
    azure_resource_location : str = None
    azure_resource_group_name : str = None

    azure_storage_account_name : str = None
    azure_storage_container_name : str = None

    container: Container = None

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
        
        if config is None:
            config = {}
            
        # Use environment variables as fallback for missing config values
        self.azure_tenant_id = config.get('azure_tenant_id') or AZURE_TENANT_ID
        self.azure_subscription_id = config.get('azure_subscription_id') or AZURE_SUBSCRIPTION_ID
        self.azure_client_id = config.get('azure_client_id') or AZURE_CLIENT_ID
        self.azure_client_secret = config.get('azure_client_secret') or AZURE_CLIENT_SECRET
        self.azure_resource_location = config.get('azure_resource_location') or AZURE_RESOURCE_LOCATION
        self.azure_resource_group_name = config.get('azure_resource_group_name') or AZURE_RESOURCE_GROUP_NAME
        
        self.azure_storage_account_name = config.get('azure_storage_account_name') or AZURE_STORAGE_ACCOUNT_NAME
        self.azure_storage_container_name = config.get('azure_storage_container_name') or AZURE_STORAGE_CONTAINER_NAME
        
        # Validate required parameters
        missing_params = []
        if not self.azure_tenant_id:
            missing_params.append('azure_tenant_id (or DOCUMENT_LOADER_AZURE_TENANT_ID env var)')
        if not self.azure_subscription_id:
            missing_params.append('azure_subscription_id (or DOCUMENT_LOADER_AZURE_SUBSCRIPTION_ID env var)')
        if not self.azure_client_id:
            missing_params.append('azure_client_id (or DOCUMENT_LOADER_AZURE_CLIENT_ID env var)')
        if not self.azure_client_secret:
            missing_params.append('azure_client_secret (or DOCUMENT_LOADER_AZURE_CLIENT_SECRET env var)')
        if not self.azure_resource_group_name:
            missing_params.append('azure_resource_group_name (or DOCUMENT_LOADER_AZURE_RESOURCE_GROUP_NAME env var)')
        if not self.azure_storage_account_name:
            missing_params.append('azure_storage_account_name (or DOCUMENT_LOADER_AZURE_STORAGE_ACCOUNT_NAME env var)')
        if not self.azure_storage_container_name:
            missing_params.append('azure_storage_container_name (or DOCUMENT_LOADER_AZURE_STORAGE_CONTAINER_NAME env var)')
            
        if missing_params:
            raise ValueError(f"Missing required Azure configuration parameters: {', '.join(missing_params)}")
   
    async def initialize(self):
        """Initialize the Azure Blob RAG system and create container if needed."""
        log_info("Initializing Azure Blob RAG system")
        log_info("Get Identity")
        identity = Identity( 
            tenant_id=self.azure_tenant_id, 
            client_id=self.azure_client_id, 
            client_secret=self.azure_client_secret
        )
        log_info(f"Get Subscritption {self.azure_subscription_id}")
        subscription: Subscription = identity.get_subscription(self.azure_subscription_id)
        log_info(f"Get Resource Group {self.azure_resource_group_name}")
        resource_group: ResourceGroup = subscription.get_resource_group(self.azure_resource_group_name)
        log_info(f"Get StorageAccount {self.azure_storage_account_name}")
        try:
            storage_account:StorageAccount = resource_group.get_storage_account(self.azure_storage_account_name)
        except ResourceNotFoundError as e:
            log_info(f"Storage account {self.azure_storage_account_name} not found. Creating Storage account.")
            storage_account = resource_group.create_storage_account(self.azure_storage_account_name, self.azure_resource_location)
            log_info(f"Storage account '{self.azure_storage_account_name}' created successfully")

        if (storage_account is None):
            log_info(f"Storage account '{self.azure_storage_account_name}' not found and could not be created.")
        else:
            container: Container = storage_account.get_container(self.azure_storage_container_name)
            if container is None or container.container_client.exists() == False:
                log_info(f"Creating blob container '{self.azure_storage_container_name}'...")
                container = storage_account.create_container(self.azure_storage_container_name, public_access_level="container")
                log_info(f"Blob container '{self.azure_storage_container_name}' created successfully")
            else:
                log_info(f"Blob container '{self.azure_storage_container_name}' already exists")
                container = storage_account.create_container(self.azure_storage_container_name, public_access_level="container")
        
    async def get_container(self) -> Container:
        log_info("Initializing Azure Blob RAG system")

        log_info("Get Identity")
        identity = Identity( 
            tenant_id=self.azure_tenant_id, 
            client_id=self.azure_client_id, 
            client_secret=self.azure_client_secret
        )
        log_info(f"Get Subscritption {self.azure_subscription_id}")
        subscription: Subscription = identity.get_subscription(self.azure_subscription_id)
        log_info(f"Get Resource Group {self.azure_resource_group_name}")
        resource_group: ResourceGroup = subscription.get_resource_group(self.azure_resource_group_name)
        log_info(f"Get StorageAccount {self.azure_storage_account_name}")
        storage_account:StorageAccount = resource_group.get_storage_account(self.azure_storage_account_name)
        container: Container = storage_account.get_container(self.azure_storage_container_name)
        self.container = container
        return container

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

        log_info(f"Uploading document to Azure Blob: {filename}")
        log_info(f"Uploading document {filename} with metadata: {metadata} to Azure Blob")
        if (self.container is None):
            self.container = await self.get_container()
        log_info(f"Container: {self.container= } folder based on {metadata['kb_name']}")
        destination_blob_name = f"{metadata['kb_name']}/{filename}"
        
        from io import BytesIO
        buffered_reader = BytesIO(content)

        blobproperties:BlobProperties = self.container.upload_stream( buffered_reader, destination_blob_name = destination_blob_name)
        log_info(f"Uploaded document {filename} to Azure Blob: {blobproperties= }")


        # TODO: Implement upload logic
        # - Upload blob to container
        # - Set blob metadata
        # - Optionally index in Azure Search
        # - Return the blob URI
        #raise NotImplementedError("Azure Blob upload not implemented")
    
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
        log_info(f"Updating document in Azure Blob: {uri}")
        
        if (self.container is None):
            self.container = await self.get_container()
        log_info(f"Container: {self.container= } folder based on {metadata['kb_name']}")
        deleted = self.container.delete_blob(uri)
        log_info(f"Document in Azure Blob: {uri} succesfully(?) {deleted=}")
        from io import BytesIO
        buffered_reader = BytesIO(content)
        blobproperties:BlobProperties = self.container.upload_stream( buffered_reader, destination_blob_name = uri)
        log_info(f"Updated document {metadata=} to Azure Blob: {blobproperties= }")

        # TODO: Implement update logic
        # - Verify blob exists
        # - Upload new content
        # - Update metadata
        # - Update search index if configured
        #raise NotImplementedError("Azure Blob update not implemented")
    
    async def delete_document(self, uri: str):
        """
        Delete a document from Azure Blob Storage.
        
        Args:
            uri: The blob URI to delete
        """
        log_info(f"Updating document in Azure Blob: {uri}")
        
        if (self.container is None):
            self.container = await self.get_container()
        deleted = self.container.delete_blob(uri)
        log_info(f"Document in Azure Blob: {uri} succesfully(?) {deleted=}")

        # TODO: Implement delete logic
        # - Delete blob from container
        # - Remove from search index if configured
        #raise NotImplementedError("Azure Blob delete not implemented")
    
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