"""
SharePoint Configuration Helper

This module provides utilities to help users create SharePoint configurations
from discovery results with interactive prompts and validation.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

from .sharepoint_discovery import SharePointSiteInfo, SharePointDiscovery

logger = logging.getLogger(__name__)

@dataclass
class ConfigurationTemplate:
    """Template for generating SharePoint configurations."""
    name: str
    description: str
    includes_libraries: bool = True
    includes_lists: bool = False
    includes_pages: bool = False
    library_filter: Optional[List[str]] = None
    list_filter: Optional[List[str]] = None
    rag_type: str = "mock"
    rag_config: Dict[str, Any] = None

class SharePointConfigHelper:
    """
    Helper class for creating SharePoint configurations from discovery results.
    
    This class provides:
    - Interactive configuration creation
    - Configuration templates for common scenarios
    - Validation of configuration options
    - Export to various formats
    """
    
    def __init__(self, site_info: SharePointSiteInfo, auth_config: Dict[str, Any]):
        """
        Initialize the configuration helper.
        
        Args:
            site_info: SharePoint site information from discovery
            auth_config: Authentication configuration used for discovery
        """
        self.site_info = site_info
        self.auth_config = auth_config
        self.templates = self._create_default_templates()
    
    def _create_default_templates(self) -> List[ConfigurationTemplate]:
        """Create default configuration templates."""
        return [
            ConfigurationTemplate(
                name="all_documents",
                description="Include all document libraries",
                includes_libraries=True,
                includes_lists=False,
                includes_pages=False,
                rag_type="mock"
            ),
            ConfigurationTemplate(
                name="documents_and_lists",
                description="Include all document libraries and lists",
                includes_libraries=True,
                includes_lists=True,
                includes_pages=False,
                rag_type="mock"
            ),
            ConfigurationTemplate(
                name="everything",
                description="Include all content (documents, lists, and pages)",
                includes_libraries=True,
                includes_lists=True,
                includes_pages=True,
                rag_type="mock"
            ),
            ConfigurationTemplate(
                name="selective_documents",
                description="Select specific document libraries",
                includes_libraries=True,
                includes_lists=False,
                includes_pages=False,
                library_filter=[],  # Will be populated interactively
                rag_type="mock"
            )
        ]
    
    def list_available_sources(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get a summary of available sources in the SharePoint site.
        
        Returns:
            Dictionary with libraries, lists, and pages available
        """
        return {
            'libraries': [
                {
                    'title': lib['title'],
                    'id': lib['id'],
                    'item_count': lib['item_count'],
                    'description': lib.get('description', '')
                }
                for lib in self.site_info.libraries
                if not lib.get('hidden', False)
            ],
            'lists': [
                {
                    'title': lst['title'],
                    'id': lst['id'],
                    'item_count': lst['item_count'],
                    'description': lst.get('description', '')
                }
                for lst in self.site_info.lists
                if not lst.get('hidden', False)
            ],
            'pages': [
                {
                    'title': page['title'],
                    'file_name': page['file_name']
                }
                for page in self.site_info.pages[:10]  # Limit to first 10 for display
            ]
        }
    
    def create_configuration_from_template(self, template: ConfigurationTemplate, 
                                         kb_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a configuration from a template.
        
        Args:
            template: Configuration template to use
            kb_name: Knowledge base name (auto-generated if not provided)
            
        Returns:
            Complete knowledge base configuration
        """
        # Generate KB name if not provided
        if not kb_name:
            kb_name = f"{self.site_info.site_name.lower().replace(' ', '-')}-{template.name}"
        
        # Build source configuration
        source_config = {
            'site_url': self.site_info.site_url,
            'site_id': self.site_info.site_id,
            'site_name': self.site_info.site_name,
            'tenant_name': self.site_info.tenant_name,
            'recursive': True,
            'sources': []
        }
        
        # Add authentication config
        source_config.update(self.auth_config)
        
        # Add libraries
        if template.includes_libraries:
            libraries_to_include = self.site_info.libraries
            if template.library_filter:
                libraries_to_include = [
                    lib for lib in self.site_info.libraries 
                    if lib['title'] in template.library_filter
                ]
            
            for library in libraries_to_include:
                if not library.get('hidden', False):
                    source_config['sources'].append({
                        'type': 'library',
                        'id': library['id'],
                        'title': library['title'],
                        'url': library['server_relative_url'],
                        'item_count': library['item_count']
                    })
        
        # Add lists
        if template.includes_lists:
            lists_to_include = self.site_info.lists
            if template.list_filter:
                lists_to_include = [
                    lst for lst in self.site_info.lists 
                    if lst['title'] in template.list_filter
                ]
            
            for lst in lists_to_include:
                if not lst.get('hidden', False):
                    source_config['sources'].append({
                        'type': 'list',
                        'id': lst['id'],
                        'title': lst['title'],
                        'url': lst['server_relative_url'],
                        'item_count': lst['item_count']
                    })
        
        # Add pages
        if template.includes_pages and self.site_info.pages:
            source_config['sources'].append({
                'type': 'pages',
                'title': 'Site Pages',
                'count': len(self.site_info.pages)
            })
        
        # Build complete configuration
        config = {
            'name': kb_name,
            'description': f"SharePoint knowledge base for {self.site_info.site_name} - {template.description}",
            'source_type': 'sharepoint',
            'source_config': source_config,
            'rag_type': template.rag_type,
            'rag_config': template.rag_config or {}
        }
        
        return config
    
    def create_custom_configuration(self, 
                                  kb_name: str,
                                  selected_libraries: List[str] = None,
                                  selected_lists: List[str] = None,
                                  include_pages: bool = False,
                                  rag_type: str = "mock",
                                  rag_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a custom configuration with specific selections.
        
        Args:
            kb_name: Knowledge base name
            selected_libraries: List of library titles to include
            selected_lists: List of list titles to include  
            include_pages: Whether to include site pages
            rag_type: RAG system type
            rag_config: RAG system configuration
            
        Returns:
            Complete knowledge base configuration
        """
        template = ConfigurationTemplate(
            name="custom",
            description="Custom selection",
            includes_libraries=bool(selected_libraries),
            includes_lists=bool(selected_lists),
            includes_pages=include_pages,
            library_filter=selected_libraries,
            list_filter=selected_lists,
            rag_type=rag_type,
            rag_config=rag_config or {}
        )
        
        return self.create_configuration_from_template(template, kb_name)
    
    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a configuration for common issues.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        required_fields = ['name', 'source_type', 'source_config', 'rag_type']
        for field in required_fields:
            if field not in config:
                issues.append(f"Missing required field: {field}")
        
        # Check source configuration
        if 'source_config' in config:
            source_config = config['source_config']
            
            # Check SharePoint-specific fields
            sp_required = ['site_url', 'site_id']
            for field in sp_required:
                if field not in source_config:
                    issues.append(f"Missing SharePoint field in source_config: {field}")
            
            # Check authentication
            has_service_principal = all(
                field in source_config 
                for field in ['tenant_id', 'client_id', 'client_secret']
            )
            has_user_creds = all(
                field in source_config 
                for field in ['username', 'password']
            )
            
            if not (has_service_principal or has_user_creds):
                issues.append("Missing authentication configuration. Need either service principal or user credentials.")
            
            # Check sources
            if 'sources' not in source_config or not source_config['sources']:
                issues.append("No sources specified in configuration")
        
        # Check RAG configuration based on type
        rag_type = config.get('rag_type')
        if rag_type == 'azure_blob':
            rag_config = config.get('rag_config', {})
            azure_fields = [
                'azure_tenant_id', 'azure_subscription_id', 'azure_client_id',
                'azure_client_secret', 'azure_resource_group_name',
                'azure_storage_account_name', 'azure_storage_container_name'
            ]
            
            # Check if any Azure field is missing (they can be in env vars)
            missing_azure = [field for field in azure_fields if field not in rag_config]
            if missing_azure:
                issues.append(f"Azure Blob RAG type may need these fields (or environment variables): {', '.join(missing_azure)}")
        
        return len(issues) == 0, issues
    
    def export_configuration(self, config: Dict[str, Any], output_path: str,
                           format: str = "json") -> bool:
        """
        Export configuration to file.
        
        Args:
            config: Configuration to export
            output_path: Output file path
            format: Export format ("json" or "yaml")
            
        Returns:
            True if export successful
        """
        try:
            output_file = Path(output_path)
            
            if format.lower() == "json":
                with open(output_file, 'w') as f:
                    json.dump(config, f, indent=2)
            elif format.lower() == "yaml":
                try:
                    import yaml
                    with open(output_file, 'w') as f:
                        yaml.dump(config, f, default_flow_style=False, indent=2)
                except ImportError:
                    logger.error("PyYAML not available for YAML export")
                    return False
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def generate_cli_commands(self, config: Dict[str, Any]) -> List[str]:
        """
        Generate CLI commands to create the knowledge base from configuration.
        
        Args:
            config: Configuration to generate commands for
            
        Returns:
            List of CLI commands
        """
        commands = []
        
        # Create KB command
        kb_name = config['name']
        source_type = config['source_type']
        rag_type = config['rag_type']
        
        # For now, suggest saving config to file first
        config_file = f"{kb_name}-config.json"
        
        commands.append(f"# Save configuration to file:")
        commands.append(f"# (Save the configuration JSON to {config_file})")
        commands.append("")
        
        commands.append(f"# Create knowledge base:")
        commands.append(
            f'document-loader create-kb \\\n'
            f'  --name "{kb_name}" \\\n'
            f'  --source-type "{source_type}" \\\n'
            f'  --source-config @{config_file} \\\n'
            f'  --rag-type "{rag_type}"'
        )
        
        if rag_type == "azure_blob":
            commands.append("")
            commands.append(f"# Initialize Azure resources:")
            commands.append(f'document-loader init-azure --kb-name "{kb_name}"')
        
        commands.append("")
        commands.append(f"# Sync documents:")
        commands.append(f'document-loader sync --kb-name "{kb_name}"')
        
        return commands
    
    def print_configuration_summary(self, config: Dict[str, Any]) -> str:
        """
        Generate a formatted summary of the configuration.
        
        Args:
            config: Configuration to summarize
            
        Returns:
            Formatted summary string
        """
        source_config = config.get('source_config', {})
        sources = source_config.get('sources', [])
        
        summary = f"""
Configuration Summary: {config['name']}
{'=' * (len(config['name']) + 23)}

Knowledge Base:
  Name: {config['name']}
  Description: {config.get('description', 'N/A')}
  
SharePoint Site:
  Name: {source_config.get('site_name', 'N/A')}
  URL: {source_config.get('site_url', 'N/A')}
  Site ID: {source_config.get('site_id', 'N/A')}
  
RAG System:
  Type: {config['rag_type']}
  
Sources ({len(sources)}):"""
        
        for source in sources:
            source_type = source.get('type', 'unknown')
            title = source.get('title', 'N/A')
            item_count = source.get('item_count', 0)
            summary += f"\n  - {title} ({source_type}, {item_count} items)"
        
        # Validation
        is_valid, issues = self.validate_configuration(config)
        if is_valid:
            summary += "\n\nValidation: ✓ Configuration is valid"
        else:
            summary += f"\n\nValidation: ⚠ {len(issues)} issues found:"
            for issue in issues:
                summary += f"\n  - {issue}"
        
        return summary