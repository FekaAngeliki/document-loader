"""
Schema Management API - Exposes CLI schema commands through web API
Provides corporate-grade schema isolation with proper authentication and audit logging.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import sys
import os
import asyncio

# Add the parent directory to the path so we can import from document_loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from src.data.database import DatabaseConfig, Database
from src.data.schema import create_schema_sql
from ..core.auth import User, get_current_user, require_roles, UserRole
import psycopg

router = APIRouter()

# Pydantic models for API requests/responses
class SchemaCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

class SchemaInfo(BaseModel):
    schema_name: str
    is_isolated: bool
    table_count: int
    knowledge_bases_count: int
    description: Optional[str] = None

class SchemaListResponse(BaseModel):
    schemas: List[SchemaInfo]
    total_count: int

class OperationResponse(BaseModel):
    success: bool
    message: str
    schema_name: Optional[str] = None

class ConnectionStatus(BaseModel):
    success: bool
    message: str
    host: str
    port: int
    database: str
    user: str
    postgres_reachable: bool
    target_database_exists: bool

class DatabaseCreateRequest(BaseModel):
    database_name: Optional[str] = None
    create_schema: bool = True
    force: bool = False

class DatabaseDeleteRequest(BaseModel):
    database_name: str
    force: bool = False

class DatabaseInfo(BaseModel):
    database_name: str
    owner: str
    size: Optional[str] = None
    encoding: str
    collation: str
    is_template: bool
    connection_limit: int

class DatabaseListResponse(BaseModel):
    databases: List[DatabaseInfo]
    total_count: int

class ConnectionCheckRequest(BaseModel):
    database_name: Optional[str] = None

@router.post("/schemas", response_model=OperationResponse)
async def create_schema(
    request: SchemaCreateRequest,
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SCHEMA_MANAGER]))
):
    """
    Create a new isolated schema for RAG use case.
    Equivalent to CLI: document-loader create-schema --name {name} --description {description}
    """
    try:
        # Create database config for schema operations
        config = DatabaseConfig(schema_name=request.name)
        db = Database(config)
        await db.connect()
        
        try:
            # Check if schema already exists
            existing_schemas = await db.fetch(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                request.name
            )
            
            if existing_schemas:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Schema '{request.name}' already exists"
                )
            
            # Create the schema
            await db.execute(f'CREATE SCHEMA "{request.name}"')
            
            # Set search path to the new schema
            await db.execute(f'SET search_path TO "{request.name}"')
            
            # Create all tables in the new schema
            base_sql = create_schema_sql()
            
            # Replace table references to be schema-specific (same logic as CLI)
            schema_sql = base_sql.replace(
                "CREATE TABLE IF NOT EXISTS ",
                f'CREATE TABLE IF NOT EXISTS "{request.name}".'
            ).replace(
                "CREATE INDEX IF NOT EXISTS ",
                f'CREATE INDEX IF NOT EXISTS '
            ).replace(
                "INSERT INTO source_type",
                f'INSERT INTO "{request.name}".source_type'
            ).replace(
                "INSERT INTO rag_type", 
                f'INSERT INTO "{request.name}".rag_type'
            ).replace(
                "ON file_record(", 
                f'ON "{request.name}".file_record('
            ).replace(
                "ON sync_run(",
                f'ON "{request.name}".sync_run('
            )
            
            # Fix foreign key references to be schema-specific
            schema_sql = schema_sql.replace(
                "REFERENCES knowledge_base(id)",
                f'REFERENCES "{request.name}".knowledge_base(id)'
            ).replace(
                "REFERENCES sync_run(id)",
                f'REFERENCES "{request.name}".sync_run(id)'
            )
            
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                await db.execute(statement)
            
            # Add schema metadata if description provided
            if request.description:
                await db.execute(f'SET search_path TO "{request.name}"')
                # Use direct string formatting to avoid parameterized query issues
                escaped_description = request.description.replace("'", "''")
                await db.execute(
                    f"COMMENT ON SCHEMA \"{request.name}\" IS '{escaped_description}'"
                )
            
            return OperationResponse(
                success=True,
                message=f"Schema '{request.name}' created successfully with complete table structure",
                schema_name=request.name
            )
            
        finally:
            await db.disconnect()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schema: {str(e)}")

@router.get("/schemas", response_model=SchemaListResponse)
async def list_schemas(
    current_user: User = Depends(get_current_user)
):
    """
    List all RAG schemas with metadata.
    Equivalent to CLI: document-loader list-schemas
    """
    try:
        config = DatabaseConfig()
        db = Database(config)
        await db.connect()
        
        try:
            # Get all non-system schemas
            schemas_query = """
            SELECT 
                s.schema_name,
                obj_description(quote_ident(s.schema_name)::regnamespace, 'pg_namespace') as description,
                (
                    SELECT COUNT(*) 
                    FROM information_schema.tables t 
                    WHERE t.table_schema = s.schema_name 
                    AND t.table_name IN ('knowledge_base', 'sync_run', 'file_record', 'source_type', 'rag_type')
                ) as table_count
            FROM information_schema.schemata s
            WHERE s.schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'public')
            AND s.schema_name !~ '^pg_'
            ORDER BY s.schema_name
            """
            
            schemas_data = await db.fetch(schemas_query)
            
            schemas = []
            for schema_row in schemas_data:
                # Count knowledge bases in this schema
                kb_config = DatabaseConfig(schema_name=schema_row['schema_name'])
                kb_db = Database(kb_config)
                await kb_db.connect()
                
                try:
                    kb_count = await kb_db.fetchval(
                        f"SELECT COUNT(*) FROM {kb_config.qualify_table('knowledge_base')}"
                    )
                except:
                    kb_count = 0
                finally:
                    await kb_db.disconnect()
                
                schemas.append(SchemaInfo(
                    schema_name=schema_row['schema_name'],
                    is_isolated=True,
                    table_count=schema_row['table_count'] or 0,
                    knowledge_bases_count=kb_count or 0,
                    description=schema_row['description']
                ))
            
            return SchemaListResponse(
                schemas=schemas,
                total_count=len(schemas)
            )
            
        finally:
            await db.disconnect()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list schemas: {str(e)}")

@router.get("/schemas/{schema_name}", response_model=SchemaInfo)
async def get_schema_info(
    schema_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific schema.
    Equivalent to CLI: document-loader --schema {schema_name} schema-info
    """
    try:
        config = DatabaseConfig(schema_name=schema_name)
        db = Database(config)
        await db.connect()
        
        try:
            # Check if schema exists
            schema_exists = await db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)",
                schema_name
            )
            
            if not schema_exists:
                raise HTTPException(status_code=404, detail=f"Schema '{schema_name}' not found")
            
            # Get schema description
            description = await db.fetchval(
                "SELECT obj_description(quote_ident(%s)::regnamespace, 'pg_namespace')",
                schema_name
            )
            
            # Count tables
            table_count = await db.fetchval("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name IN ('knowledge_base', 'sync_run', 'file_record', 'source_type', 'rag_type')
            """, schema_name)
            
            # Count knowledge bases
            try:
                kb_count = await db.fetchval(
                    f"SELECT COUNT(*) FROM {config.qualify_table('knowledge_base')}"
                )
            except:
                kb_count = 0
            
            return SchemaInfo(
                schema_name=schema_name,
                is_isolated=schema_name != 'public',
                table_count=table_count or 0,
                knowledge_bases_count=kb_count or 0,
                description=description
            )
            
        finally:
            await db.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schema info: {str(e)}")

@router.delete("/schemas/{schema_name}", response_model=OperationResponse)
async def drop_schema(
    schema_name: str,
    force: bool = Query(False, description="Force drop without confirmation"),
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """
    Drop a schema and all its contents.
    Equivalent to CLI: document-loader drop-schema --name {schema_name} [--force]
    """
    try:
        if schema_name in ['public', 'information_schema', 'pg_catalog']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot drop system schema '{schema_name}'"
            )
        
        config = DatabaseConfig()
        db = Database(config)
        await db.connect()
        
        try:
            # Check if schema exists
            schema_exists = await db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)",
                schema_name
            )
            
            if not schema_exists:
                raise HTTPException(status_code=404, detail=f"Schema '{schema_name}' not found")
            
            # In a real corporate environment, you might want additional safety checks here
            # such as checking if schema has active connections, recent activity, etc.
            
            # Drop the schema
            await db.execute(f'DROP SCHEMA "{schema_name}" CASCADE')
            
            return OperationResponse(
                success=True,
                message=f"Schema '{schema_name}' dropped successfully",
                schema_name=schema_name
            )
            
        finally:
            await db.disconnect()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to drop schema: {str(e)}")

@router.get("/schemas/{schema_name}/knowledge-bases")
async def list_schema_knowledge_bases(
    schema_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    List all knowledge bases in a specific schema.
    Equivalent to CLI: document-loader --schema {schema_name} list
    """
    try:
        config = DatabaseConfig(schema_name=schema_name)
        db = Database(config)
        await db.connect()
        
        try:
            # Get all knowledge bases for this schema
            knowledge_bases = await db.fetch(f"""
                SELECT id, name, source_type, rag_type, created_at, updated_at
                FROM {config.qualify_table('knowledge_base')}
                ORDER BY name
            """)
            
            return {
                "schema_name": schema_name,
                "knowledge_bases": [dict(kb) for kb in knowledge_bases],
                "count": len(knowledge_bases)
            }
        finally:
            await db.disconnect()
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to list knowledge bases for schema '{schema_name}': {str(e)}"
        )

