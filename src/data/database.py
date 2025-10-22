import psycopg
from psycopg_pool import AsyncConnectionPool
import json
from typing import Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseConfig:
    def __init__(self, database_name: str = None, schema_name: str = None):
        self.host = os.getenv('DOCUMENT_LOADER_DB_HOST', 'localhost')
        self.port = int(os.getenv('DOCUMENT_LOADER_DB_PORT', '5432'))
        self.database = database_name or os.getenv('DOCUMENT_LOADER_DB_NAME')
        self.user = os.getenv('DOCUMENT_LOADER_DB_USER', 'postgres')
        self.password = os.getenv('DOCUMENT_LOADER_DB_PASSWORD', 'password')
        self.schema = schema_name or os.getenv('DOCUMENT_LOADER_DB_SCHEMA', 'public')
        self.min_pool_size = int(os.getenv('DOCUMENT_LOADER_DB_MIN_POOL_SIZE', '10'))
        self.max_pool_size = int(os.getenv('DOCUMENT_LOADER_DB_MAX_POOL_SIZE', '20'))
    
    def get_connection_string(self):
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def qualify_table(self, table_name: str) -> str:
        """Return schema-qualified table name."""
        if self.schema and self.schema != 'public':
            return f'"{self.schema}".{table_name}'
        return table_name
    
    def get_schema_info(self) -> dict:
        """Return schema configuration info."""
        return {
            'schema': self.schema,
            'is_isolated': self.schema != 'public',
            'qualified_prefix': f'"{self.schema}".' if self.schema != 'public' else ''
        }
    
    @staticmethod
    def get_available_databases():
        """Get list of available database names from environment."""
        db_names = os.getenv('DOCUMENT_LOADER_DB_NAMES', '')
        if db_names:
            return [name.strip() for name in db_names.split(',')]
        
        # Fallback to default database name
        default_db = os.getenv('DOCUMENT_LOADER_DB_NAME')
        return [default_db] if default_db else []
    
    @staticmethod
    def get_default_database():
        """Get the default database name."""
        available = DatabaseConfig.get_available_databases()
        return available[0] if available else None

class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool: Optional[AsyncConnectionPool] = None
    
    async def connect(self):
        """Create database connection pool."""
        self.pool = AsyncConnectionPool(
            conninfo=self.config.get_connection_string(),
            min_size=self.config.min_pool_size,
            max_size=self.config.max_pool_size,
        )
        await self.pool.open()
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def execute(self, query: str, *args, timeout: float = None):
        """Execute a query without returning results."""
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                return await cursor.execute(query, args)
    
    async def fetch(self, query: str, *args, timeout: float = None):
        """Execute a query and fetch all results."""
        from psycopg.rows import dict_row
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, args)
                return await cursor.fetchall()
    
    async def fetchrow(self, query: str, *args, timeout: float = None):
        """Execute a query and fetch one result."""
        from psycopg.rows import dict_row
        async with self.pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, args)
                return await cursor.fetchone()
    
    async def fetchval(self, query: str, *args, timeout: float = None):
        """Execute a query and fetch a single value."""
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(query, args)
                row = await cursor.fetchone()
                return row[0] if row else None

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)