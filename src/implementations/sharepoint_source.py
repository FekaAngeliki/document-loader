import os
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env.sharepoint')))
from typing import List, Dict, Any, AsyncIterator
from datetime import datetime
import logging
import aiohttp
from ..abstractions.file_source import FileSource, FileMetadata

logger = logging.getLogger(__name__)
class SharePointSource(FileSource):
    async def list_files_in_library(self, library_url: str, recursive: bool = True) -> list:
        """Recursively list all files in a document library."""
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

    async def download_file(self, file_url: str) -> bytes:
        """Download file content from SharePoint."""
        try:
            file = self.client.web.get_file_by_server_relative_url(file_url)
            self.client.load(file)
            self.client.execute_query()
            content = file.read()
            return content
        except Exception as e:
            logger.error(f"Error downloading file {file_url}: {e}")
            return b''

    async def list_site_pages(self) -> list:
        """List all site pages (.aspx files) in the Site Pages library."""
        try:
            site_pages_lib = await self.get_site_pages_library()
            if not site_pages_lib:
                return []
            return await self.list_files_in_library(site_pages_lib['url'], recursive=False)
        except Exception as e:
            logger.error(f"Error listing site pages: {e}")
            return []

    async def list_items_in_list(self, list_title: str) -> list:
        """List all items in a SharePoint list."""
        try:
            sp_list = self.client.web.lists.get_by_title(list_title)
            items = sp_list.items
            self.client.load(items)
            self.client.execute_query()
            return [item.properties for item in items]
        except Exception as e:
            logger.error(f"Error listing items in list {list_title}: {e}")
            return []
    async def list_document_libraries(self) -> list:
        """List all document libraries in the SharePoint site."""
        try:
            lists = self.client.web.lists
            self.client.load(lists)
            self.client.execute_query()
            doc_libs = [l for l in lists if l.properties.get('BaseTemplate') == 101]
            return [{
                'title': l.properties.get('Title'),
                'id': l.properties.get('Id'),
                'url': l.properties.get('RootFolder', {}).get('ServerRelativeUrl')
            } for l in doc_libs]
        except Exception as e:
            logger.error(f"Error listing document libraries: {e}")
            return []

    async def list_lists(self) -> list:
        """List all lists in the SharePoint site."""
        try:
            lists = self.client.web.lists
            self.client.load(lists)
            self.client.execute_query()
            # Exclude document libraries (BaseTemplate 101)
            sharepoint_lists = [l for l in lists if l.properties.get('BaseTemplate') != 101]
            return [{
                'title': l.properties.get('Title'),
                'id': l.properties.get('Id'),
                'url': l.properties.get('RootFolder', {}).get('ServerRelativeUrl')
            } for l in sharepoint_lists]
        except Exception as e:
            logger.error(f"Error listing lists: {e}")
            return []

    async def get_site_pages_library(self) -> dict:
        """Get the Site Pages library info."""
        try:
            lists = self.client.web.lists
            self.client.load(lists)
            self.client.execute_query()
            for l in lists:
                if l.properties.get('Title') == 'Site Pages':
                    return {
                        'title': l.properties.get('Title'),
                        'id': l.properties.get('Id'),
                        'url': l.properties.get('RootFolder', {}).get('ServerRelativeUrl')
                    }
            return {}
        except Exception as e:
            logger.error(f"Error getting Site Pages library: {e}")
            return {}
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
        from office365.sharepoint.client_context import ClientContext
        from office365.runtime.auth.client_credential import ClientCredential
        try:
            if self.client_id and self.client_secret and self.tenant_id:
                credentials = ClientCredential(self.client_id, self.client_secret)
                self.client = ClientContext(self.site_url).with_credentials(credentials)
                logger.info(f"Authenticated SharePoint source (service principal) for {self.site_url}")
            elif self.username and self.password:
                from office365.runtime.auth.user_credential import UserCredential
                self.client = ClientContext(self.site_url).with_credentials(UserCredential(self.username, self.password))
                logger.info(f"Authenticated SharePoint source (user credentials) for {self.site_url}")
            else:
                raise ValueError("Missing authentication credentials for SharePoint (need either client_id/client_secret/tenant_id or username/password)")
        except Exception as e:
            logger.error(f"Failed to authenticate SharePoint: {e}")
            raise
    
    async def list_files(self, path: str = "") -> List[FileMetadata]:
        """List all files in the SharePoint path using Office365-REST-Python-Client."""
        from office365.sharepoint.files.file import File
        from office365.sharepoint.folders.folder import Folder
        files = []
        try:
            folder_path = self.path if not path else path
            folder = self.client.web.get_folder_by_server_relative_url(folder_path)
            self.client.load(folder)
            self.client.execute_query()
            items = folder.files
            self.client.load(items)
            self.client.execute_query()
            for file in items:
                # Get file properties
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
    
    async def get_file_content(self, uri: str) -> bytes:
        """Get the content of a file from SharePoint."""
        # TODO: Implement actual SharePoint file download
        logger.warning(f"Mock download of {uri}")
        return b"Mock file content"
    
    async def get_file_metadata(self, uri: str) -> FileMetadata:
        """Get metadata for a file."""
        # TODO: Implement actual SharePoint metadata retrieval
        return FileMetadata(
            uri=uri,
            size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            content_type="application/octet-stream"
        )
    
    async def exists(self, uri: str) -> bool:
        """Check if a file exists in SharePoint."""
        # TODO: Implement actual SharePoint file existence check
        return True
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def stream_files(self, path: str = "") -> AsyncIterator[FileMetadata]:
        """Stream files for large directories."""
        # TODO: Implement streaming for large SharePoint libraries
        files = await self.list_files(path)
        for file in files:
            yield file