@router.post("/connection/check", response_model=ConnectionStatus)
async def check_connection(
    request: ConnectionCheckRequest
):
    """
    Test database connectivity and check if target database exists.
    Uses secure request body instead of URL parameters.
    Equivalent to CLI: document-loader check-connection [--database-name {database_name}]
    """
    try:
        # Use custom database name if provided, otherwise use default from config
        config = DatabaseConfig(request.database_name) if request.database_name else DatabaseConfig()
        
        postgres_reachable = False
        target_database_exists = False
        message = ""
        
        try:
            # Check if we can connect to postgres database (server connection)
            connection = await psycopg.AsyncConnection.connect(
                f"postgresql://{config.user}:{config.password}@{config.host}:{config.port}/postgres"
            )
            postgres_reachable = True
            
            # Check if target database exists
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (config.database,)
                )
                result = await cursor.fetchone()
                exists = bool(result)
            target_database_exists = bool(exists)
            
            await connection.close()
            
            if target_database_exists:
                # Try connecting to the target database
                target_connection = await psycopg.AsyncConnection.connect(
                    f"postgresql://{config.user}:{config.password}@{config.host}:{config.port}/{config.database}"
                )
                await target_connection.close()
                message = f"Successfully connected to database '{config.database}'"
            else:
                message = f"PostgreSQL server reachable, but database '{config.database}' does not exist"
                
        except Exception as e:
            message = f"Connection failed: {str(e)}"
        
        return ConnectionStatus(
            success=postgres_reachable and target_database_exists,
            message=message,
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            postgres_reachable=postgres_reachable,
            target_database_exists=target_database_exists
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check connection: {str(e)}")

@router.post("/database/create", response_model=OperationResponse)
async def create_database(
    request: DatabaseCreateRequest,
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """
    Create the database and optionally the schema if they don't exist.
    Equivalent to CLI: document-loader create-db [--no-schema] [--force]
    """
    try:
        # Use custom database name if provided, otherwise use default from config
        config = DatabaseConfig(request.database_name) if request.database_name else DatabaseConfig()
        
        # Connect to postgres database to create the target database
        connection = await psycopg.AsyncConnection.connect(
            f"postgresql://{config.user}:{config.password}@{config.host}:{config.port}/postgres",
            autocommit=True
        )
        
        try:
            # Check if database already exists
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (config.database,)
                )
                result = await cursor.fetchone()
                exists = bool(result)
            
            if exists:
                await connection.close()
                return OperationResponse(
                    success=True,
                    message=f"Database '{config.database}' already exists"
                )
            
            # Create the database (autocommit enabled at connection level)
            async with connection.cursor() as cursor:
                await cursor.execute(f'CREATE DATABASE "{config.database}"')
            await connection.close()
            
            message = f"Database '{config.database}' created successfully"
            
            # Create the schema if requested
            if request.create_schema:
                db = Database(config)
                await db.connect()
                
                try:
                    schema_sql = create_schema_sql()
                    statements = schema_sql.split(';')
                    
                    for statement in statements:
                        if statement.strip():
                            await db.execute(statement)
                    
                    message += " with complete schema"
                    
                except Exception as e:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Database created but schema creation failed: {str(e)}"
                    )
                finally:
                    await db.disconnect()
            
            return OperationResponse(
                success=True,
                message=message
            )
            
        except Exception as e:
            await connection.close()
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create database: {str(e)}")

