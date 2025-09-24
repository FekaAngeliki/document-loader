"""
Configuration File Manager for Multi-Source Knowledge Bases

This module provides functionality for admins to upload, manage, and deploy
configuration files stored in PostgreSQL.
"""

import asyncio
import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ..data.database import Database, DatabaseConfig


class ConfigManager:
    """Manages knowledge base configuration files in PostgreSQL."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def _calculate_file_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of config content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _validate_config_structure(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate the config file structure."""
        try:
            # Required top-level fields
            required_fields = ['name', 'rag_type', 'sources']
            for field in required_fields:
                if field not in config:
                    return False, f"Missing required field: {field}"
            
            # Validate sources array
            if not isinstance(config['sources'], list):
                return False, "Field 'sources' must be an array"
            
            if len(config['sources']) == 0:
                return False, "At least one source is required"
            
            # Validate each source
            for i, source in enumerate(config['sources']):
                required_source_fields = ['source_id', 'source_type', 'source_config']
                for field in required_source_fields:
                    if field not in source:
                        return False, f"Source {i}: Missing required field '{field}'"
                
                # Validate source_id format
                source_id = source['source_id']
                if not isinstance(source_id, str) or not source_id.replace('_', '').replace('-', '').isalnum():
                    return False, f"Source {i}: Invalid source_id format. Use alphanumeric characters, hyphens, and underscores only."
            
            # Check for duplicate source IDs
            source_ids = [s['source_id'] for s in config['sources']]
            if len(source_ids) != len(set(source_ids)):
                return False, "Duplicate source_id values found"
            
            return True, "Configuration is valid"
            
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
    
    async def upload_config_file(self, 
                                file_path: str, 
                                name: Optional[str] = None,
                                description: Optional[str] = None,
                                created_by: str = "admin") -> Dict[str, Any]:
        """
        Upload a configuration file to PostgreSQL.
        
        Args:
            file_path: Path to the JSON config file
            name: Optional name override (uses filename if not provided)
            description: Optional description
            created_by: Username of the admin uploading the file
            
        Returns:
            Dict with upload results and config ID
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Read and parse config file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                config = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise Exception(f"Error reading config file: {e}")
        
        # Use provided name or derive from filename
        config_name = name or file_path.stem
        
        # Use description from config or provided description
        config_description = description or config.get('description', f"Config uploaded from {file_path.name}")
        
        # Validate configuration structure
        is_valid, validation_message = self._validate_config_structure(config)
        if not is_valid:
            raise ValueError(f"Configuration validation failed: {validation_message}")
        
        # Calculate file hash
        file_hash = self._calculate_file_hash(content)
        
        # Check if config with same name exists
        existing_query = "SELECT id, version, file_hash FROM kb_config_files WHERE name = $1 ORDER BY version DESC LIMIT 1"
        existing = await self.db.fetchrow(existing_query, config_name)
        
        if existing:
            # Check if content is the same
            if existing['file_hash'] == file_hash:
                return {
                    "status": "unchanged",
                    "message": f"Configuration '{config_name}' already exists with identical content",
                    "config_id": existing['id'],
                    "version": existing['version']
                }
            
            # Create new version
            new_version = existing['version'] + 1
            
            # Archive the old version
            archive_query = "UPDATE kb_config_files SET status = 'archived' WHERE name = $1 AND version < $2"
            await self.db.execute(archive_query, config_name, new_version)
        else:
            new_version = 1
        
        # Insert new configuration
        insert_query = """
        INSERT INTO kb_config_files 
        (name, description, config_content, file_path, file_hash, version, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, version
        """
        
        result = await self.db.fetchrow(
            insert_query,
            config_name,
            config_description,
            json.dumps(config),
            str(file_path),
            file_hash,
            new_version,
            created_by
        )
        
        return {
            "status": "uploaded" if new_version == 1 else "updated",
            "message": f"Configuration '{config_name}' version {new_version} uploaded successfully",
            "config_id": result['id'],
            "version": result['version'],
            "source_count": len(config['sources']),
            "rag_type": config['rag_type']
        }
    
    async def list_configs(self, status: str = "active") -> List[Dict[str, Any]]:
        """List all configuration files with given status."""
        query = """
        SELECT 
            name, description, status, version, created_by, created_at,
            last_deployed_at, deployment_count,
            jsonb_array_length(config_content->'sources') as source_count,
            config_content->>'rag_type' as rag_type
        FROM kb_config_files 
        WHERE status = $1
        ORDER BY updated_at DESC
        """
        
        rows = await self.db.fetch(query, status)
        return [dict(row) for row in rows]
    
    async def get_config(self, name: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get a specific configuration by name and optionally version."""
        if version:
            query = """
            SELECT id, name, description, config_content, version, status, 
                   created_by, created_at, file_hash
            FROM kb_config_files 
            WHERE name = $1 AND version = $2
            """
            result = await self.db.fetchrow(query, name, version)
        else:
            query = """
            SELECT id, name, description, config_content, version, status,
                   created_by, created_at, file_hash
            FROM kb_config_files 
            WHERE name = $1 AND status = 'active'
            ORDER BY version DESC LIMIT 1
            """
            result = await self.db.fetchrow(query, name)
        
        if result:
            config_dict = dict(result)
            config_dict['config_content'] = json.loads(result['config_content'])
            return config_dict
        
        return None
    
    async def delete_config(self, name: str, version: Optional[int] = None) -> bool:
        """Delete a configuration (or mark as archived)."""
        if version:
            query = "UPDATE kb_config_files SET status = 'archived' WHERE name = $1 AND version = $2"
            result = await self.db.execute(query, name, version)
        else:
            query = "UPDATE kb_config_files SET status = 'archived' WHERE name = $1"
            result = await self.db.execute(query, name)
        
        return result == "UPDATE 1" or "UPDATE" in result
    
    async def mark_deployed(self, config_id: int) -> bool:
        """Mark a configuration as deployed and increment deployment count."""
        query = """
        UPDATE kb_config_files 
        SET last_deployed_at = NOW(), deployment_count = deployment_count + 1
        WHERE id = $1
        """
        result = await self.db.execute(query, config_id)
        return result == "UPDATE 1" or "UPDATE" in result
    
    async def export_config(self, name: str, output_path: str, version: Optional[int] = None) -> bool:
        """Export a configuration to a file."""
        config = await self.get_config(name, version)
        if not config:
            return False
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config['config_content'], f, indent=2, ensure_ascii=False)
        
        return True
    
    async def get_config_summary(self) -> Dict[str, Any]:
        """Get summary statistics of stored configurations."""
        query = """
        SELECT 
            COUNT(*) as total_configs,
            COUNT(*) FILTER (WHERE status = 'active') as active_configs,
            COUNT(*) FILTER (WHERE status = 'archived') as archived_configs,
            COUNT(*) FILTER (WHERE last_deployed_at IS NOT NULL) as deployed_configs,
            AVG(deployment_count) as avg_deployments,
            MAX(created_at) as latest_upload
        FROM kb_config_files
        """
        
        result = await self.db.fetchrow(query)
        return dict(result) if result else {}


async def create_config_manager() -> ConfigManager:
    """Factory function to create a ConfigManager with database connection."""
    from ..data.database import Database, DatabaseConfig
    
    config = DatabaseConfig()
    db = Database(config)
    await db.connect()
    
    return ConfigManager(db)