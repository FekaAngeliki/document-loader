import os
import logging
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env.sharepoint')))
from typing import List, Dict, Any
from datetime import datetime
from ..abstractions.file_source import FileSource, FileMetadata

logger = logging.getLogger(__name__)

class SharePointSource(FileSource):
    """SharePoint implementation of FileSource.
    
    Note: This is a basic implementation. In production, you would need to
    implement proper authentication and use the SharePoint API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.site_url = config.get('site_url')
        self.site_id = config.get('site_id')
        self.path = config.get('path', '/')
        self.recursive = config.get('recursive', True)
        self.username = config.get('username')
        self.password = config.get('password')
        self.tenant_id = config.get('tenant_id')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.client = None

    async def initialize(self):
        """Initialize the SharePoint connection using service principal credentials if provided."""
        try:
            # Check if Office365-REST-Python-Client is available
            try:
                from office365.sharepoint.client_context import ClientContext
                from office365.runtime.auth.client_credential import ClientCredential
            except ImportError:
                logger.warning("Office365-REST-Python-Client not available, using mock implementation")
                return
            
            if self.client_id and self.client_secret and self.tenant_id:
                credentials = ClientCredential(self.client_id, self.client_secret)
                self.client = ClientContext(self.site_url).with_credentials(credentials)
                logger.info(f"Authenticated SharePoint source (service principal) for {self.site_url}")
            elif self.username and self.password:
                from office365.runtime.auth.user_credential import UserCredential
                self.client = ClientContext(self.site_url).with_credentials(UserCredential(self.username, self.password))
                logger.info(f"Authenticated SharePoint source (user credentials) for {self.site_url}")
            else:
                logger.warning("Missing authentication credentials for SharePoint")
        except Exception as e:
            logger.error(f"Failed to authenticate SharePoint: {e}")
            # Don't raise - allow mock implementation to work
    
    async def list_files(self, path: str = "") -> List[FileMetadata]:
        """List all files in the SharePoint path using Office365-REST-Python-Client."""
        if not self.client:
            # Mock implementation for testing
            logger.info(f"Using mock SharePoint file listing for {path or self.path}")
            return []
        
        try:
            from office365.sharepoint.files.file import File
            from office365.sharepoint.folders.folder import Folder
            
            files = []
            folder_path = self.path if not path else path
            folder = self.client.web.get_folder_by_server_relative_url(folder_path)
            self.client.load(folder)
            self.client.execute_query()
            items = folder.files
            self.client.load(items)
            self.client.execute_query()
            
            for file in items:
                files.append(FileMetadata(
                    uri=file.serverRelativeUrl,
                    size=file.length,
                    created_at=file.time_created,
                    modified_at=file.time_last_modified,
                    content_type=file.properties.get('MimeType', 'application/octet-stream')
                ))
            
            # Optionally recurse into subfolders
            if self.recursive:
                subfolders = folder.folders
                self.client.load(subfolders)
                self.client.execute_query()
                for subfolder in subfolders:
                    files.extend(await self.list_files(subfolder.serverRelativeUrl))
            
            return files
        except Exception as e:
            logger.error(f"Error listing files from SharePoint: {e}")
            return []

    async def list_files_in_library(self, library_url: str, recursive: bool = True) -> list:
        """Recursively list all files in a document library."""
        if not self.client:
            logger.info(f"Using mock SharePoint library listing for {library_url}")
            return []
        
        files = []
        try:
            folder = self.client.web.get_folder_by_server_relative_url(library_url)
            self.client.load(folder)
            self.client.execute_query()
            
            # List files in current folder
            self.client.load(folder.files)
            self.client.execute_query()
            for file in folder.files:
                files.append({
                    'name': file.properties.get('Name'),
                    'url': file.properties.get('ServerRelativeUrl'),
                    'size': file.properties.get('Length'),
                    'created': file.properties.get('TimeCreated'),
                    'modified': file.properties.get('TimeLastModified'),
                    'mime_type': file.properties.get('MimeType', 'application/octet-stream')
                })
                
            # Recurse into subfolders
            if recursive:
                self.client.load(folder.folders)
                self.client.execute_query()
                for subfolder in folder.folders:
                    files.extend(await self.list_files_in_library(subfolder.properties.get('ServerRelativeUrl'), recursive=True))
            return files
        except Exception as e:
            logger.error(f"Error listing files in library {library_url}: {e}")
            return []
    
    async def get_file_content(self, uri: str) -> bytes:
        """Get the content of a file from SharePoint."""
        if not self.client:
            logger.info(f"Using mock SharePoint file content for {uri}")
            return b"Mock SharePoint file content"
        
        try:
            file = self.client.web.get_file_by_server_relative_url(uri)
            self.client.load(file)
            self.client.execute_query()
            content = file.read()
            return content
        except Exception as e:
            logger.error(f"Error downloading file {uri}: {e}")
            return b''
    
    async def get_file_metadata(self, uri: str) -> FileMetadata:
        """Get metadata for a SharePoint file."""
        if not self.client:
            logger.info(f"Using mock SharePoint metadata for {uri}")
            return FileMetadata(
                uri=uri,
                size=1024,
                created_at=datetime.utcnow(),
                modified_at=datetime.utcnow(),
                content_type="application/octet-stream"
            )
        
        try:
            file = self.client.web.get_file_by_server_relative_url(uri)
            self.client.load(file)
            self.client.execute_query()
            
            return FileMetadata(
                uri=file.serverRelativeUrl,
                size=file.length,
                created_at=file.time_created,
                modified_at=file.time_last_modified,
                content_type=file.properties.get('MimeType', 'application/octet-stream')
            )
        except Exception as e:
            logger.error(f"Error getting metadata for {uri}: {e}")
            return FileMetadata(
                uri=uri,
                size=0,
                created_at=datetime.utcnow(),
                modified_at=datetime.utcnow(),
                content_type="application/octet-stream"
            )
    
    async def exists(self, uri: str) -> bool:
        """Check if a file exists in SharePoint."""
        if not self.client:
            logger.info(f"Using mock SharePoint exists check for {uri}")
            return True
        
        try:
            file = self.client.web.get_file_by_server_relative_url(uri)
            self.client.load(file)
            self.client.execute_query()
            return True
        except Exception as e:
            logger.debug(f"File {uri} does not exist: {e}")
            return False
    
    async def cleanup(self):
        """Clean up SharePoint resources."""
        logger.info("Cleaning up SharePoint connection")
        self.client = None