@router.get("/database/list", response_model=DatabaseListResponse)
async def list_databases(
    current_user: User = Depends(get_current_user)
):
    """
    List all PostgreSQL databases accessible by the current user.
    Shows database name, owner, size, encoding, and other metadata.
    """
    try:
        config = DatabaseConfig()
        
        # Connect to postgres database to list all databases
        connection = await psycopg.AsyncConnection.connect(
            f"postgresql://{config.user}:{config.password}@{config.host}:{config.port}/postgres"
        )
        
        try:
            async with connection.cursor() as cursor:
                # Get comprehensive database information
                query = """
                SELECT 
                    d.datname as database_name,
                    pg_catalog.pg_get_userbyid(d.datdba) as owner,
                    pg_size_pretty(pg_database_size(d.datname)) as size,
                    pg_encoding_to_char(d.encoding) as encoding,
                    d.datcollate as collation,
                    d.datistemplate as is_template,
                    d.datconnlimit as connection_limit
                FROM pg_catalog.pg_database d
                WHERE d.datallowconn = true
                ORDER BY d.datname
                """
                
                await cursor.execute(query)
                results = await cursor.fetchall()
                
                databases = []
                for row in results:
                    databases.append(DatabaseInfo(
                        database_name=row[0],
                        owner=row[1],
                        size=row[2],
                        encoding=row[3],
                        collation=row[4],
                        is_template=row[5],
                        connection_limit=row[6]
                    ))
                
                return DatabaseListResponse(
                    databases=databases,
                    total_count=len(databases)
                )
                
        finally:
            await connection.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list databases: {str(e)}")

