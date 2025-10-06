import asyncpg
from asyncpg import Pool
import json
from typing import Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseConfig:
    def __init__(self, database_name: str = None):
        self.host = os.getenv('DOCUMENT_LOADER_DB_HOST', 'localhost')
        self.port = int(os.getenv('DOCUMENT_LOADER_DB_PORT', '5432'))
        self.database = database_name or os.getenv('DOCUMENT_LOADER_DB_NAME', 'document_loader')
        self.user = os.getenv('DOCUMENT_LOADER_DB_USER', 'postgres')
        self.password = os.getenv('DOCUMENT_LOADER_DB_PASSWORD', 'password')
        self.min_pool_size = int(os.getenv('DOCUMENT_LOADER_DB_MIN_POOL_SIZE', '10'))
        self.max_pool_size = int(os.getenv('DOCUMENT_LOADER_DB_MAX_POOL_SIZE', '20'))
    
    def get_connection_string(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @staticmethod
    def get_available_databases():
        """Get list of available database names from environment."""
        db_names = os.getenv('DOCUMENT_LOADER_DB_NAMES', '')
        if db_names:
            return [name.strip() for name in db_names.split(',')]
        
        # Fallback to default database name
        default_db = os.getenv('DOCUMENT_LOADER_DB_NAME', 'document_loader')
        return [default_db]
    
    @staticmethod
    def get_default_database():
        """Get the default database name."""
        available = DatabaseConfig.get_available_databases()
        return available[0] if available else 'document_loader'

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool: Optional[Pool] = None
    
    async def connect(self):
        """Create database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.config.get_connection_string(),
            min_size=self.config.min_pool_size,
            max_size=self.config.max_pool_size,
        )
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def execute(self, query: str, *args, timeout: float = None):
        """Execute a query without returning results."""
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args, timeout=timeout)
    
    async def fetch(self, query: str, *args, timeout: float = None):
        """Execute a query and fetch all results."""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args, timeout=timeout)
    
    async def fetchrow(self, query: str, *args, timeout: float = None):
        """Execute a query and fetch one result."""
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args, timeout=timeout)
    
    async def fetchval(self, query: str, *args, timeout: float = None):
        """Execute a query and fetch a single value."""
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args, timeout=timeout)

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)