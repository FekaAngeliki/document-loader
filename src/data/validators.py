"""
Validation logic for knowledge base and database operations.

Provides comprehensive validation for create-kb and create-db operations
to ensure data integrity and prevent runtime errors.
"""

import re
import json
import asyncio
import psycopg
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .models import KnowledgeBase, SourceType, RagType
from .database import Database, DatabaseConfig
from .repository import Repository


@dataclass
class ValidationError:
    """Represents a validation error with field and message."""
    field: str
    message: str
    severity: str = "error"  # error, warning


class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
    
    def add_error(self, field: str, message: str):
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, "error"))
    
    def add_warning(self, field: str, message: str):
        """Add a validation warning."""
        self.warnings.append(ValidationError(field, message, "warning"))
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0


class KnowledgeBaseValidator:
    """Validator for knowledge base creation."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        
    async def validate_create_kb(self, kb_config: Dict[str, Any]) -> ValidationResult:
        """
        Comprehensive validation for knowledge base creation.
        
        Args:
            kb_config: Knowledge base configuration dictionary
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Basic structure validation
        await self._validate_basic_structure(kb_config, result)
        
        if not result.is_valid:
            return result  # Don't proceed if basic structure is invalid
        
        # Advanced validations
        await self._validate_name_uniqueness(kb_config.get('name'), result)
        await self._validate_source_types(kb_config.get('sources', []), result)
        await self._validate_rag_type(kb_config.get('rag_type'), result)
        await self._validate_source_configurations(kb_config.get('sources', []), result)
        await self._validate_rag_configuration(kb_config.get('rag_type'), kb_config.get('rag_config', {}), result)
        
        return result
    
    async def _validate_basic_structure(self, kb_config: Dict[str, Any], result: ValidationResult):
        """Validate basic structure and required fields."""
        required_fields = ['name', 'rag_type', 'sources']
        
        for field in required_fields:
            if field not in kb_config:
                result.add_error(field, f"Required field '{field}' is missing")
            elif not kb_config[field]:
                result.add_error(field, f"Field '{field}' cannot be empty")
        
        # Validate name format
        name = kb_config.get('name', '')
        if name:
            if not re.match(r'^[a-zA-Z0-9_-]+$', name):
                result.add_error('name', "Knowledge base name can only contain letters, numbers, hyphens, and underscores")
            
            if len(name) < 3:
                result.add_error('name', "Knowledge base name must be at least 3 characters long")
            
            if len(name) > 64:
                result.add_error('name', "Knowledge base name cannot exceed 64 characters")
        
        # Validate sources is a list
        sources = kb_config.get('sources')
        if sources is not None and not isinstance(sources, list):
            result.add_error('sources', "Sources must be a list")
        elif isinstance(sources, list) and len(sources) == 0:
            result.add_error('sources', "At least one source must be defined")
    
    async def _validate_name_uniqueness(self, name: str, result: ValidationResult):
        """Check if knowledge base name already exists."""
        if not name:
            return
            
        try:
            existing_kb = await self.repository.get_knowledge_base_by_name(name)
            if existing_kb:
                result.add_error('name', f"Knowledge base with name '{name}' already exists. Knowledge bases are immutable - delete the existing one first if you need to change the configuration.")
        except Exception as e:
            result.add_warning('name', f"Could not verify name uniqueness: {str(e)}")
    
    async def _validate_source_types(self, sources: List[Dict[str, Any]], result: ValidationResult):
        """Validate that all source types exist in the registry."""
        if not sources:
            return
            
        try:
            registered_types = await self.repository.get_all_source_types()
            registered_names = {st.name for st in registered_types}
            
            for i, source in enumerate(sources):
                source_type = source.get('source_type')
                if not source_type:
                    result.add_error(f'sources[{i}].source_type', "Source type is required")
                elif source_type not in registered_names:
                    result.add_error(f'sources[{i}].source_type', 
                                   f"Unknown source type '{source_type}'. Available types: {', '.join(registered_names)}")
        except Exception as e:
            result.add_warning('sources', f"Could not verify source types: {str(e)}")
    
    async def _validate_rag_type(self, rag_type: str, result: ValidationResult):
        """Validate that RAG type exists in the registry."""
        if not rag_type:
            return
            
        try:
            registered_types = await self.repository.get_all_rag_types()
            registered_names = {rt.name for rt in registered_types}
            
            if rag_type not in registered_names:
                result.add_error('rag_type', 
                               f"Unknown RAG type '{rag_type}'. Available types: {', '.join(registered_names)}")
        except Exception as e:
            result.add_warning('rag_type', f"Could not verify RAG type: {str(e)}")
    
    async def _validate_source_configurations(self, sources: List[Dict[str, Any]], result: ValidationResult):
        """Validate source configurations against their schemas."""
        if not sources:
            return
            
        for i, source in enumerate(sources):
            # Validate required source fields
            if 'source_config' not in source:
                result.add_error(f'sources[{i}].source_config', "Source configuration is required")
                continue
            
            source_type = source.get('source_type')
            source_config = source.get('source_config', {})
            
            # Basic validation for common source types
            if source_type == 'file_system':
                self._validate_filesystem_config(source_config, i, result)
            elif source_type in ['sharepoint', 'enterprise_sharepoint']:
                self._validate_sharepoint_config(source_config, i, result)
            elif source_type == 'onedrive':
                self._validate_onedrive_config(source_config, i, result)
    
    def _validate_filesystem_config(self, config: Dict[str, Any], index: int, result: ValidationResult):
        """Validate file system source configuration."""
        if 'base_path' not in config:
            result.add_error(f'sources[{index}].source_config.base_path', "Base path is required for file system sources")
        else:
            base_path = Path(config['base_path'])
            if not base_path.exists():
                result.add_warning(f'sources[{index}].source_config.base_path', 
                                 f"Base path '{base_path}' does not exist")
            elif not base_path.is_dir():
                result.add_error(f'sources[{index}].source_config.base_path', 
                               f"Base path '{base_path}' is not a directory")
    
    def _validate_sharepoint_config(self, config: Dict[str, Any], index: int, result: ValidationResult):
        """Validate SharePoint source configuration."""
        required_fields = ['tenant_id', 'client_id', 'client_secret', 'site_url']
        
        for field in required_fields:
            if field not in config or not config[field]:
                result.add_error(f'sources[{index}].source_config.{field}', 
                               f"Field '{field}' is required for SharePoint sources")
        
        # Validate site URL format
        site_url = config.get('site_url', '')
        if site_url and not site_url.startswith('https://'):
            result.add_error(f'sources[{index}].source_config.site_url', 
                           "SharePoint site URL must start with 'https://'")
    
    def _validate_onedrive_config(self, config: Dict[str, Any], index: int, result: ValidationResult):
        """Validate OneDrive source configuration."""
        required_fields = ['tenant_id', 'client_id', 'client_secret']
        
        for field in required_fields:
            if field not in config or not config[field]:
                result.add_error(f'sources[{index}].source_config.{field}', 
                               f"Field '{field}' is required for OneDrive sources")
    
    async def _validate_rag_configuration(self, rag_type: str, rag_config: Dict[str, Any], result: ValidationResult):
        """Validate RAG configuration against its schema."""
        if not rag_type:
            return
            
        # Basic validation for common RAG types
        if rag_type == 'azure_blob':
            self._validate_azure_blob_config(rag_config, result)
        elif rag_type == 'file_system_storage':
            self._validate_file_storage_config(rag_config, result)
        # mock RAG type doesn't need validation
    
    def _validate_azure_blob_config(self, config: Dict[str, Any], result: ValidationResult):
        """Validate Azure Blob Storage RAG configuration."""
        required_fields = ['connection_string', 'container_name']
        
        for field in required_fields:
            if field not in config or not config[field]:
                result.add_error(f'rag_config.{field}', 
                               f"Field '{field}' is required for Azure Blob Storage")
    
    def _validate_file_storage_config(self, config: Dict[str, Any], result: ValidationResult):
        """Validate file system storage RAG configuration."""
        # Check for either storage_path or root_path (both supported by implementation)
        if 'storage_path' not in config and 'root_path' not in config:
            result.add_error('rag_config.storage_path', "storage_path or root_path is required for file system storage")
        else:
            storage_path = Path(config.get('storage_path') or config.get('root_path'))
            if not storage_path.exists():
                result.add_warning('rag_config.storage_path', 
                                 f"RAG storage path '{storage_path}' does not exist")


