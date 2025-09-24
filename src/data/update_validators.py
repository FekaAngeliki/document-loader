"""
Validation logic for knowledge base update operations.

Enforces immutability rules for RAG configuration while allowing source updates.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .validators import ValidationResult, ValidationError
from .models import KnowledgeBase
from .repository import Repository


class KnowledgeBaseUpdateValidator:
    """Validator for knowledge base update operations."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
    
    async def validate_kb_update(self, kb_name: str, updates: Dict[str, Any]) -> ValidationResult:
        """
        Validate knowledge base update operation.
        
        Args:
            kb_name: Name of the knowledge base to update
            updates: Dictionary of fields to update
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Check if KB exists
        existing_kb = await self.repository.get_knowledge_base_by_name(kb_name)
        if not existing_kb:
            result.add_error('kb_name', f"Knowledge base '{kb_name}' not found")
            return result
        
        # Validate immutability rules
        await self._validate_immutability_rules(updates, result)
        
        # Validate allowed updates
        await self._validate_source_updates(updates, result)
        
        return result
    
    async def _validate_immutability_rules(self, updates: Dict[str, Any], result: ValidationResult):
        """Validate that immutable fields are not being updated."""
        immutable_fields = {
            'rag_type': 'RAG type is immutable once set. Delete and recreate the knowledge base to change RAG type.',
            'rag_config': 'RAG configuration is immutable once set. Delete and recreate the knowledge base to change RAG configuration.',
            'name': 'Knowledge base name cannot be changed.',
            'id': 'Knowledge base ID cannot be changed.'
        }
        
        for field, message in immutable_fields.items():
            if field in updates:
                result.add_error(field, message)
    
    async def _validate_source_updates(self, updates: Dict[str, Any], result: ValidationResult):
        """Validate source-related updates."""
        
        # Validate source type if provided
        if 'source_type' in updates:
            source_type = updates['source_type']
            try:
                valid_source_types = await self.repository.get_all_source_types()
                valid_names = {st.name for st in valid_source_types}
                
                if source_type not in valid_names:
                    result.add_error('source_type', 
                                   f"Invalid source type '{source_type}'. Available types: {', '.join(valid_names)}")
            except Exception as e:
                result.add_warning('source_type', f"Could not validate source type: {str(e)}")
        
        # Validate source configuration if provided
        if 'source_config' in updates:
            source_config = updates['source_config']
            if not isinstance(source_config, dict):
                result.add_error('source_config', "Source configuration must be a dictionary")
            else:
                # Basic validation based on source type
                source_type = updates.get('source_type')
                if source_type:
                    self._validate_source_config_for_type(source_type, source_config, result)


def _validate_source_config_for_type(self, source_type: str, config: Dict[str, Any], result: ValidationResult):
    """Validate source configuration based on source type."""
    
    if source_type == 'file_system':
        if 'base_path' not in config:
            result.add_error('source_config.base_path', "base_path is required for file system sources")
    
    elif source_type in ['sharepoint', 'enterprise_sharepoint']:
        required_fields = ['tenant_id', 'client_id', 'client_secret', 'site_url']
        for field in required_fields:
            if field not in config:
                result.add_error(f'source_config.{field}', f"{field} is required for SharePoint sources")
    
    elif source_type == 'onedrive':
        required_fields = ['tenant_id', 'client_id', 'client_secret']
        for field in required_fields:
            if field not in config:
                result.add_error(f'source_config.{field}', f"{field} is required for OneDrive sources")


async def validate_kb_update(kb_name: str, updates: Dict[str, Any], repository: Repository) -> ValidationResult:
    """
    Convenience function to validate knowledge base updates.
    
    Args:
        kb_name: Name of the knowledge base to update
        updates: Dictionary of fields to update
        repository: Repository instance for database operations
        
    Returns:
        ValidationResult with errors and warnings
    """
    validator = KnowledgeBaseUpdateValidator(repository)
    return await validator.validate_kb_update(kb_name, updates)