@router.post("/database/delete", response_model=OperationResponse)
async def delete_database(
    request: DatabaseDeleteRequest,
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN]))
):
    """
    Delete a PostgreSQL database using request body.
    WARNING: This operation is irreversible and will destroy all data in the database.
    
    Request Body:
        database_name: Name of the database to delete
        force: Skip safety checks (use with extreme caution)
    """
    try:
        # Prevent deletion of system databases
        system_databases = {'postgres', 'template0', 'template1'}
        if request.database_name.lower() in system_databases:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete system database '{request.database_name}'"
            )
        
        config = DatabaseConfig()
        
        # Connect to postgres database to drop the target database
        connection = await psycopg.AsyncConnection.connect(
            f"postgresql://{config.user}:{config.password}@{config.host}:{config.port}/postgres",
            autocommit=True
        )
        
        try:
            # Check if database exists
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (request.database_name,)
                )
                result = await cursor.fetchone()
                exists = bool(result)
            
            if not exists:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Database '{request.database_name}' does not exist"
                )
            
            # Additional safety check: count active connections
            if not request.force:
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = %s",
                        (request.database_name,)
                    )
                    result = await cursor.fetchone()
                    active_connections = result[0] if result else 0
                
                if active_connections > 0:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Database '{request.database_name}' has {active_connections} active connections. Use force=true to override."
                    )
            
            # Terminate active connections if force is enabled
            if request.force:
                async with connection.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity 
                        WHERE datname = %s AND pid <> pg_backend_pid()
                    """, (request.database_name,))
            
            # Drop the database
            async with connection.cursor() as cursor:
                await cursor.execute(f'DROP DATABASE "{request.database_name}"')
            
            return OperationResponse(
                success=True,
                message=f"Database '{request.database_name}' deleted successfully"
            )
            
        finally:
            await connection.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete database: {str(e)}")