class DatabaseValidator:
    """Validator for database operations."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
    
    async def validate_create_db(self, database_name: str) -> ValidationResult:
        """
        Validate database creation operation.
        
        Args:
            database_name: Name of the database to create
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Basic name validation
        self._validate_database_name(database_name, result)
        
        if not result.is_valid:
            return result
        
        # Check connectivity and permissions
        await self._validate_database_connectivity(result)
        await self._validate_database_existence(database_name, result)
        await self._validate_create_permissions(result)
        
        return result
    
    def _validate_database_name(self, name: str, result: ValidationResult):
        """Validate database name format."""
        if not name:
            result.add_error('database_name', "Database name is required")
            return
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            result.add_error('database_name', 
                           "Database name must start with a letter and contain only letters, numbers, and underscores")
        
        if len(name) > 63:
            result.add_error('database_name', "Database name cannot exceed 63 characters")
        
        # Check for reserved names
        reserved_names = {'postgres', 'template0', 'template1'}
        if name.lower() in reserved_names:
            result.add_error('database_name', f"'{name}' is a reserved database name")
    
    async def _validate_database_connectivity(self, result: ValidationResult):
        """Test database server connectivity."""
        try:
            conn = await psycopg.AsyncConnection.connect(
                f"postgresql://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/postgres"
            )
            await conn.close()
        except psycopg.OperationalError as e:
            if "authentication failed" in str(e).lower():
                result.add_error('credentials', "Invalid database credentials")
            else:
                result.add_error('connection', "Cannot connect to database server")
        except Exception as e:
            result.add_error('connection', f"Database connection failed: {str(e)}")
    
    async def _validate_database_existence(self, database_name: str, result: ValidationResult):
        """Check if database already exists."""
        try:
            conn = await psycopg.AsyncConnection.connect(
                f"postgresql://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/postgres"
            )
            
            async with conn.cursor() as cursor:
                query = "SELECT 1 FROM pg_database WHERE datname = %s"
                await cursor.execute(query, (database_name,))
                exists = await cursor.fetchone()
            
            if exists:
                result.add_error('database_name', f"Database '{database_name}' already exists")
            
            await conn.close()
        except Exception as e:
            result.add_warning('existence_check', f"Could not verify database existence: {str(e)}")
    
    async def _validate_create_permissions(self, result: ValidationResult):
        """Check if user has CREATE DATABASE permissions."""
        try:
            conn = await psycopg.AsyncConnection.connect(
                f"postgresql://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/postgres"
            )
            
            # Check if user has createdb privilege
            async with conn.cursor() as cursor:
                query = "SELECT rolcreatedb FROM pg_roles WHERE rolname = %s"
                await cursor.execute(query, (self.config.user,))
                result_row = await cursor.fetchone()
                can_create = result_row[0] if result_row else False
            
            if not can_create:
                result.add_error('permissions', f"User '{self.config.user}' does not have CREATE DATABASE privileges")
            
            await conn.close()
        except Exception as e:
            result.add_warning('permissions_check', f"Could not verify create permissions: {str(e)}")


async def validate_kb_creation(kb_config: Dict[str, Any], repository: Repository) -> ValidationResult:
    """
    Convenience function to validate knowledge base creation.
    
    Args:
        kb_config: Knowledge base configuration dictionary
        repository: Repository instance for database operations
        
    Returns:
        ValidationResult with errors and warnings
    """
    validator = KnowledgeBaseValidator(repository)
    return await validator.validate_create_kb(kb_config)


async def validate_db_creation(database_name: str, config: DatabaseConfig) -> ValidationResult:
    """
    Convenience function to validate database creation.
    
    Args:
        database_name: Name of the database to create
        config: Database configuration
        
    Returns:
        ValidationResult with errors and warnings
    """
    validator = DatabaseValidator(config)
    return await validator.validate_create_db(database_name)