#!/usr/bin/env python3
"""
Script to update the database with new RAG types.
Run this after adding new RAG implementations.
"""
import asyncio
import logging
import os
from pathlib import Path

# Add the parent directory to the Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.data.database import Database, DatabaseConfig
from src.data.repository import Repository

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SQL to insert new RAG types
INSERT_RAG_TYPES_SQL = """
    -- Insert FileSystemStorage RAG type
    INSERT INTO rag_type (name, class_name, config_schema)
    VALUES ('file_system_storage', 'src.implementations.file_system_storage.FileSystemStorage',
           '{"type": "object", "properties": {"storage_path": {"type": "string"}, "create_dirs": {"type": "boolean"}, "preserve_structure": {"type": "boolean"}, "metadata_format": {"type": "string", "enum": ["json", "yaml"]}}, "required": ["storage_path"]}')
    ON CONFLICT (name) DO UPDATE SET 
        class_name = EXCLUDED.class_name,
        config_schema = EXCLUDED.config_schema;
    
    -- Insert AzureBlob RAG type
    INSERT INTO rag_type (name, class_name, config_schema)
    VALUES ('azure_blob', 'src.implementations.azure_blob_rag_system.AzureBlobRAGSystem',
           '{"type": "object", "properties": {"connection_string": {"type": "string"}, "container_name": {"type": "string"}, "index_name": {"type": "string"}, "endpoint": {"type": "string"}, "api_key": {"type": "string"}}, "required": ["connection_string", "container_name"]}')
    ON CONFLICT (name) DO UPDATE SET 
        class_name = EXCLUDED.class_name,
        config_schema = EXCLUDED.config_schema;
"""

async def update_rag_types():
    """Update the database with new RAG types."""
    config = DatabaseConfig()
    db = Database(config)
    
    try:
        await db.connect()
        logger.info("Connected to database")
        
        # Execute the insert/update statements
        await db.execute(INSERT_RAG_TYPES_SQL)
        logger.info("Successfully updated RAG types")
        
        # Query to verify the updates
        repository = Repository(db)
        rag_types = await repository.get_rag_types()
        
        logger.info("Current RAG types in database:")
        for rag_type in rag_types:
            logger.info(f"  - {rag_type['name']}: {rag_type['class_name']}")
            
    except Exception as e:
        logger.error(f"Error updating RAG types: {e}")
        raise
    finally:
        await db.disconnect()
        logger.info("Disconnected from database")

if __name__ == "__main__":
    print("Updating RAG types in database...")
    asyncio.run(update_rag_types())
    print("Done!")