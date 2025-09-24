"""
Database migration script to update Azure Blob RAG configurations
to the new comprehensive configuration structure
"""
import asyncio
import logging
import json
from pathlib import Path
import sys

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.implementations.azure_blob_rag_config import (
    AzureBlobRAGConfig,
    AzureBlobConfig,
    AzureServicePrincipalAuth,
    AzureResourceConfig,
    AzureAuthMethod
)
from src.data.database import get_database_config, create_connection_pool
from src.data.repository import Repository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_azure_blob_configs():
    """Migrate existing Azure Blob RAG configurations to new format"""
    db_config = get_database_config()
    pool = await create_connection_pool(db_config)
    
    try:
        async with pool.acquire() as connection:
            # Find all Azure Blob RAG type entries
            rows = await connection.fetch("""
                SELECT id, name, config
                FROM rag_type
                WHERE name LIKE '%azure%blob%'
            """)
            
            for row in rows:
                rag_type_id = row['id']
                rag_type_name = row['name']
                old_config = row['config']
                
                logger.info(f"Migrating configuration for: {rag_type_name}")
                
                # Convert old config to new format
                new_config = convert_config(old_config)
                
                # Update the database
                await connection.execute("""
                    UPDATE rag_type
                    SET config = $1
                    WHERE id = $2
                """, new_config, rag_type_id)
                
                logger.info(f"Updated configuration for {rag_type_name}")
            
            # Find and update knowledge_base entries using Azure Blob
            kb_rows = await connection.fetch("""
                SELECT kb.id, kb.name, kb.rag_config
                FROM knowledge_base kb
                JOIN rag_type rt ON kb.rag_type = rt.name
                WHERE rt.name LIKE '%azure%blob%'
            """)
            
            for kb_row in kb_rows:
                kb_id = kb_row['id']
                kb_name = kb_row['name']
                old_rag_config = kb_row['rag_config']
                
                logger.info(f"Migrating knowledge base: {kb_name}")
                
                # Convert to new format
                new_rag_config = convert_config(old_rag_config)
                
                # Update the knowledge base
                await connection.execute("""
                    UPDATE knowledge_base
                    SET rag_config = $1
                    WHERE id = $2
                """, new_rag_config, kb_id)
                
                logger.info(f"Updated knowledge base {kb_name}")
                
            logger.info("Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        await pool.close()

def convert_config(old_config):
    """Convert old configuration format to new comprehensive format"""
    if not old_config:
        return create_default_config()
    
    # Parse the old config
    if isinstance(old_config, str):
        old_config = json.loads(old_config)
    
    # Create new config structure
    new_config = {
        "auth_method": "service_principal"  # Default to service principal
    }
    
    # Map old fields to new structure
    if "azure_tenant_id" in old_config:
        new_config["service_principal"] = {
            "tenant_id": old_config.get("azure_tenant_id"),
            "subscription_id": old_config.get("azure_subscription_id"),
            "client_id": old_config.get("azure_client_id"),
            "client_secret": old_config.get("azure_client_secret")
        }
    
    # Map storage configuration
    if "azure_storage_account_name" in old_config:
        new_config["blob_config"] = {
            "storage_account_name": old_config.get("azure_storage_account_name"),
            "container_name": old_config.get("azure_storage_container_name", "documents")
        }
    elif "storage_account_name" in old_config:
        new_config["blob_config"] = {
            "storage_account_name": old_config.get("storage_account_name"),
            "container_name": old_config.get("container_name", "documents")
        }
    
    # Map resource configuration
    if "azure_resource_group_name" in old_config:
        new_config["resource_config"] = {
            "resource_group_name": old_config.get("azure_resource_group_name"),
            "location": old_config.get("azure_resource_location", "eastus")
        }
    elif "resource_group_name" in old_config:
        new_config["resource_config"] = {
            "resource_group_name": old_config.get("resource_group_name"),
            "location": old_config.get("location", "eastus")
        }
    
    # Check for connection string
    if "connection_string" in old_config:
        new_config["auth_method"] = "connection_string"
        new_config["connection_string"] = old_config["connection_string"]
    
    # Add any Azure Search configuration
    if any(key in old_config for key in ["endpoint", "search_endpoint", "index_name"]):
        new_config["search_config"] = {
            "endpoint": old_config.get("endpoint") or old_config.get("search_endpoint"),
            "api_key": old_config.get("api_key") or old_config.get("search_api_key"),
            "index_name": old_config.get("index_name")
        }
    
    # Validate the new configuration
    try:
        config_obj = AzureBlobRAGConfig.from_dict(new_config)
        return json.dumps(new_config)
    except Exception as e:
        logger.warning(f"Failed to create valid config, using defaults: {e}")
        return create_default_config()

def create_default_config():
    """Create a default configuration"""
    default_config = {
        "auth_method": "service_principal",
        "service_principal": {
            "tenant_id": "",
            "subscription_id": "",
            "client_id": "",
            "client_secret": ""
        },
        "blob_config": {
            "container_name": "documents",
            "storage_account_name": "mystorageaccount"
        },
        "resource_config": {
            "resource_group_name": "myresourcegroup",
            "location": "eastus"
        }
    }
    return json.dumps(default_config)

async def main():
    """Run the migration"""
    logger.info("Starting Azure Blob RAG configuration migration")
    await migrate_azure_blob_configs()
    logger.info("Migration completed")

if __name__ == "__main__":
    asyncio.run(main())