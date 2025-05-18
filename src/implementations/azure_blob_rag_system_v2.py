"""
Azure Blob RAG System implementation with comprehensive configuration
"""
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, ClientSecretCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from ..abstractions.rag_system import RAGSystem, DocumentMetadata
from .azure_blob_rag_config import (
    AzureBlobRAGConfig, 
    AzureAuthMethod, 
    AzureServicePrincipalAuth,
    get_default_config
)

logger = logging.getLogger(__name__)

class AzureBlobRAGSystem(RAGSystem):
    """Azure Blob Storage implementation of RAGSystem with full configuration support."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Azure Blob RAG system with comprehensive configuration.
        
        Args:
            config: Configuration dictionary that matches AzureBlobRAGConfig structure
        """
        super().__init__(config)
        
        # Parse configuration
        self.config = AzureBlobRAGConfig.from_dict(config)
        
        # Initialize clients
        self.blob_service_client = None
        self.container_client = None
        self.search_client = None
        self.search_index_client = None
        
        # Set up authentication
        self._setup_authentication()
        
    def _setup_authentication(self):
        """Set up Azure authentication based on configuration"""
        if self.config.auth_method == AzureAuthMethod.CONNECTION_STRING:
            if not self.config.connection_string:
                raise ValueError("Connection string required for connection_string auth method")
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.config.connection_string
            )
            
        elif self.config.auth_method == AzureAuthMethod.SERVICE_PRINCIPAL:
            if not self.config.service_principal:
                raise ValueError("Service principal configuration required")
            
            # Use environment variables as fallback
            sp = self.config.service_principal
            credential = ClientSecretCredential(
                tenant_id=sp.tenant_id or os.getenv('AZURE_TENANT_ID'),
                client_id=sp.client_id or os.getenv('AZURE_CLIENT_ID'),
                client_secret=sp.client_secret or os.getenv('AZURE_CLIENT_SECRET')
            )
            
            account_url = f"https://{self.config.blob_config.storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
            
        elif self.config.auth_method == AzureAuthMethod.MANAGED_IDENTITY:
            credential = ManagedIdentityCredential()
            account_url = f"https://{self.config.blob_config.storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
            
        elif self.config.auth_method == AzureAuthMethod.DEFAULT_CREDENTIAL:
            credential = DefaultAzureCredential()
            account_url = f"https://{self.config.blob_config.storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
            
        # Set up Azure Search if configured
        if self.config.search_config and self.config.search_config.endpoint:
            search_credential = credential if hasattr(self, 'credential') else None
            if self.config.search_config.api_key:
                from azure.core.credentials import AzureKeyCredential
                search_credential = AzureKeyCredential(self.config.search_config.api_key)
                
            self.search_client = SearchClient(
                endpoint=self.config.search_config.endpoint,
                index_name=self.config.search_config.index_name,
                credential=search_credential
            )
            
            self.search_index_client = SearchIndexClient(
                endpoint=self.config.search_config.endpoint,
                credential=search_credential
            )
    
    async def initialize(self):
        """Initialize the Azure Blob RAG system and create container if needed."""
        logger.info(f"Initializing Azure Blob RAG system for container: {self.config.blob_config.container_name}")
        
        try:
            # Get or create container
            self.container_client = self.blob_service_client.get_container_client(
                self.config.blob_config.container_name
            )
            
            # Check if container exists
            try:
                properties = self.container_client.get_container_properties()
                logger.info(f"Container {self.config.blob_config.container_name} already exists")
            except:
                # Create container with configured settings
                self.container_client.create_container(
                    public_access=self.config.blob_config.public_access_level
                )
                logger.info(f"Created container {self.config.blob_config.container_name}")
                
                # Configure container settings
                if self.config.blob_config.enable_versioning:
                    # Note: Versioning is set at storage account level in Azure
                    logger.info("Blob versioning should be enabled at storage account level")
                
            # Initialize search index if configured
            if self.config.search_config and self.config.search_config.index_name:
                await self._initialize_search_index()
                
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob RAG system: {e}")
            raise
    
    async def _initialize_search_index(self):
        """Initialize Azure Cognitive Search index if configured"""
        if not self.search_index_client:
            return
            
        try:
            # Check if index exists
            index = self.search_index_client.get_index(self.config.search_config.index_name)
            logger.info(f"Search index {self.config.search_config.index_name} already exists")
        except:
            # Create index with basic schema
            from azure.search.documents.indexes.models import (
                SearchIndex, SimpleField, SearchableField, SearchFieldDataType
            )
            
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="filename", type=SearchFieldDataType.String),
                SimpleField(name="uri", type=SearchFieldDataType.String),
                SimpleField(name="kb_name", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset),
                SimpleField(name="updated_at", type=SearchFieldDataType.DateTimeOffset),
            ]
            
            index = SearchIndex(
                name=self.config.search_config.index_name,
                fields=fields
            )
            
            self.search_index_client.create_index(index)
            logger.info(f"Created search index {self.config.search_config.index_name}")
    
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
            The blob URI
        """
        logger.info(f"Uploading document to Azure Blob: {filename}")
        
        try:
            # Determine content type
            content_type = metadata.get('content_type', 'application/octet-stream')
            
            # Prepare blob client
            blob_client = self.container_client.get_blob_client(filename)
            
            # Upload with metadata and content settings
            blob_metadata = {
                'kb_name': metadata.get('kb_name', ''),
                'original_path': metadata.get('original_path', ''),
                'file_hash': metadata.get('file_hash', ''),
                'uploaded_at': metadata.get('uploaded_at', ''),
            }
            
            content_settings = ContentSettings(content_type=content_type)
            
            # Upload blob
            blob_client.upload_blob(
                content,
                metadata=blob_metadata,
                content_settings=content_settings,
                overwrite=True,
                standard_blob_tier=self.config.blob_tier
            )
            
            # Get the blob URL
            blob_url = blob_client.url
            
            # Index in search if configured
            if self.search_client and self.config.enable_blob_indexing:
                await self._index_document(filename, content, metadata, blob_url)
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload document {filename}: {e}")
            raise
    
    async def _index_document(self, filename: str, content: bytes, metadata: Dict[str, Any], uri: str):
        """Index document in Azure Cognitive Search"""
        if not self.search_client:
            return
            
        try:
            # Extract text content (simplified - in practice use Azure Form Recognizer or similar)
            text_content = content.decode('utf-8', errors='ignore')[:32000]  # Limit for search
            
            document = {
                "id": filename,
                "content": text_content,
                "filename": filename,
                "uri": uri,
                "kb_name": metadata.get('kb_name', ''),
                "created_at": metadata.get('created_at'),
                "updated_at": metadata.get('updated_at')
            }
            
            self.search_client.upload_documents([document])
            logger.info(f"Indexed document {filename} in search")
            
        except Exception as e:
            logger.warning(f"Failed to index document {filename}: {e}")
    
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
        
        try:
            # Extract blob name from URI
            blob_name = uri.split('/')[-1]
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Check if blob exists
            if not blob_client.exists():
                raise ValueError(f"Blob {blob_name} not found")
            
            # Update blob
            await self.upload_document(content, blob_name, metadata)
            
        except Exception as e:
            logger.error(f"Failed to update document {uri}: {e}")
            raise
    
    async def delete_document(self, uri: str):
        """
        Delete a document from Azure Blob Storage.
        
        Args:
            uri: The blob URI to delete
        """
        logger.info(f"Deleting document from Azure Blob: {uri}")
        
        try:
            # Extract blob name from URI
            blob_name = uri.split('/')[-1]
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Delete blob
            blob_client.delete_blob()
            
            # Remove from search index if configured
            if self.search_client:
                try:
                    self.search_client.delete_documents([{"id": blob_name}])
                except Exception as e:
                    logger.warning(f"Failed to remove {blob_name} from search index: {e}")
            
            logger.info(f"Deleted blob {blob_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete document {uri}: {e}")
            raise
    
    async def get_document(self, uri: str) -> Optional[DocumentMetadata]:
        """
        Get metadata for a document in Azure Blob Storage.
        
        Args:
            uri: The blob URI
            
        Returns:
            DocumentMetadata if found, None otherwise
        """
        logger.info(f"Getting document metadata from Azure Blob: {uri}")
        
        try:
            # Extract blob name from URI
            blob_name = uri.split('/')[-1]
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Get blob properties
            properties = blob_client.get_blob_properties()
            
            # Convert to DocumentMetadata
            return DocumentMetadata(
                rag_id=blob_name,
                file_hash=properties.metadata.get('file_hash', ''),
                rag_uri=uri,
                created_at=properties.creation_time,
                updated_at=properties.last_modified,
                metadata=properties.metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to get document {uri}: {e}")
            return None
    
    async def list_documents(self, prefix: str = "") -> List[DocumentMetadata]:
        """
        List all documents in Azure Blob Storage with optional prefix filter.
        
        Args:
            prefix: Filter blobs by prefix (e.g., folder path)
            
        Returns:
            List of DocumentMetadata objects
        """
        logger.info(f"Listing documents in Azure Blob with prefix: {prefix}")
        
        documents = []
        
        try:
            # List blobs with prefix
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            
            for blob in blobs:
                # Get full blob URL
                blob_client = self.container_client.get_blob_client(blob.name)
                blob_url = blob_client.url
                
                # Create DocumentMetadata
                doc = DocumentMetadata(
                    rag_id=blob.name,
                    file_hash=blob.metadata.get('file_hash', '') if blob.metadata else '',
                    rag_uri=blob_url,
                    created_at=blob.creation_time,
                    updated_at=blob.last_modified,
                    metadata=blob.metadata or {}
                )
                documents.append(doc)
                
            logger.info(f"Found {len(documents)} documents with prefix '{prefix}'")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise
    
    async def cleanup(self):
        """Clean up Azure resources."""
        logger.info("Cleaning up Azure Blob RAG system")
        
        # Azure SDK clients handle their own cleanup
        # Just log that we're done
        logger.info("Azure Blob RAG system cleanup complete")