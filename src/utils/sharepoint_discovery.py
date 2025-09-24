"""
SharePoint Discovery Utility

This module provides functionality to discover SharePoint site information
from URLs without requiring users to know site IDs, list IDs, etc.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class SharePointSiteInfo:
    """Information about a SharePoint site."""
    site_url: str
    site_id: str
    site_name: str
    web_id: str
    tenant_name: str
    lists: List[Dict[str, Any]]
    libraries: List[Dict[str, Any]]
    pages: List[Dict[str, Any]]

@dataclass
class SharePointListInfo:
    """Information about a SharePoint list or library."""
    list_id: str
    title: str
    description: str
    list_type: str  # DocumentLibrary, GenericList, etc.
    url: str
    item_count: int
    created: datetime
    modified: datetime

class SharePointDiscovery:
    """
    SharePoint discovery utility that extracts site information from URLs.
    
    This class provides methods to:
    - Parse SharePoint URLs to extract tenant and site information
    - Connect to SharePoint using various authentication methods
    - Discover site metadata, lists, libraries, and pages
    - Generate configuration templates for the document loader
    """
    
    def __init__(self, auth_config: Dict[str, Any]):
        """
        Initialize SharePoint discovery client.
        
        Args:
            auth_config: Authentication configuration with keys:
                - tenant_id: Azure tenant ID
                - client_id: Azure app client ID  
                - client_secret: Azure app client secret
                OR
                - username: SharePoint username
                - password: SharePoint password
        """
        self.auth_config = auth_config
        self.client = None
        self.site_info = None
        
    async def initialize(self):
        """Initialize the SharePoint connection."""
        try:
            # Check if Office365-REST-Python-Client is available
            try:
                from office365.sharepoint.client_context import ClientContext
                from office365.runtime.auth.client_credential import ClientCredential
                from office365.runtime.auth.user_credential import UserCredential
            except ImportError:
                logger.error("Office365-REST-Python-Client not available. Install with: pip install Office365-REST-Python-Client")
                raise ImportError("Office365-REST-Python-Client package is required for SharePoint discovery")
            
            # Choose authentication method
            if all(key in self.auth_config for key in ['tenant_id', 'client_id', 'client_secret']):
                # Service principal authentication
                logger.info("Using service principal authentication")
                self.auth_method = "service_principal"
            elif all(key in self.auth_config for key in ['username', 'password']):
                # User credentials authentication
                logger.info("Using user credentials authentication")
                self.auth_method = "user_credentials"
            else:
                raise ValueError("Authentication configuration must include either (tenant_id, client_id, client_secret) or (username, password)")
                
        except Exception as e:
            logger.error(f"Failed to initialize SharePoint discovery: {e}")
            raise
    
    def parse_sharepoint_url(self, url: str) -> Dict[str, str]:
        """
        Parse a SharePoint URL to extract tenant and site information.
        
        Args:
            url: SharePoint site URL (e.g., https://contoso.sharepoint.com/sites/marketing)
            
        Returns:
            Dictionary with parsed URL components:
            - tenant_name: SharePoint tenant name
            - site_collection: Site collection name (if applicable)
            - site_name: Site name (if applicable)
            - base_url: Base SharePoint URL
            - site_url: Full site URL
        """
        parsed = urlparse(url)
        
        if 'sharepoint.com' not in parsed.netloc:
            raise ValueError(f"Invalid SharePoint URL: {url}")
        
        # Extract tenant name from domain
        tenant_match = re.match(r'([^.]+)\.sharepoint\.com', parsed.netloc)
        if not tenant_match:
            raise ValueError(f"Could not extract tenant name from URL: {url}")
        
        tenant_name = tenant_match.group(1)
        base_url = f"https://{parsed.netloc}"
        
        # Parse path to extract site collection and site info
        path_parts = [p for p in parsed.path.split('/') if p]
        
        site_collection = None
        site_name = None
        
        if path_parts:
            if path_parts[0] == 'sites' and len(path_parts) > 1:
                site_collection = 'sites'
                site_name = path_parts[1]
            elif path_parts[0] == 'teams' and len(path_parts) > 1:
                site_collection = 'teams'
                site_name = path_parts[1]
            elif len(path_parts) == 1:
                # Could be a root site
                site_name = path_parts[0]
        
        return {
            'tenant_name': tenant_name,
            'site_collection': site_collection,
            'site_name': site_name,
            'base_url': base_url,
            'site_url': url,
            'parsed_path': path_parts
        }
    
    async def discover_site(self, site_url: str) -> SharePointSiteInfo:
        """
        Discover comprehensive information about a SharePoint site.
        
        Args:
            site_url: SharePoint site URL
            
        Returns:
            SharePointSiteInfo object with site details
        """
        try:
            from office365.sharepoint.client_context import ClientContext
            from office365.runtime.auth.client_credential import ClientCredential
            from office365.runtime.auth.user_credential import UserCredential
        except ImportError:
            raise ImportError("Office365-REST-Python-Client package is required")
        
        # Parse URL
        url_info = self.parse_sharepoint_url(site_url)
        
        # Create client context
        if self.auth_method == "service_principal":
            credentials = ClientCredential(
                self.auth_config['client_id'],
                self.auth_config['client_secret']
            )
            ctx = ClientContext(site_url).with_credentials(credentials)
        else:
            credentials = UserCredential(
                self.auth_config['username'],
                self.auth_config['password']
            )
            ctx = ClientContext(site_url).with_credentials(credentials)
        
        self.client = ctx
        
        # Get site information
        site = ctx.site
        web = ctx.web
        ctx.load(site)
        ctx.load(web)
        ctx.execute_query()
        
        # Get lists and libraries
        lists = await self._discover_lists(ctx)
        libraries = await self._discover_libraries(ctx)
        pages = await self._discover_pages(ctx)
        
        site_info = SharePointSiteInfo(
            site_url=site_url,
            site_id=str(site.id),
            site_name=web.title,
            web_id=str(web.id),
            tenant_name=url_info['tenant_name'],
            lists=lists,
            libraries=libraries,
            pages=pages
        )
        
        self.site_info = site_info
        return site_info
    
    async def _discover_lists(self, ctx) -> List[Dict[str, Any]]:
        """Discover all lists in the site."""
        lists_info = []
        
        try:
            lists = ctx.web.lists
            ctx.load(lists)
            ctx.execute_query()
            
            for list_obj in lists:
                # Skip system lists and libraries
                if (not list_obj.hidden and 
                    list_obj.base_template != 101 and  # Document Library
                    list_obj.base_template != 851):    # Asset Library
                    
                    list_info = {
                        'id': str(list_obj.id),
                        'title': list_obj.title,
                        'description': list_obj.description,
                        'base_template': list_obj.base_template,
                        'item_count': list_obj.item_count,
                        'server_relative_url': list_obj.default_view_url,
                        'hidden': list_obj.hidden,
                        'list_type': 'GenericList'
                    }
                    lists_info.append(list_info)
                    
        except Exception as e:
            logger.warning(f"Could not retrieve lists: {e}")
        
        return lists_info
    
    async def _discover_libraries(self, ctx) -> List[Dict[str, Any]]:
        """Discover all document libraries in the site."""
        libraries_info = []
        
        try:
            lists = ctx.web.lists
            ctx.load(lists)
            ctx.execute_query()
            
            for list_obj in lists:
                # Only include document libraries
                if (not list_obj.hidden and 
                    list_obj.base_template in [101, 851]):  # Document Library, Asset Library
                    
                    library_info = {
                        'id': str(list_obj.id),
                        'title': list_obj.title,
                        'description': list_obj.description,
                        'base_template': list_obj.base_template,
                        'item_count': list_obj.item_count,
                        'server_relative_url': list_obj.default_view_url,
                        'hidden': list_obj.hidden,
                        'list_type': 'DocumentLibrary'
                    }
                    libraries_info.append(library_info)
                    
        except Exception as e:
            logger.warning(f"Could not retrieve libraries: {e}")
        
        return libraries_info
    
    async def _discover_pages(self, ctx) -> List[Dict[str, Any]]:
        """Discover pages in the site."""
        pages_info = []
        
        try:
            # Get Site Pages library
            site_pages = ctx.web.lists.get_by_title("Site Pages")
            ctx.load(site_pages)
            ctx.execute_query()
            
            items = site_pages.items
            ctx.load(items)
            ctx.execute_query()
            
            for item in items:
                page_info = {
                    'id': item.id,
                    'title': item.properties.get('Title', ''),
                    'file_name': item.properties.get('FileLeafRef', ''),
                    'server_relative_url': item.properties.get('FileRef', ''),
                    'created': item.properties.get('Created', ''),
                    'modified': item.properties.get('Modified', '')
                }
                pages_info.append(page_info)
                
        except Exception as e:
            logger.warning(f"Could not retrieve pages: {e}")
        
        return pages_info
    
    def generate_source_config(self, 
                             libraries: Optional[List[str]] = None,
                             lists: Optional[List[str]] = None,
                             include_pages: bool = False,
                             recursive: bool = True) -> Dict[str, Any]:
        """
        Generate a source configuration for the document loader.
        
        Args:
            libraries: List of library titles to include (default: all)
            lists: List of list titles to include (default: none)
            include_pages: Whether to include site pages
            recursive: Whether to scan recursively
            
        Returns:
            Dictionary with source configuration
        """
        if not self.site_info:
            raise ValueError("Site discovery must be completed first")
        
        config = {
            'site_url': self.site_info.site_url,
            'site_id': self.site_info.site_id,
            'site_name': self.site_info.site_name,
            'tenant_name': self.site_info.tenant_name,
            'recursive': recursive,
            'sources': []
        }
        
        # Add authentication config
        if self.auth_method == "service_principal":
            config.update({
                'tenant_id': self.auth_config.get('tenant_id'),
                'client_id': self.auth_config.get('client_id'),
                'client_secret': self.auth_config.get('client_secret')
            })
        else:
            config.update({
                'username': self.auth_config.get('username'),
                'password': self.auth_config.get('password')
            })
        
        # Add selected libraries
        if libraries is None:
            # Include all non-hidden libraries
            selected_libraries = [lib for lib in self.site_info.libraries if not lib.get('hidden', False)]
        else:
            # Include only specified libraries
            selected_libraries = [lib for lib in self.site_info.libraries if lib['title'] in libraries]
        
        for library in selected_libraries:
            source_config = {
                'type': 'library',
                'id': library['id'],
                'title': library['title'],
                'url': library['server_relative_url'],
                'item_count': library['item_count']
            }
            config['sources'].append(source_config)
        
        # Add selected lists
        if lists:
            selected_lists = [lst for lst in self.site_info.lists if lst['title'] in lists]
            for lst in selected_lists:
                source_config = {
                    'type': 'list',
                    'id': lst['id'],
                    'title': lst['title'],
                    'url': lst['server_relative_url'],
                    'item_count': lst['item_count']
                }
                config['sources'].append(source_config)
        
        # Add pages if requested
        if include_pages and self.site_info.pages:
            pages_config = {
                'type': 'pages',
                'title': 'Site Pages',
                'count': len(self.site_info.pages)
            }
            config['sources'].append(pages_config)
        
        return config
    
    def print_discovery_summary(self) -> str:
        """
        Generate a formatted summary of the discovery results.
        
        Returns:
            Formatted string with discovery summary
        """
        if not self.site_info:
            return "No site information available. Run discover_site() first."
        
        summary = f"""
SharePoint Site Discovery Summary
=================================

Site Information:
  Name: {self.site_info.site_name}
  URL: {self.site_info.site_url}
  Site ID: {self.site_info.site_id}
  Web ID: {self.site_info.web_id}
  Tenant: {self.site_info.tenant_name}

Document Libraries ({len(self.site_info.libraries)}):"""
        
        for lib in self.site_info.libraries:
            summary += f"\n  - {lib['title']} (ID: {lib['id']}, Items: {lib['item_count']})"
        
        if self.site_info.lists:
            summary += f"\n\nLists ({len(self.site_info.lists)}):"
            for lst in self.site_info.lists:
                summary += f"\n  - {lst['title']} (ID: {lst['id']}, Items: {lst['item_count']})"
        
        if self.site_info.pages:
            summary += f"\n\nPages ({len(self.site_info.pages)}):"
            for page in self.site_info.pages[:5]:  # Show first 5 pages
                summary += f"\n  - {page['title']}"
            if len(self.site_info.pages) > 5:
                summary += f"\n  ... and {len(self.site_info.pages) - 5} more pages"
        
        return summary