"""
Config Asset Manager for PostgreSQL Storage

Manages configuration files stored as assets in PostgreSQL database.
Provides upload, download, validation, and management capabilities.
"""

import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ConfigAsset:
    """Represents a configuration asset."""
    id: Optional[int]
    name: str
    description: Optional[str]
    config_type: str
    config_data: Dict[str, Any]
    version: int
    is_active: bool
    tags: List[str]
    file_size: Optional[int]
    file_hash: Optional[str]
    original_filename: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str]
    is_valid: bool
    validation_errors: Optional[Dict[str, Any]]
    last_used_at: Optional[datetime]
    usage_count: int

class ConfigAssetManager:
    """Manages configuration assets in PostgreSQL."""
    
    def __init__(self, database):
        self.db = database
    
    async def upload_config_file(self, 
                                file_path: str, 
                                name: str,
                                description: Optional[str] = None,
                                tags: Optional[List[str]] = None,
                                config_type: str = "multi_source") -> int:
        """Upload a configuration file to PostgreSQL storage."""
        try:
            # Read and validate the config file
            config_path = Path(file_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {file_path}")
            
            # Read file content
            config_content = config_path.read_text(encoding='utf-8')
            config_data = json.loads(config_content)
            
            # Calculate file metadata
            file_size = len(config_content.encode('utf-8'))
            file_hash = hashlib.sha256(config_content.encode('utf-8')).hexdigest()
            
            # Validate config structure
            is_valid, validation_errors = await self._validate_config(config_data, config_type)
            
            # Insert into database
            query = """
                INSERT INTO config_assets 
                (name, description, config_type, config_data, tags, file_size, file_hash, 
                 original_filename, is_valid, validation_errors, last_validated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                RETURNING id
            """
            
            config_id = await self.db.fetchval(
                query,
                name,
                description or f"Config uploaded from {config_path.name}",
                config_type,
                json.dumps(config_data),
                tags or [],
                file_size,
                file_hash,
                config_path.name,
                is_valid,
                json.dumps(validation_errors) if validation_errors else None
            )
            
            logger.info(f"Uploaded config '{name}' with ID {config_id} (valid: {is_valid})")
            return config_id
            
        except Exception as e:
            logger.error(f"Failed to upload config file {file_path}: {e}")
            raise
    
    async def get_config_by_name(self, name: str) -> Optional[ConfigAsset]:
        """Get a configuration by name."""
        try:
            query = """
                SELECT * FROM config_assets 
                WHERE name = $1 AND is_active = true
                ORDER BY version DESC
                LIMIT 1
            """
            
            row = await self.db.fetchrow(query, name)
            if not row:
                return None
            
            # Track usage
            await self.db.execute("SELECT track_config_usage($1)", name)
            
            return self._row_to_config_asset(row)
            
        except Exception as e:
            logger.error(f"Failed to get config '{name}': {e}")
            return None
    
    async def list_configs(self, 
                          config_type: Optional[str] = None,
                          tags: Optional[List[str]] = None,
                          active_only: bool = True) -> List[ConfigAsset]:
        """List all configuration assets with optional filtering."""
        try:
            conditions = []
            params = []
            param_count = 0
            
            if active_only:
                conditions.append("is_active = true")
            
            if config_type:
                param_count += 1
                conditions.append(f"config_type = ${param_count}")
                params.append(config_type)
            
            if tags:
                param_count += 1
                conditions.append(f"tags && ${param_count}")
                params.append(tags)
            
            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
                SELECT * FROM config_assets
                {where_clause}
                ORDER BY created_at DESC
            """
            
            rows = await self.db.fetch(query, *params)
            return [self._row_to_config_asset(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list configs: {e}")
            return []
    
    async def delete_config(self, name: str, soft_delete: bool = True) -> bool:
        """Delete a configuration (soft delete by default)."""
        try:
            if soft_delete:
                query = """
                    UPDATE config_assets 
                    SET is_active = false, updated_at = NOW()
                    WHERE name = $1
                """
            else:
                query = "DELETE FROM config_assets WHERE name = $1"
            
            result = await self.db.execute(query, name)
            success = "UPDATE 1" in result or "DELETE 1" in result
            
            if success:
                action = "deactivated" if soft_delete else "deleted"
                logger.info(f"Config '{name}' {action} successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete config '{name}': {e}")
            return False
    
    async def export_config(self, name: str, output_path: str) -> bool:
        """Export a configuration to a local file."""
        try:
            config = await self.get_config_by_name(name)
            if not config:
                logger.error(f"Config '{name}' not found")
                return False
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write config data to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config.config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported config '{name}' to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export config '{name}': {e}")
            return False
    
    async def get_config_stats(self) -> Dict[str, Any]:
        """Get statistics about stored configurations."""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_configs,
                    COUNT(CASE WHEN is_active THEN 1 END) as active_configs,
                    COUNT(CASE WHEN is_valid THEN 1 END) as valid_configs,
                    COUNT(DISTINCT config_type) as config_types,
                    AVG(file_size) as avg_file_size,
                    MAX(created_at) as latest_upload,
                    SUM(usage_count) as total_usage
                FROM config_assets
            """
            
            row = await self.db.fetchrow(query)
            
            # Get config types breakdown
            type_query = """
                SELECT config_type, COUNT(*) as count
                FROM config_assets 
                WHERE is_active = true
                GROUP BY config_type
                ORDER BY count DESC
            """
            
            type_rows = await self.db.fetch(type_query)
            type_breakdown = {row['config_type']: row['count'] for row in type_rows}
            
            return {
                'total_configs': row['total_configs'],
                'active_configs': row['active_configs'],
                'valid_configs': row['valid_configs'],
                'config_types': row['config_types'],
                'avg_file_size_bytes': int(row['avg_file_size']) if row['avg_file_size'] else 0,
                'latest_upload': row['latest_upload'],
                'total_usage': row['total_usage'] or 0,
                'type_breakdown': type_breakdown
            }
            
        except Exception as e:
            logger.error(f"Failed to get config stats: {e}")
            return {}
    
    async def _validate_config(self, config_data: Dict[str, Any], config_type: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate configuration data structure."""
        errors = {}
        
        try:
            if config_type == "multi_source":
                # Validate multi-source config structure
                if 'name' not in config_data:
                    errors['name'] = "Missing required field: name"
                
                if 'sources' not in config_data:
                    errors['sources'] = "Missing required field: sources"
                elif not isinstance(config_data['sources'], list):
                    errors['sources'] = "Sources must be a list"
                elif len(config_data['sources']) == 0:
                    errors['sources'] = "At least one source is required"
                
                if 'rag_type' not in config_data:
                    errors['rag_type'] = "Missing required field: rag_type"
                
                if 'rag_config' not in config_data:
                    errors['rag_config'] = "Missing required field: rag_config"
                
                # Validate each source
                for i, source in enumerate(config_data.get('sources', [])):
                    if not isinstance(source, dict):
                        errors[f'sources[{i}]'] = "Source must be an object"
                        continue
                    
                    if 'source_id' not in source:
                        errors[f'sources[{i}].source_id'] = "Missing source_id"
                    
                    if 'source_type' not in source:
                        errors[f'sources[{i}].source_type'] = "Missing source_type"
                    
                    if 'source_config' not in source:
                        errors[f'sources[{i}].source_config'] = "Missing source_config"
            
            is_valid = len(errors) == 0
            return is_valid, errors if errors else None
            
        except Exception as e:
            logger.error(f"Config validation error: {e}")
            return False, {"validation_exception": str(e)}
    
    def _row_to_config_asset(self, row) -> ConfigAsset:
        """Convert database row to ConfigAsset object."""
        # Handle config_data - it might be stored as JSON string
        config_data = row['config_data']
        if isinstance(config_data, str):
            config_data = json.loads(config_data)
        
        # Handle validation_errors - it might be stored as JSON string
        validation_errors = row.get('validation_errors')
        if isinstance(validation_errors, str):
            validation_errors = json.loads(validation_errors)
        
        return ConfigAsset(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            config_type=row['config_type'],
            config_data=config_data,
            version=row['version'],
            is_active=row['is_active'],
            tags=row['tags'] or [],
            file_size=row['file_size'],
            file_hash=row['file_hash'],
            original_filename=row['original_filename'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by=row.get('created_by'),
            is_valid=row['is_valid'],
            validation_errors=validation_errors,
            last_used_at=row.get('last_used_at'),
            usage_count=row.get('usage_count', 0)
        )