#!/usr/bin/env python3
"""
Document Management System for RAG - CLI Application
"""
import click
import asyncio
import logging
from pathlib import Path
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.logging import RichHandler
from rich import print as rprint
import asyncpg
import asyncpg.exceptions

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.database import Database, DatabaseConfig
from src.data.repository import Repository
from src.data.repository_ext import ExtendedRepository
from src.data.models import KnowledgeBase, SyncRunStatus
from src.cli.multi_source_commands import multi_source
from src.cli.analytics_commands import analytics
from src.core.batch_runner import BatchRunner
from src.core.scanner import FileScanner
from src.data.schema import create_schema_sql
from src.core.factory import SourceFactory, RAGFactory
from src.cli.params import init_params, get_params, update_params
from src.core.logging_config import configure_app_logging
from src.admin.config_manager import create_config_manager
from src.data.multi_source_models import create_multi_source_kb_from_config
from src.data.multi_source_repository import MultiSourceRepository
from src.cli.validation_helpers import validate_and_confirm_kb_creation, validate_and_confirm_db_creation, get_user_confirmation
from src.data.update_validators import validate_kb_update

# Setup rich console
console = Console()

# Logging will be configured after parsing command line arguments

async def create_database(config: DatabaseConfig, create_schema: bool = True) -> bool:
    """Create the database if it doesn't exist, optionally with schema."""
    try:
        # Connect to postgres database
        connection = await asyncpg.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database='postgres'
        )
        
        # Check if database already exists
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            config.database
        )
        
        if not exists:
            # Create the database
            await connection.execute(f'CREATE DATABASE "{config.database}"')
            console.print(f"[green]✓ Database '{config.database}' created successfully.[/green]")
            await connection.close()
            
            # Create the schema if requested
            if create_schema:
                console.print("[yellow]Setting up database schema...[/yellow]")
                db = Database(config)
                await db.connect()
                
                try:
                    schema_sql = create_schema_sql()
                    statements = schema_sql.split(';')
                    
                    with console.status("[bold green]Creating tables and indexes..."):
                        for i, statement in enumerate(statements):
                            if statement.strip():
                                await db.execute(statement)
                                console.print(f"[dim]Executed statement {i+1}/{len(statements)}[/dim]")
                    
                    console.print("[green]✓ Database schema created successfully.[/green]")
                except Exception as e:
                    console.print(f"[red]Error creating schema: {e}[/red]")
                    raise
                finally:
                    await db.disconnect()
            
            return True
        else:
            console.print(f"[yellow]Database '{config.database}' already exists.[/yellow]")
            await connection.close()
            return False
        
    except asyncpg.exceptions.InvalidPasswordError:
        console.print(f"[red]Invalid password for user '{config.user}'.[/red]")
        raise
    except Exception as e:
        console.print(f"[red]Failed to create database: {e}[/red]")
        raise

async def check_database_exists(config: DatabaseConfig) -> bool:
    """Check if database exists by connecting to postgres database first."""
    try:
        # Create a temporary config to connect to postgres database
        temp_config = DatabaseConfig()
        temp_config.database = 'postgres'  # Connect to default postgres database
        
        connection = await asyncpg.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database='postgres'
        )
        
        # Check if our target database exists
        result = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            config.database
        )
        
        await connection.close()
        return result is not None
        
    except asyncpg.exceptions.InvalidPasswordError:
        console.print(f"[red]Invalid password for user '{config.user}'.[/red]")
        console.print("\n[yellow]Please check your .env configuration:[/yellow]")
        console.print("  DOCUMENT_LOADER_DB_PASSWORD")
        console.print(f"\n[yellow]Current settings:[/yellow]")
        console.print(f"  User: {config.user}")
        console.print(f"  Host: {config.host}")
        console.print(f"  Port: {config.port}")
        console.print("\n[yellow]Common fixes:[/yellow]")
        console.print("  1. Update the password in your .env file")
        console.print("  2. Check PostgreSQL authentication settings (pg_hba.conf)")
        console.print("  3. Verify the user exists in PostgreSQL")
        raise SystemExit(1)
    except ConnectionRefusedError:
        console.print(f"[red]Cannot connect to PostgreSQL at {config.host}:{config.port}[/red]")
        console.print("\n[yellow]Please ensure PostgreSQL is running:[/yellow]")
        console.print("  On macOS: brew services start postgresql")
        console.print("  On Linux: sudo systemctl start postgresql")
        console.print("  On Windows: net start postgresql-x64-14")
        raise SystemExit(1)
    except asyncpg.exceptions.UndefinedObjectError as e:
        if 'role' in str(e):
            console.print(f"[red]User '{config.user}' does not exist in PostgreSQL.[/red]")
            console.print("\n[yellow]Please create the user:[/yellow]")
            console.print(f"  sudo -u postgres createuser --interactive {config.user}")
            console.print("Or:")
            console.print(f"  sudo -u postgres psql -c \"CREATE USER {config.user} WITH PASSWORD 'yourpassword';\"")
        else:
            console.print(f"[red]Database error: {e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Unable to connect to PostgreSQL: {e}[/red]")
        console.print("\n[yellow]Please ensure PostgreSQL is running and check:[/yellow]")
        console.print(f"  Host: {config.host}")
        console.print(f"  Port: {config.port}")
        console.print(f"  User: {config.user}")
        raise SystemExit(1)

async def get_database():
    """Get database connection."""
    config = DatabaseConfig()
    
    # First check if database exists
    db_exists = await check_database_exists(config)
    
    if not db_exists:
        console.print(f"[red]Database '{config.database}' does not exist.[/red]")
        console.print("\n[yellow]You have several options to create it:[/yellow]")
        console.print("\n1. Use the document-loader CLI:")
        console.print("   [cyan]document-loader create-db[/cyan]")
        console.print("\n2. Create it manually:")
        console.print(f"   [cyan]createdb -U {config.user} -h {config.host} -p {config.port} {config.database}[/cyan]")
        console.print("\n3. If using psql:")
        console.print(f"   [cyan]psql -U {config.user} -h {config.host} -p {config.port} -c \"CREATE DATABASE {config.database};\"[/cyan]")
        console.print("\n[yellow]Current configuration:[/yellow]")
        console.print(f"  Host: {config.host}")
        console.print(f"  Port: {config.port}")
        console.print(f"  User: {config.user}")
        console.print(f"  Database: {config.database}")
        raise SystemExit(1)
    
    db = Database(config)
    try:
        await db.connect()
        return db
    except Exception as e:
        console.print(f"[red]Database connection failed: {e}[/red]")
        console.print("\n[yellow]Please check your database configuration.[/yellow]")
        raise

@click.group()
@click.version_option(version='0.1.0')
@click.option('--verbose', is_flag=True, help='Enable verbose logging (DEBUG level)')
@click.option('--database', '-d', help='Database name override (for multi-tenant deployments)')
@click.option('--schema', '-s', help='Schema name for isolated RAG use cases')
@click.pass_context
def cli(ctx, verbose, database, schema):
    """Document Management System for RAG systems."""
    # Initialize command line parameters
    params = init_params(ctx)
    params.verbose = verbose
    
    # Initialize context for passing parameters
    ctx.ensure_object(dict)
    
    # Handle database override for multi-tenant deployments
    if database:
        original_db = os.environ.get('DOCUMENT_LOADER_DB_NAME')
        os.environ['DOCUMENT_LOADER_DB_NAME'] = database
        ctx.obj['database_override'] = database
        ctx.obj['original_database'] = original_db
        console.print(f"[blue]Database override:[/blue] {database}")
        if original_db:
            console.print(f"[dim]Original database: {original_db}[/dim]")
    
    # Handle schema override for RAG use case isolation
    if schema:
        ctx.obj['schema'] = schema
        # Convert to valid PostgreSQL identifier
        ctx.obj['schema_name'] = schema.lower().replace('-', '_')
        os.environ['DOCUMENT_LOADER_DB_SCHEMA'] = ctx.obj['schema_name']
        console.print(f"[blue]Schema override:[/blue] {schema} -> {ctx.obj['schema_name']}")
        console.print(f"[dim]All operations will be isolated to schema '{ctx.obj['schema_name']}'[/dim]")
    
    # Configure logging based on verbose flag
    log_level = params.get_log_level()
    if not log_level:
        log_level = os.getenv('DOCUMENT_LOADER_LOG_LEVEL', 'INFO')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    # Configure application logging
    configure_app_logging(verbose)
    
    # Store verbose flag in context for sub-commands
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

@cli.command()
@click.option('--create-db', is_flag=True, help='Create the database if it doesn\'t exist')
def init_db(create_db: bool):
    """Initialize the database (optionally create if not exists)."""
    async def run_init():
        config = DatabaseConfig()
        
        try:
            # First check if database exists
            db_exists = await check_database_exists(config)
            
            if not db_exists:
                if create_db:
                    console.print(f"[yellow]Database '{config.database}' does not exist. Creating it with schema...[/yellow]")
                    created = await create_database(config, create_schema=True)
                    if not created:
                        console.print(f"[red]Failed to create database '{config.database}'[/red]")
                        return
                    console.print(f"[green]Database and schema created successfully![/green]")
                    console.print("\nYou can now:")
                    console.print("  1. Create a knowledge base: [cyan]document-loader create-kb[/cyan]")
                    console.print("  2. List knowledge bases: [cyan]document-loader list-kb[/cyan]")
                    return
                else:
                    console.print(f"[red]Database '{config.database}' does not exist.[/red]")
                    console.print("\n[yellow]You can:[/yellow]")
                    console.print("  1. Use the --create-db flag:")
                    console.print("     [cyan]document-loader init-db --create-db[/cyan]")
                    console.print("  2. Use the create-db command:")
                    console.print("     [cyan]document-loader create-db[/cyan]")
                    console.print("  3. Create it manually:")
                    console.print(f"     [cyan]createdb -U {config.user} -h {config.host} -p {config.port} {config.database}[/cyan]")
                    return
            
            if db_exists:
                console.print(f"[green]Database '{config.database}' exists.[/green]")
                
                # Now check if tables exist
                db = await get_database()
                try:
                    repo = Repository(db)
                    # Try to count knowledge bases as a simple check
                    count = await repo.db.fetchval("SELECT COUNT(*) FROM knowledge_base")
                    console.print(f"[green]Tables are already initialized. Found {count} knowledge bases.[/green]")
                except asyncpg.exceptions.UndefinedTableError:
                    # Tables don't exist, create schema now
                    console.print("[yellow]Database exists but tables need to be created. Creating schema...[/yellow]")
                    await db.disconnect()
                    
                    # Create the schema
                    await create_database(config, create_schema=True)
                    console.print("[green]Schema created successfully![/green]")
                except Exception as e:
                    console.print(f"[red]Error checking tables: {e}[/red]")
                finally:
                    if db.pool:
                        await db.disconnect()
                
        except SystemExit:
            # Already handled with proper error message
            pass
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    asyncio.run(run_init())

@cli.command()
@click.option('--no-schema', is_flag=True, help='Create database without schema')
@click.option('--force', is_flag=True, help='Skip validation checks and create without confirmation')
def create_db(no_schema: bool, force: bool):
    """Create the database and schema if they don't exist."""
    async def run_create():
        config = DatabaseConfig()
        
        # Validate database creation
        if not await validate_and_confirm_db_creation(config.database, config, force):
            console.print("[red]❌ Database creation cancelled due to validation errors.[/red]")
            return
        
        # Get user confirmation unless forced
        if not force:
            if not get_user_confirmation(
                f"create database '{config.database}'",
                f"This will create a new PostgreSQL database on {config.host}:{config.port}"
            ):
                console.print("[yellow]Operation cancelled by user.[/yellow]")
                return
        
        console.print("[yellow]Creating database...[/yellow]")
        console.print(f"\n[cyan]Configuration:[/cyan]")
        console.print(f"  Host: {config.host}")
        console.print(f"  Port: {config.port}")
        console.print(f"  User: {config.user}")
        console.print(f"  Database: {config.database}")
        
        try:
            created = await create_database(config, create_schema=not no_schema)
            
            if created:
                console.print(f"\n[green]Database '{config.database}' has been created successfully![/green]")
                if not no_schema:
                    console.print("[green]Schema has been initialized.[/green]")
                console.print("\nNext steps:")
                console.print("  1. Create a knowledge base: [cyan]document-loader create-kb[/cyan]")
                console.print("  2. List knowledge bases: [cyan]document-loader list-kb[/cyan]")
            else:
                console.print("\nDatabase already exists.")
                
                # Check if schema needs to be created
                if not no_schema:
                    db = await get_database()
                    try:
                        # Check if tables exist
                        tables = await db.fetch("""
                            SELECT tablename FROM pg_tables 
                            WHERE schemaname = 'public' 
                            ORDER BY tablename
                        """)
                        
                        if not tables:
                            console.print("[yellow]Schema not found. Creating schema...[/yellow]")
                            
                            schema_sql = create_schema_sql()
                            statements = schema_sql.split(';')
                            
                            with console.status("[bold green]Creating tables and indexes..."):
                                for i, statement in enumerate(statements):
                                    if statement.strip():
                                        await db.execute(statement)
                            
                            console.print("[green]✓ Schema created successfully.[/green]")
                        else:
                            console.print("[green]Schema already exists.[/green]")
                            
                    except Exception as e:
                        console.print(f"[red]Error checking/creating schema: {e}[/red]")
                    finally:
                        await db.disconnect()
                
                console.print("\nYou can proceed with:")
                console.print("  1. Create a knowledge base: [cyan]document-loader create-kb[/cyan]")
                console.print("  2. List knowledge bases: [cyan]document-loader list-kb[/cyan]")
                
        except asyncpg.exceptions.InvalidPasswordError:
            console.print("\n[yellow]Please check your .env configuration:[/yellow]")
            console.print("  DOCUMENT_LOADER_DB_PASSWORD")
            raise SystemExit(1)
        except Exception as e:
            console.print(f"\n[red]Error creating database: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_create())

@cli.command()
@click.option('--database-name', help='PostgreSQL database name (overrides .env setting)')
def check_connection(database_name):
    """Check database connectivity."""
    async def run_check():
        # Use custom database name if provided, otherwise use default from .env
        config = DatabaseConfig(database_name) if database_name else DatabaseConfig()
        
        console.print("[yellow]Checking database connection...[/yellow]")
        console.print(f"\n[cyan]Configuration:[/cyan]")
        console.print(f"  Host: {config.host}")
        console.print(f"  Port: {config.port}")
        console.print(f"  User: {config.user}")
        console.print(f"  Database: {config.database}")
        console.print(f"  Password: {'*' * len(config.password)}")
        
        try:
            # Check if we can connect to postgres database
            console.print("\n[yellow]Step 1: Checking PostgreSQL server connection...[/yellow]")
            connection = await asyncpg.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database='postgres'
            )
            await connection.close()
            console.print("[green]✓ Successfully connected to PostgreSQL server[/green]")
            
            # Check if our database exists
            console.print("\n[yellow]Step 2: Checking if database exists...[/yellow]")
            db_exists = await check_database_exists(config)
            
            if db_exists:
                console.print(f"[green]✓ Database '{config.database}' exists[/green]")
                
                # Try to connect to our database
                console.print(f"\n[yellow]Step 3: Connecting to '{config.database}' database...[/yellow]")
                db = await get_database()
                console.print(f"[green]✓ Successfully connected to '{config.database}' database[/green]")
                
                # Check if tables exist
                console.print("\n[yellow]Step 4: Checking database schema...[/yellow]")
                try:
                    tables = await db.fetch("""
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public' 
                        ORDER BY tablename
                    """)
                    
                    if tables:
                        console.print("[green]✓ Found the following tables:[/green]")
                        for table in tables:
                            console.print(f"  - {table['tablename']}")
                    else:
                        console.print("[yellow]⚠ No tables found. Database schema needs to be initialized.[/yellow]")
                        
                except Exception as e:
                    console.print(f"[red]✗ Error checking tables: {e}[/red]")
                
                await db.disconnect()
            else:
                console.print(f"[red]✗ Database '{config.database}' does not exist[/red]")
                console.print("\n[yellow]To create the database, use one of these methods:[/yellow]")
                console.print("  1. [cyan]document-loader create-db[/cyan]")
                console.print(f"  2. [cyan]createdb -U {config.user} -h {config.host} -p {config.port} {config.database}[/cyan]")
            
            console.print("\n[green]Connection check complete![/green]")
            
        except Exception as e:
            console.print(f"\n[red]Connection check failed: {e}[/red]")
    
    asyncio.run(run_check())

@cli.command()
@click.option('--name', required=True, help='Schema name for the RAG use case')
@click.option('--description', help='Description of the RAG use case')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def create_schema(name: str, description: str, force: bool):
    """Create a new schema for a specific RAG knowledge base use case."""
    async def run_create_schema():
        config = DatabaseConfig()
        
        # Validate schema name (PostgreSQL naming rules)
        if not name.replace('_', '').replace('-', '').isalnum():
            console.print("[red]❌ Schema name must contain only letters, numbers, underscores, and hyphens[/red]")
            return
        
        # Convert to valid PostgreSQL identifier
        schema_name = name.lower().replace('-', '_')
        
        console.print(f"[yellow]Creating schema for RAG use case...[/yellow]")
        console.print(f"\n[cyan]Configuration:[/cyan]")
        console.print(f"  Database: {config.database}")
        console.print(f"  Schema Name: {schema_name}")
        console.print(f"  Description: {description or 'None'}")
        console.print(f"  User: {config.user}")
        
        if not force:
            console.print(f"\n[yellow]This will create schema '{schema_name}' in database '{config.database}'[/yellow]")
            if not click.confirm("Continue?"):
                console.print("[yellow]Operation cancelled.[/yellow]")
                return
        
        try:
            # Connect to the database
            connection = await asyncpg.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database
            )
            
            # Check if schema already exists
            existing = await connection.fetchval(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = $1",
                schema_name
            )
            
            if existing:
                console.print(f"[yellow]⚠️  Schema '{schema_name}' already exists[/yellow]")
                await connection.close()
                return
            
            # Create the schema
            await connection.execute(f'CREATE SCHEMA "{schema_name}"')
            
            # Create all core tables within the schema
            console.print("  Creating core tables...")
            
            # Import schema creation function
            from src.data.schema import create_schema_sql
            
            # Get the schema SQL and modify it to target our specific schema
            base_sql = create_schema_sql()
            
            # Replace table references to be schema-specific
            schema_sql = base_sql.replace(
                "CREATE TABLE IF NOT EXISTS ",
                f'CREATE TABLE IF NOT EXISTS "{schema_name}".'
            ).replace(
                "CREATE INDEX IF NOT EXISTS ",
                f'CREATE INDEX IF NOT EXISTS '
            ).replace(
                "INSERT INTO source_type",
                f'INSERT INTO "{schema_name}".source_type'
            ).replace(
                "INSERT INTO rag_type", 
                f'INSERT INTO "{schema_name}".rag_type'
            ).replace(
                "ON file_record(", 
                f'ON "{schema_name}".file_record('
            ).replace(
                "ON sync_run(",
                f'ON "{schema_name}".sync_run('
            )
            
            # Fix foreign key references to be schema-specific
            schema_sql = schema_sql.replace(
                "REFERENCES knowledge_base(id)",
                f'REFERENCES "{schema_name}".knowledge_base(id)'
            ).replace(
                "REFERENCES sync_run(id)",
                f'REFERENCES "{schema_name}".sync_run(id)'
            )
            
            # Execute the schema creation
            await connection.execute(schema_sql)
            
            # Create a metadata table for this RAG use case
            await connection.execute(f'''
                CREATE TABLE "{schema_name}".rag_metadata (
                    id SERIAL PRIMARY KEY,
                    use_case_name TEXT NOT NULL DEFAULT '{name}',
                    description TEXT DEFAULT '{description or ''}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    schema_version TEXT DEFAULT '1.0',
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Insert metadata record
            await connection.execute(f'''
                INSERT INTO "{schema_name}".rag_metadata (use_case_name, description)
                VALUES ($1, $2)
            ''', name, description or '')
            
            console.print("  ✅ Core tables created")
            console.print("  ✅ Source and RAG types populated")
            console.print("  ✅ Metadata table created")
            
            await connection.close()
            
            console.print(f"\n[green]✅ Schema '{schema_name}' created successfully![/green]")
            console.print("\n[cyan]Next steps:[/cyan]")
            console.print(f"  1. List schemas: [cyan]document-loader list-schemas[/cyan]")
            console.print(f"  2. Create knowledge base in this schema")
            console.print(f"  3. When done: [cyan]document-loader drop-schema --name {name}[/cyan]")
            
        except asyncpg.exceptions.InsufficientPrivilegeError:
            console.print(f"[red]❌ Insufficient privileges to create schema[/red]")
            console.print("The database user needs CREATE privileges on the database")
        except Exception as e:
            console.print(f"[red]❌ Error creating schema: {e}[/red]")
    
    asyncio.run(run_create_schema())

@cli.command()
@click.pass_context
def list_schemas(ctx):
    """List all RAG schemas in the database."""
    async def run_list_schemas():
        config = DatabaseConfig()
        
        # Show current schema context if any
        active_schema = ctx.obj.get('schema_name') if ctx.obj else None
        if active_schema:
            console.print(f"[blue]Active Schema:[/blue] {active_schema}")
            console.print(f"[dim]Commands will operate within this schema[/dim]\n")
        
        console.print("[yellow]Listing RAG schemas...[/yellow]")
        
        try:
            connection = await asyncpg.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database
            )
            
            # Get all schemas (exclude system schemas)
            schemas = await connection.fetch('''
                SELECT 
                    schema_name,
                    schema_owner
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'public')
                ORDER BY schema_name
            ''')
            
            if not schemas:
                console.print("\n[yellow]No custom schemas found[/yellow]")
                await connection.close()
                return
            
            console.print(f"\n[bold cyan]Schemas in database '{config.database}':[/bold cyan]")
            console.print()
            
            from rich.table import Table
            table = Table()
            table.add_column("Schema Name", style="bold green")
            table.add_column("Owner", style="cyan")
            table.add_column("Use Case", style="yellow")
            table.add_column("Description", style="dim")
            table.add_column("Created", style="dim")
            
            for schema in schemas:
                schema_name = schema['schema_name']
                
                # Try to get metadata from rag_metadata table
                try:
                    metadata = await connection.fetchrow(f'''
                        SELECT use_case_name, description, created_at
                        FROM "{schema_name}".rag_metadata
                        ORDER BY created_at DESC LIMIT 1
                    ''')
                    
                    if metadata:
                        use_case = metadata['use_case_name'] or schema_name
                        description = metadata['description'] or 'No description'
                        created = metadata['created_at'].strftime('%Y-%m-%d %H:%M') if metadata['created_at'] else 'Unknown'
                    else:
                        use_case = 'Unknown'
                        description = 'No metadata'
                        created = 'Unknown'
                except:
                    use_case = 'Unknown'
                    description = 'No metadata table'
                    created = 'Unknown'
                
                table.add_row(
                    schema_name,
                    schema['schema_owner'],
                    use_case,
                    description,
                    created
                )
            
            console.print(table)
            await connection.close()
            
        except Exception as e:
            console.print(f"[red]❌ Error listing schemas: {e}[/red]")
    
    asyncio.run(run_list_schemas())

@cli.command()
@click.option('--name', required=True, help='Schema name to drop')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def drop_schema(name: str, force: bool):
    """Drop a RAG schema and all its data."""
    async def run_drop_schema():
        config = DatabaseConfig()
        
        # Convert to valid PostgreSQL identifier
        schema_name = name.lower().replace('-', '_')
        
        console.print(f"[yellow]Preparing to drop schema...[/yellow]")
        console.print(f"\n[cyan]Configuration:[/cyan]")
        console.print(f"  Database: {config.database}")
        console.print(f"  Schema Name: {schema_name}")
        console.print(f"  User: {config.user}")
        
        try:
            connection = await asyncpg.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database
            )
            
            # Check if schema exists
            existing = await connection.fetchval(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = $1",
                schema_name
            )
            
            if not existing:
                console.print(f"[yellow]⚠️  Schema '{schema_name}' does not exist[/yellow]")
                await connection.close()
                return
            
            # Get table count
            table_count = await connection.fetchval(f'''
                SELECT count(*)
                FROM information_schema.tables 
                WHERE table_schema = '{schema_name}'
            ''')
            
            console.print(f"\n[red]⚠️  WARNING: This will permanently delete:[/red]")
            console.print(f"  - Schema: {schema_name}")
            console.print(f"  - Tables: {table_count}")
            console.print(f"  - All data in the schema")
            
            if not force:
                console.print(f"\n[red]Are you sure you want to drop schema '{schema_name}' and ALL its data?[/red]")
                if not click.confirm("This action cannot be undone"):
                    console.print("[yellow]Operation cancelled.[/yellow]")
                    await connection.close()
                    return
            
            # Drop the schema with CASCADE to remove all objects
            await connection.execute(f'DROP SCHEMA "{schema_name}" CASCADE')
            
            await connection.close()
            
            console.print(f"\n[green]✅ Schema '{schema_name}' dropped successfully[/green]")
            
        except asyncpg.exceptions.InsufficientPrivilegeError:
            console.print(f"[red]❌ Insufficient privileges to drop schema[/red]")
        except Exception as e:
            console.print(f"[red]❌ Error dropping schema: {e}[/red]")
    
    asyncio.run(run_drop_schema())

@cli.command()
@click.pass_context
def schema_info(ctx):
    """Show current schema configuration and table access."""
    async def run_schema_info():
        config = DatabaseConfig()
        schema_info = config.get_schema_info()
        
        console.print("[yellow]Schema Configuration:[/yellow]")
        console.print(f"  Current Schema: [cyan]{config.schema}[/cyan]")
        console.print(f"  Isolated Mode: [cyan]{schema_info['is_isolated']}[/cyan]")
        console.print(f"  Table Prefix: [cyan]{schema_info['qualified_prefix']}[/cyan]")
        
        # Show active schema from CLI context
        active_schema = ctx.obj.get('schema_name') if ctx.obj else None
        if active_schema:
            console.print(f"  CLI Override: [blue]{active_schema}[/blue]")
        
        try:
            connection = await asyncpg.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database
            )
            
            # Test table access in current schema
            tables_query = f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{config.schema}'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            
            tables = await connection.fetch(tables_query)
            
            console.print(f"\n[yellow]Tables in schema '{config.schema}':[/yellow]")
            if tables:
                for table in tables:
                    qualified_name = config.qualify_table(table['table_name'])
                    console.print(f"  • {qualified_name}")
            else:
                console.print("  [dim]No tables found[/dim]")
                
            await connection.close()
            
        except Exception as e:
            console.print(f"[red]❌ Error checking schema: {e}[/red]")
    
    asyncio.run(run_schema_info())

@cli.command()
@click.option('--kb-name', required=True, help='Knowledge base name')
@click.option('--run-once', is_flag=True, help='Run sync once instead of scheduled')
@click.pass_context
def sync(ctx, kb_name: str, run_once: bool):
    """Synchronize a knowledge base."""
    # Update command line params
    update_params(kb_name=kb_name, run_once=run_once)
    
    async def run_sync():
        db = await get_database()
        try:
            repository = Repository(db)
            
            # Check if KB exists first
            kb = await repository.get_knowledge_base_by_name(kb_name)
            if not kb:
                console.print(f"[red]Knowledge base '{kb_name}' not found[/red]")
                return
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task(f"Syncing {kb_name}...", total=100)
                
                runner = BatchRunner(repository)
                await runner.sync_knowledge_base(kb_name)
                
                progress.update(task, completed=100)
            
            console.print(f"[green]✓[/green] Successfully synchronized '{kb_name}'")
            
        except asyncpg.exceptions.UndefinedTableError as e:
            console.print(f"[red]Database tables are not initialized.[/red]")
            console.print("\n[yellow]The database exists but the schema hasn't been set up.[/yellow]")
            console.print("\n[cyan]Please run one of these commands:[/cyan]")
            console.print("  [cyan]document-loader create-db[/cyan]  # Will setup schema if database exists")
            console.print("  [cyan]document-loader setup[/cyan]      # Setup schema only")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        finally:
            await db.disconnect()
    
    console.print(Panel(f"[bold blue]Synchronizing knowledge base: {kb_name}[/bold blue]"))
    asyncio.run(run_sync())

@cli.command()
def list_kb():
    """List all knowledge bases."""
    async def run_list():
        db = await get_database()
        try:
            repository = Repository(db)
            kbs = await repository.list_knowledge_bases()
            
            if not kbs:
                console.print("[yellow]No knowledge bases found[/yellow]")
                return
            
            table = Table(
                title="Knowledge Bases",
                style="cyan",
                header_style="bold magenta",
            )
            table.add_column("Name", style="green")
            table.add_column("Source Type", style="blue")
            table.add_column("RAG Type", style="blue")
            table.add_column("Created", style="yellow")
            
            for kb in kbs:
                created_str = kb.created_at.strftime("%Y-%m-%d %H:%M") if kb.created_at else "N/A"
                table.add_row(
                    kb.name,
                    kb.source_type,
                    kb.rag_type,
                    created_str
                )
            
            console.print(table)
            
        except asyncpg.exceptions.UndefinedTableError as e:
            console.print(f"[red]Database tables are not initialized.[/red]")
            console.print("\n[yellow]The database exists but the schema hasn't been set up.[/yellow]")
            console.print("\n[cyan]Please run one of these commands:[/cyan]")
            console.print("  [cyan]document-loader create-db[/cyan]  # Will setup schema if database exists")
            console.print("  [cyan]document-loader setup[/cyan]      # Setup schema only")
            await db.disconnect()
            raise SystemExit(1)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            await db.disconnect()
            raise
        finally:
            await db.disconnect()
    
    asyncio.run(run_list())

@cli.command()
@click.option('--name', required=True, help='Knowledge base name')
@click.option('--source-type', 
              default='file_system', 
              help='Source type for documents. Available options: file_system, sharepoint (default: file_system)')
@click.option('--source-config', 
              required=True, 
              help='Source configuration as JSON (e.g., {"root_path": "/path/to/docs"} for file_system)')
@click.option('--rag-type', 
              default='mock', 
              help='RAG system type. Available options: mock, azure_blob, file_system_storage (default: mock)')
@click.option('--rag-config', 
              default='{}', 
              help='''RAG configuration as JSON. Structure depends on rag-type:
              
              \b
              For "file_system_storage":
              {
                "storage_path": "/path/to/storage",     # Base directory for documents
                "kb_name": "knowledge-base-name",       # Subdirectory name
                "create_dirs": true,                    # Auto-create directories (default: true)
                "preserve_structure": false,            # Keep original structure (default: false)
                "metadata_format": "json"               # Metadata format: "json" or "yaml" (default: "json")"
              }
              
              \b
              For "azure_blob":
              {
                "azure_tenant_id": "...",              # Or use env: AZURE_TENANT_ID
                "azure_subscription_id": "...",        # Or use env: AZURE_SUBSCRIPTION_ID  
                "azure_client_id": "...",              # Or use env: AZURE_CLIENT_ID
                "azure_client_secret": "...",          # Or use env: AZURE_CLIENT_SECRET
                "azure_resource_group_name": "...",    # Or use env: AZURE_RESOURCE_GROUP_NAME
                "azure_storage_account_name": "...",   # Or use env: AZURE_STORAGE_ACCOUNT_NAME
                "azure_storage_container_name": "..."  # Or use env: AZURE_STORAGE_CONTAINER_NAME
              }
              
              For "mock": {} (empty)
              ''')
@click.option('--force', is_flag=True, help='Skip validation checks and create without confirmation')
def create_kb(name: str, source_type: str, source_config: str, rag_type: str, rag_config: str, force: bool):
    """Create a new knowledge base.
    
    Examples:
    
    \b
    # File system source with mock RAG:
    document-loader create-kb \\
      --name "my-docs" \\
      --source-type "file_system" \\
      --source-config '{"root_path": "/path/to/documents"}' \\
      --rag-type "mock"
    
    \b
    # File system source with file system storage:
    document-loader create-kb \\
      --name "my-docs" \\
      --source-type "file_system" \\
      --source-config '{"root_path": "/path/to/documents"}' \\
      --rag-type "file_system_storage" \\
      --rag-config '{"storage_path": "/path/to/rag/storage", "kb_name": "my-docs"}'
    
    \b
    # SharePoint source with Azure Blob RAG:
    document-loader create-kb \\
      --name "sharepoint-docs" \\
      --source-type "sharepoint" \\
      --source-config '{"site_url": "https://company.sharepoint.com/sites/docs"}' \\
      --rag-type "azure_blob" \\
      --rag-config '{}'
    """
    async def run_create():
        db = await get_database()
        try:
            repository = Repository(db)
            
            # Validate and get user confirmation
            kb_config = await validate_and_confirm_kb_creation(
                name, source_type, source_config, rag_type, rag_config, repository, force
            )
            
            if not kb_config:
                console.print("[red]❌ Knowledge base creation cancelled due to validation errors.[/red]")
                return
            
            # Get user confirmation unless forced
            if not force:
                if not get_user_confirmation(
                    f"create knowledge base '{name}'",
                    "This will create a new knowledge base entry in the database."
                ):
                    console.print("[yellow]Operation cancelled by user.[/yellow]")
                    return
            
            # Create knowledge base from first source (backwards compatibility)
            source_def = kb_config['sources'][0]
            kb = KnowledgeBase(
                name=name,
                source_type=source_def['source_type'],
                source_config=source_def['source_config'],
                rag_type=kb_config['rag_type'],
                rag_config=kb_config['rag_config']
            )
            
            with console.status("[bold green]Creating knowledge base..."):
                kb_id = await repository.create_knowledge_base(kb)
            
            console.print(f"\n[green]✅ Created knowledge base '[bold]{name}[/bold]' with ID {kb_id}[/green]")
            
        except asyncpg.exceptions.UndefinedTableError as e:
            console.print(f"[red]Database tables are not initialized.[/red]")
            console.print("\n[yellow]The database exists but the schema hasn't been set up.[/yellow]")
            console.print("\n[cyan]Please run one of these commands:[/cyan]")
            console.print("  [cyan]document-loader create-db[/cyan]  # Will setup schema if database exists")
            console.print("  [cyan]document-loader setup[/cyan]      # Setup schema only")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        finally:
            await db.disconnect()
    
    asyncio.run(run_create())

@cli.command()
@click.option('--name', required=True, help='Knowledge base name')
@click.option('--source-type', 
              help='New source type. Available options: file_system, sharepoint')
@click.option('--source-config', 
              help='New source configuration as JSON')
def update_kb(name: str, source_type: str, source_config: str):
    """Update source configuration of an existing knowledge base.
    
    Note: RAG type and RAG configuration are immutable and cannot be changed.
    Only source type and source configuration can be updated.
    
    Examples:
    
    \b
    # Update source type only:
    document-loader update-kb \\
      --name "my-docs" \\
      --source-type "sharepoint"
    
    \b
    # Update source configuration only:
    document-loader update-kb \\
      --name "my-docs" \\
      --source-config '{"root_path": "/new/path/to/documents"}'
    
    \b
    # Update both source type and configuration:
    document-loader update-kb \\
      --name "my-docs" \\
      --source-type "file_system" \\
      --source-config '{"root_path": "/updated/path/to/documents"}'
    """
    async def run_update():
        db = await get_database()
        try:
            repository = Repository(db)
            
            # Check if KB exists first
            kb = await repository.get_knowledge_base_by_name(name)
            if not kb:
                console.print(f"[red]Knowledge base '{name}' not found[/red]")
                return
            
            # Build updates dictionary
            updates = {}
            
            if source_type:
                updates['source_type'] = source_type
            
            if source_config:
                try:
                    source_config_dict = json.loads(source_config)
                    # Basic validation - ensure it's a dictionary
                    if not isinstance(source_config_dict, dict):
                        console.print(f"[red]Source config must be a JSON object[/red]")
                        return
                    updates['source_config'] = source_config_dict
                except json.JSONDecodeError as e:
                    console.print(f"[red]Error parsing source config JSON: {e}[/red]")
                    return
            
            # Validate updates
            validation_result = await validate_kb_update(name, updates, repository)
            if not validation_result.is_valid:
                console.print(f"\n[red]❌ Update validation failed:[/red]")
                for error in validation_result.errors:
                    console.print(f"  - {error.field}: {error.message}")
                return
            
            if not updates:
                console.print("[yellow]No updates provided. Use --source-type or --source-config[/yellow]")
                console.print("[dim]Note: RAG type and RAG config are immutable and cannot be updated[/dim]")
                return
            
            # Display current configuration
            console.print(Panel.fit(
                f"[bold]Current Configuration[/bold]\n\n"
                f"Name: [green]{kb.name}[/green]\n"
                f"Source Type: [blue]{kb.source_type}[/blue]\n"
                f"RAG Type: [blue]{kb.rag_type}[/blue] [dim](immutable)[/dim]",
                title="Knowledge Base",
                border_style="blue"
            ))
            
            # Display proposed changes
            console.print("\n[bold]Proposed Changes:[/bold]")
            if 'source_type' in updates:
                console.print(f"  Source Type: [red]{kb.source_type}[/red] → [green]{updates['source_type']}[/green]")
            if 'source_config' in updates:
                console.print("  Source Config: [green]Updated[/green]")
                syntax = Syntax(json.dumps(updates['source_config'], indent=2), "json", theme="monokai")
                console.print(syntax)
            
            # Confirm update
            if not click.confirm("\nDo you want to apply these changes?"):
                console.print("[yellow]Update cancelled[/yellow]")
                return
            
            # Apply updates
            with console.status("[bold green]Updating knowledge base..."):
                success = await repository.update_knowledge_base(name, updates)
            
            if success:
                console.print(f"\n[green]✓[/green] Successfully updated knowledge base '[bold]{name}[/bold]'")
            else:
                console.print(f"[red]Failed to update knowledge base '{name}'[/red]")
            
        except asyncpg.exceptions.UndefinedTableError as e:
            console.print(f"[red]Database tables are not initialized.[/red]")
            console.print("\n[yellow]The database exists but the schema hasn't been set up.[/yellow]")
            console.print("\n[cyan]Please run one of these commands:[/cyan]")
            console.print("  [cyan]document-loader create-db[/cyan]  # Will setup schema if database exists")
            console.print("  [cyan]document-loader setup[/cyan]      # Setup schema only")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        finally:
            await db.disconnect()
    
    asyncio.run(run_update())

@cli.command()
@click.argument('name')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def delete_kb(name: str, force: bool):
    """Delete a knowledge base and all its associated data.
    
    This command will delete:
    - The knowledge base configuration
    - All sync run history
    - All file records for this knowledge base
    
    Examples:
    
    \b
    # Delete with confirmation prompt
    document-loader delete-kb "my-kb"
    
    \b
    # Delete without confirmation (use with caution)
    document-loader delete-kb "my-kb" --force
    """
    async def run_delete():
        db = await get_database()
        try:
            repository = Repository(db)
            
            # Check if KB exists
            kb = await repository.get_knowledge_base_by_name(name)
            if not kb:
                console.print(f"[red]Knowledge base '{name}' not found[/red]")
                return
            
            # Show KB info before deletion
            console.print(Panel.fit(
                f"[bold red]Deleting Knowledge Base[/bold red]\n\n"
                f"Name: [yellow]{kb.name}[/yellow]\n"
                f"Source Type: [blue]{kb.source_type}[/blue]\n"
                f"RAG Type: [blue]{kb.rag_type}[/blue]\n"
                f"Created: [green]{kb.created_at.strftime('%Y-%m-%d %H:%M') if kb.created_at else 'N/A'}[/green]",
                title="⚠️  WARNING",
                border_style="red"
            ))
            
            # Get statistics about what will be deleted
            try:
                sync_runs = await db.fetch(
                    "SELECT COUNT(*) as count FROM sync_run WHERE knowledge_base_id = $1",
                    kb.id
                )
                file_records = await db.fetch(
                    "SELECT COUNT(*) as count FROM file_record WHERE knowledge_base_id = $1", 
                    kb.id
                )
                
                sync_count = sync_runs[0]['count'] if sync_runs else 0
                file_count = file_records[0]['count'] if file_records else 0
                
                console.print(f"\n[bold]This will delete:[/bold]")
                console.print(f"  • Knowledge base configuration")
                console.print(f"  • {sync_count} sync run records")
                console.print(f"  • {file_count} file records")
                console.print(f"\n[red]This action cannot be undone![/red]")
                
            except Exception as e:
                console.print(f"[yellow]Warning: Could not get deletion statistics: {e}[/yellow]")
            
            # Confirmation
            if not force:
                if not click.confirm(f"\nAre you sure you want to delete knowledge base '{name}'?"):
                    console.print("[yellow]Deletion cancelled[/yellow]")
                    return
            
            # Perform deletion in transaction
            with console.status("[bold red]Deleting knowledge base..."):
                async with db.pool.acquire() as conn:
                    async with conn.transaction():
                        # Delete in correct order (due to foreign key constraints)
                        
                        # 1. Delete file records
                        await conn.execute(
                            "DELETE FROM file_record WHERE knowledge_base_id = $1",
                            kb.id
                        )
                        
                        # 2. Delete sync runs  
                        await conn.execute(
                            "DELETE FROM sync_run WHERE knowledge_base_id = $1",
                            kb.id
                        )
                        
                        # 3. Delete knowledge base
                        await conn.execute(
                            "DELETE FROM knowledge_base WHERE id = $1",
                            kb.id
                        )
            
            console.print(f"\n[green]✓[/green] Knowledge base '[bold]{name}[/bold]' has been deleted successfully")
            console.print("[dim]All associated sync runs and file records have been removed[/dim]")
            
        except asyncpg.exceptions.UndefinedTableError as e:
            console.print(f"[red]Database tables are not initialized.[/red]")
            console.print("\n[yellow]The database exists but the schema hasn't been set up.[/yellow]")
            console.print("\n[cyan]Please run one of these commands:[/cyan]")
            console.print("  [cyan]document-loader create-db[/cyan]  # Will setup schema if database exists")
            console.print("  [cyan]document-loader setup[/cyan]      # Setup schema only")
        except Exception as e:
            console.print(f"[red]Error deleting knowledge base: {str(e)}[/red]")
        finally:
            await db.disconnect()
    
    asyncio.run(run_delete())

@cli.command()
def setup():
    """Set up the database schema."""
    async def run_setup():
        db = await get_database()
        try:
            with console.status("[bold green]Creating database schema..."):
                schema_sql = create_schema_sql()
                
                # Execute SQL statements one by one
                statements = schema_sql.split(';')
                for i, statement in enumerate(statements):
                    if statement.strip():
                        await db.execute(statement)
                        console.print(f"[dim]Executed statement {i+1}/{len(statements)}[/dim]")
            
            console.print("[green]✓[/green] Database schema created successfully")
            
        except Exception as e:
            console.print(f"[red]Error creating schema: {e}[/red]")
        finally:
            await db.disconnect()
    
    console.print(Panel(
        "[bold blue]Database Setup[/bold blue]\n\n"
        "This will create all necessary tables and indexes.",
        expand=False
    ))
    asyncio.run(run_setup())

@cli.command()
@click.argument('kb-name')
def info(kb_name: str):
    """Show detailed information about a knowledge base."""
    async def show_info():
        db = await get_database()
        try:
            repository = ExtendedRepository(db)
            kb = await repository.get_knowledge_base_by_name(kb_name)
            
            if not kb:
                console.print(f"[red]Knowledge base '{kb_name}' not found[/red]")
                return
            
            # Get last sync run info
            last_sync = await repository.get_last_sync_run(kb.id)
            
            # Create info panel
            info_text = f"""[bold green]{kb.name}[/bold green]

[bold]Configuration:[/bold]
Source Type: [blue]{kb.source_type}[/blue]
RAG Type: [blue]{kb.rag_type}[/blue]
Created: [yellow]{kb.created_at.strftime("%Y-%m-%d %H:%M") if kb.created_at else "N/A"}[/yellow]
Updated: [yellow]{kb.updated_at.strftime("%Y-%m-%d %H:%M") if kb.updated_at else "N/A"}[/yellow]

[bold]Last Sync:[/bold]"""
            
            if last_sync:
                info_text += f"""
Status: {_get_status_badge(last_sync.status)}
Start: [yellow]{last_sync.start_time.strftime("%Y-%m-%d %H:%M")}[/yellow]
End: [yellow]{last_sync.end_time.strftime("%Y-%m-%d %H:%M") if last_sync.end_time else "In Progress"}[/yellow]
Files: [green]{last_sync.new_files or 0}[/green] new, [blue]{last_sync.modified_files or 0}[/blue] modified, [red]{last_sync.deleted_files or 0}[/red] deleted"""
            else:
                info_text += "\n[dim]No sync runs yet[/dim]"
            
            info_text += "\n\n[bold]Source Configuration:[/bold]"
            
            console.print(Panel(info_text, title="Knowledge Base Information", expand=False))
            
            syntax = Syntax(json.dumps(kb.source_config, indent=2), "json", theme="monokai")
            console.print(syntax)
            
            console.print("\n[bold]RAG Configuration:[/bold]")
            syntax = Syntax(json.dumps(kb.rag_config, indent=2), "json", theme="monokai")
            console.print(syntax)
            
        finally:
            await db.disconnect()
    
    asyncio.run(show_info())

@cli.command()
@click.argument('kb-name')
@click.option('--limit', default=10, help='Number of sync runs to show')
def status(kb_name: str, limit: int):
    """Show sync history for a knowledge base."""
    async def show_status():
        db = await get_database()
        try:
            repository = ExtendedRepository(db)
            kb = await repository.get_knowledge_base_by_name(kb_name)
            
            if not kb:
                console.print(f"[red]Knowledge base '{kb_name}' not found[/red]")
                return
            
            runs = await repository.get_sync_runs_for_kb(kb.id, limit=limit)
            
            if not runs:
                console.print(f"[yellow]No sync runs found for '{kb_name}'[/yellow]")
                return
            
            # Create status table
            table = Table(
                title=f"Sync History for {kb_name}",
                style="cyan",
                header_style="bold magenta",
            )
            table.add_column("Started", style="yellow")
            table.add_column("Duration", style="white")
            table.add_column("Status", style="white", justify="center")
            table.add_column("Files", style="green", justify="right")
            table.add_column("Changes", style="blue")
            
            for run in runs:
                start_str = run.start_time.strftime("%Y-%m-%d %H:%M")
                duration = "N/A"
                if run.end_time:
                    delta = run.end_time - run.start_time
                    duration = f"{delta.total_seconds():.1f}s"
                
                status = _get_status_badge(run.status)
                
                files = f"{run.total_files or 0}"
                changes = []
                if run.new_files:
                    changes.append(f"[green]+{run.new_files}[/green]")
                if run.modified_files:
                    changes.append(f"[blue]~{run.modified_files}[/blue]")
                if run.deleted_files:
                    changes.append(f"[red]-{run.deleted_files}[/red]")
                
                changes_str = " ".join(changes) if changes else "[dim]No changes[/dim]"
                
                table.add_row(start_str, duration, status, files, changes_str)
            
            console.print(table)
            
        finally:
            await db.disconnect()
    
    asyncio.run(show_status())

def _get_status_badge(status: str) -> str:
    """Get a colored badge for sync status."""
    if status == SyncRunStatus.COMPLETED.value:
        return "[green]✓ Completed[/green]"
    elif status == SyncRunStatus.RUNNING.value:
        return "[yellow]⟳ Running[/yellow]"
    elif status == SyncRunStatus.FAILED.value:
        return "[red]✗ Failed[/red]"
    elif status == SyncRunStatus.SCAN_COMPLETED.value:
        return "[blue]🔍 Scan Completed[/blue]"
    elif status == SyncRunStatus.SCAN_RUNNING.value:
        return "[cyan]🔍 Scanning[/cyan]"
    elif status == SyncRunStatus.SCAN_FAILED.value:
        return "[red]🔍 Scan Failed[/red]"
    else:
        return f"[dim]{status}[/dim]"

@cli.command()
@click.option('--path', help='Path to scan (overrides KB config if --kb-name is provided)')
@click.option('--source-type', 
              default='file_system', 
              help='Source type. Available options: file_system, sharepoint (default: file_system)')
@click.option('--source-config', 
              default='{}', 
              help='Additional source configuration as JSON')
@click.option('--table', is_flag=True, help='Show results in a table format')
@click.option('--recursive/--no-recursive', default=True, help='Scan recursively')
@click.option('--update-db', is_flag=True, help='Update database as if this were a real sync')
@click.option('--kb-name', help='Knowledge base name (uses KB config if --path not provided)')
@click.pass_context
def scan(ctx, path: str, source_type: str, source_config: str, table: bool, recursive: bool, update_db: bool, kb_name: str):
    """Scan files and calculate hashes.
    
    If --kb-name is provided without --path, uses the knowledge base configuration.
    If both are provided, --path overrides the KB config.
    
    Examples:
    
    \b
    # Scan local directory:
    document-loader scan \\
      --path "/path/to/documents" \\
      --source-type "file_system" \\
      --recursive
    
    \b
    # Scan using knowledge base config:
    document-loader scan \\
      --kb-name "my-docs" \\
      --table
    """
    # Update command line params
    update_params(
        path=path,
        source_type=source_type,
        source_config=json.loads(source_config) if source_config != '{}' else {},
        table=table,
        recursive=recursive,
        update_db=update_db,
        kb_name=kb_name
    )
    
    async def run_scan():
        db = None
        repository = None
        try:
            # Validate options
            if update_db and not kb_name:
                console.print("[red]Error: --kb-name is required when using --update-db[/red]")
                return
            
            if not path and not kb_name:
                console.print("[red]Error: Either --path or --kb-name must be provided[/red]")
                return
            
            # Parse source configuration
            config = json.loads(source_config)
            
            # Determine path and configuration
            actual_path = path  # Store the provided path
            actual_source_type = source_type
            
            # If kb_name is provided and no path, load KB config
            if kb_name and not actual_path:
                db = await get_database()
                repository = Repository(db)
                kb = await repository.get_knowledge_base_by_name(kb_name)
                if not kb:
                    console.print(f"[red]Error: Knowledge base '{kb_name}' not found[/red]")
                    return
                
                # Use KB configuration
                actual_source_type = kb.source_type
                config = kb.source_config.copy()
                
                # For file_system, root_path is already in config
                if actual_source_type == 'file_system':
                    # Don't override existing include_patterns from KB config
                    if 'include_patterns' not in config:
                        config['include_patterns'] = ['**'] if recursive else ['*']
                    actual_path = config.get('root_path', '.')
                else:
                    # SharePoint or other sources
                    config['recursive'] = recursive
                    actual_path = config.get('path', '/')
            else:
                # Set up path in config if provided directly
                if actual_source_type == 'file_system':
                    config['root_path'] = actual_path
                    # Don't override include_patterns if provided in config
                    if 'include_patterns' not in config:
                        config['include_patterns'] = ['**'] if recursive else ['*']
                else:
                    # SharePoint or other sources
                    config['path'] = actual_path
                    config['recursive'] = recursive
            
            # Create source
            factory = SourceFactory()
            source = factory.create(actual_source_type, config)
            
            # Create scanner
            scanner = FileScanner()
            
            # If updating DB, check knowledge base exists (if not already loaded)
            if update_db and not repository:
                db = await get_database()
                repository = Repository(db)
                kb = await repository.get_knowledge_base_by_name(kb_name)
                if not kb:
                    console.print(f"[red]Error: Knowledge base '{kb_name}' not found[/red]")
                    return
            
            console.print(Panel(
                f"[bold blue]Scanning files[/bold blue]\n\n"
                f"Path: [green]{actual_path}[/green]\n"
                f"Source: [yellow]{actual_source_type}[/yellow]\n"
                f"Recursive: [cyan]{'Yes' if recursive else 'No'}[/cyan]" +
                (f"\nUpdate DB: [cyan]Yes (KB: {kb_name})[/cyan]" if update_db else ""),
                expand=False
            ))
            
            # Debug: Print the configuration (commented out for cleaner output)
            # console.print(f"[dim]Debug - Source config: {config}[/dim]")
            
            if table:
                await scanner.print_summary_table(source, kb_name=kb_name if update_db else None)
            else:
                await scanner.scan_source(source, show_progress=not os.getenv('CI'), 
                                        kb_name=kb_name if update_db else None,
                                        repository=repository if update_db else None)
            
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing source configuration: {e}[/red]")
        except Exception as e:
            console.print(f"[red]Error during scan: {e}[/red]")
        finally:
            if db:
                await db.disconnect()
    
    asyncio.run(run_scan())

@cli.command()
@click.option('--kb-name', required=True, help='Knowledge base name to initialize')
def init_azure(kb_name: str):
    """Initialize Azure Blob Storage container for a knowledge base.
    
    This command creates the Azure storage account and blob container
    if they don't exist, using the configuration from the knowledge base.
    """
    async def run_init():
        db = await get_database()
        try:
            repository = Repository(db)
            
            # Get the knowledge base
            kb = await repository.get_knowledge_base_by_name(kb_name)
            if not kb:
                console.print(f"[red]Knowledge base '{kb_name}' not found[/red]")
                return
                
            # Check if it's an Azure Blob RAG type
            if kb.rag_type != 'azure_blob':
                console.print(f"[red]Knowledge base '{kb_name}' is not using Azure Blob storage (RAG type: {kb.rag_type})[/red]")
                return
            
            # Create the RAG system instance
            rag_factory = RAGFactory()
            rag_system = rag_factory.create(kb.rag_type, kb.rag_config)
            
            console.print(Panel(
                f"[bold blue]Initializing Azure Blob Storage[/bold blue]\n\n"
                f"Knowledge Base: [green]{kb_name}[/green]\n"
                f"RAG Type: [yellow]{kb.rag_type}[/yellow]",
                expand=False
            ))
            
            # Initialize the Azure Blob storage
            with console.status("[bold green]Initializing Azure resources..."):
                await rag_system.initialize()
            
            console.print("[green]✓[/green] Azure Blob Storage initialized successfully")
            console.print("\nYour Azure resources are ready!")
            console.print(f"You can now sync the knowledge base with: [cyan]document-loader sync --kb-name {kb_name}[/cyan]")
            
        except Exception as e:
            console.print(f"[red]Error initializing Azure Blob Storage: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        finally:
            await db.disconnect()
    
    asyncio.run(run_init())

@cli.command()
def quickstart():
    """Show a color-coded quick start guide."""
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.panel import Panel
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Document Loader - Quick Start Guide[/bold cyan]",
        border_style="blue"
    ))
    
    # Create a table for the commands
    table = Table(
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
        title_style="bold",
    )
    table.add_column("#", style="bold yellow", width=3)
    table.add_column("Command", style="bold green", no_wrap=True)
    table.add_column("Description", style="cyan")
    
    commands = [
        ("0", "./setup-database.sh", "Install PostgreSQL and set up database/users"),
        ("1", "document-loader check-connection", "Verify database connectivity"),
        ("2", "document-loader create-db", "Create database with schema"),
        ("3", "document-loader config upload \\\n  --file configs/my-config.json \\\n  --name my-config", "Upload config to PostgreSQL"),
        ("4", "document-loader multi-source create-multi-kb \\\n  --config-name my-config", "Create multi-source knowledge base"),
        ("5", "document-loader multi-source sync-multi-kb \\\n  --config-name my-config", "Sync documents from all sources"),
        ("6", "document-loader multi-source status-multi-kb \\\n  --config-name my-config", "Check sync status and statistics"),
        ("7", "document-loader config list", "List all stored configurations"),
        ("8", "document-loader --verbose multi-source sync-multi-kb \\\n  --config-name my-config", "Sync with debug output"),
    ]
    
    for num, cmd, desc in commands:
        table.add_row(num, cmd, desc)
    
    console.print(table)
    
    # Additional info panels
    console.print("\n")
    console.print(Panel(
        "[bold]Available RAG Types:[/bold]\n"
        "[green]mock[/green] - Testing and development\n"
        "[blue]azure_blob[/blue] - Azure Blob Storage\n"
        "[yellow]file_system_storage[/yellow] - Local file storage",
        title="RAG Systems",
        border_style="green",
        expand=False
    ))
    
    console.print("\n")
    console.print(Panel(
        "[bold]Available Source Types:[/bold]\n"
        "[green]file_system[/green] - Local file system\n"
        "[blue]sharepoint[/blue] - SharePoint documents\n"
        "[blue]enterprise_sharepoint[/blue] - Enterprise SharePoint\n"
        "[cyan]onedrive[/cyan] - OneDrive (personal/business)\n"
        "[yellow]Multi-source:[/yellow] Combine multiple sources in one KB",
        title="Document Sources",
        border_style="green",
        expand=False
    ))
    
    console.print("\n")
    console.print(Panel(
        "For detailed help on any command:\n"
        "[yellow]document-loader <command> --help[/yellow]\n"
        "[yellow]document-loader multi-source --help[/yellow]\n"
        "[yellow]document-loader config --help[/yellow]\n\n"
        "For verbose output (DEBUG logging):\n"
        "[yellow]document-loader --verbose <command>[/yellow]\n\n"
        "Examples:\n"
        "[yellow]document-loader multi-source create-multi-kb --help[/yellow]\n"
        "[yellow]document-loader config upload --help[/yellow]\n"
        "[yellow]document-loader --verbose multi-source sync-multi-kb --config-name my-config[/yellow]",
        title="Getting Help",
        border_style="cyan",
        expand=False
    ))

# Configuration management commands
@cli.command()
@click.argument('config_file')
@click.option('--name', help='Configuration name (defaults to filename)')
@click.option('--description', help='Configuration description')
@click.option('--created-by', help='Admin username (defaults to current user)')
def upload_config(config_file: str, name: str, description: str, created_by: str):
    """Upload a configuration file to PostgreSQL."""
    async def run_upload():
        try:
            config_manager = await create_config_manager()
            
            console.print(f"[yellow]Uploading configuration: {config_file}[/yellow]")
            
            result = await config_manager.upload_config_file(
                file_path=config_file,
                name=name,
                description=description,
                created_by=created_by
            )
            
            if result['status'] == 'unchanged':
                console.print(f"[yellow]⚠️  {result['message']}[/yellow]")
            else:
                console.print(f"[green]✅ {result['message']}[/green]")
                console.print(f"   Config ID: {result['config_id']}")
                console.print(f"   Version: {result['version']}")
                console.print(f"   Sources: {result['source_count']}")
                console.print(f"   RAG Type: {result['rag_type']}")
            
        except Exception as e:
            console.print(f"[red]❌ Upload failed: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_upload())

@cli.command()
@click.option('--status', default='active', type=click.Choice(['active', 'archived', 'draft']),
              help='Configuration status to list')
def list_configs(status: str):
    """List all stored configurations."""
    async def run_list():
        try:
            config_manager = await create_config_manager()
            configs = await config_manager.list_configs(status)
            
            if not configs:
                console.print(f"[yellow]No {status} configurations found[/yellow]")
                return
            
            table = Table(
                title=f"{status.upper()} CONFIGURATIONS",
                style="cyan",
                header_style="bold magenta",
            )
            table.add_column("Name", style="green")
            table.add_column("Version", style="blue", justify="center")
            table.add_column("Sources", style="blue", justify="center")
            table.add_column("RAG Type", style="yellow")
            table.add_column("Created By", style="white")
            table.add_column("Deployed", style="white", justify="center")
            
            for config in configs:
                deployed = "✅ Yes" if config['last_deployed_at'] else "⏸️  No"
                table.add_row(
                    config['name'],
                    str(config['version']),
                    str(config['source_count']),
                    config['rag_type'],
                    config['created_by'],
                    deployed
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(configs)} configurations[/dim]")
            
        except Exception as e:
            console.print(f"[red]❌ List failed: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_list())

@cli.command()
@click.argument('name')
@click.option('--version', type=int, help='Specific version to show')
@click.option('--show-full', is_flag=True, help='Show full configuration JSON')
def show_config(name: str, version: int, show_full: bool):
    """Show detailed configuration information."""
    async def run_show():
        try:
            config_manager = await create_config_manager()
            config = await config_manager.get_config(name, version)
            
            if not config:
                version_text = f" version {version}" if version else ""
                console.print(f"[red]❌ Configuration '{name}'{version_text} not found[/red]")
                return
            
            console.print(Panel(
                f"[bold green]{config['name']}[/bold green]\n\n"
                f"[bold]Configuration:[/bold]\n"
                f"Version: {config['version']}\n"
                f"Status: {config['status']}\n"
                f"Description: {config['description']}\n"
                f"Created by: {config['created_by']}\n"
                f"Created at: {config['created_at']}\n"
                f"File hash: {config['file_hash'][:16]}...",
                title="Configuration Details",
                border_style="blue"
            ))
            
            # Show configuration content
            config_content = config['config_content']
            console.print(f"\n[bold]Knowledge Base Config:[/bold]")
            console.print(f"Name: [green]{config_content['name']}[/green]")
            console.print(f"RAG Type: [blue]{config_content['rag_type']}[/blue]")
            console.print(f"Sources: [yellow]{len(config_content['sources'])}[/yellow]")
            
            console.print(f"\n[bold]Sources:[/bold]")
            for i, source in enumerate(config_content['sources'], 1):
                enabled = "✅" if source.get('enabled', True) else "⏸️ "
                console.print(f"  {i}. {enabled} {source['source_id']} ({source['source_type']})")
                if 'metadata_tags' in source and 'department' in source['metadata_tags']:
                    console.print(f"     Department: {source['metadata_tags']['department']}")
            
            if show_full:
                console.print(f"\n[bold]Full Configuration:[/bold]")
                syntax = Syntax(json.dumps(config_content, indent=2), "json", theme="monokai")
                console.print(syntax)
            
        except Exception as e:
            console.print(f"[red]❌ Show failed: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_show())

@cli.command()
@click.argument('name')
@click.option('--version', type=int, help='Specific version to deploy')
def deploy_config(name: str, version: int):
    """Deploy a configuration to create a knowledge base."""
    async def run_deploy():
        try:
            config_manager = await create_config_manager()
            
            # Get the configuration
            config = await config_manager.get_config(name, version)
            if not config:
                version_text = f" version {version}" if version else ""
                console.print(f"[red]❌ Configuration '{name}'{version_text} not found[/red]")
                return
            
            console.print(f"[yellow]🚀 Deploying configuration: {config['name']} v{config['version']}[/yellow]")
            
            # Create database connection for multi-source repository
            db_config = DatabaseConfig()
            db = Database(db_config)
            await db.connect()
            
            try:
                # Create multi-source KB from config
                config_content = config['config_content']
                multi_kb = create_multi_source_kb_from_config(config_content)
                
                # Save to database
                repo = MultiSourceRepository(db)
                kb_id = await repo.create_multi_source_kb(multi_kb)
                
                # Mark config as deployed
                await config_manager.mark_deployed(config['id'])
                
                console.print(f"[green]✅ Knowledge base created successfully![/green]")
                console.print(f"   KB ID: {kb_id}")
                console.print(f"   Name: {multi_kb.name}")
                console.print(f"   Sources: {len(multi_kb.sources)}")
                console.print(f"   Config marked as deployed")
                
            finally:
                await db.disconnect()
            
        except Exception as e:
            console.print(f"[red]❌ Deployment failed: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_deploy())

@cli.command()
@click.argument('name')
@click.argument('output_file')
@click.option('--version', type=int, help='Specific version to export')
def export_config(name: str, output_file: str, version: int):
    """Export a configuration to a file."""
    async def run_export():
        try:
            config_manager = await create_config_manager()
            
            success = await config_manager.export_config(name, output_file, version)
            
            if success:
                console.print(f"[green]✅ Configuration exported to: {output_file}[/green]")
            else:
                version_text = f" version {version}" if version else ""
                console.print(f"[red]❌ Configuration '{name}'{version_text} not found[/red]")
            
        except Exception as e:
            console.print(f"[red]❌ Export failed: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_export())

@cli.command()
@click.argument('name')
@click.option('--version', type=int, help='Specific version to delete')
@click.option('--force', is_flag=True, help='Skip confirmation')
def delete_config(name: str, version: int, force: bool):
    """Delete (archive) a configuration."""
    async def run_delete():
        try:
            if not force:
                version_text = f" version {version}" if version else ""
                if not click.confirm(f"Are you sure you want to delete '{name}'{version_text}?"):
                    console.print("[yellow]❌ Delete cancelled[/yellow]")
                    return
            
            config_manager = await create_config_manager()
            success = await config_manager.delete_config(name, version)
            
            if success:
                version_text = f" version {version}" if version else ""
                console.print(f"[green]✅ Configuration '{name}'{version_text} archived[/green]")
            else:
                console.print(f"[red]❌ Configuration not found[/red]")
            
        except Exception as e:
            console.print(f"[red]❌ Delete failed: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_delete())

@cli.command()
def config_summary():
    """Show configuration management summary."""
    async def run_summary():
        try:
            config_manager = await create_config_manager()
            summary = await config_manager.get_config_summary()
            
            console.print(Panel(
                f"[bold]Configuration Summary[/bold]\n\n"
                f"Total configurations: {summary.get('total_configs', 0)}\n"
                f"Active configurations: {summary.get('active_configs', 0)}\n"
                f"Archived configurations: {summary.get('archived_configs', 0)}\n"
                f"Deployed configurations: {summary.get('deployed_configs', 0)}\n"
                f"Average deployments: {summary.get('avg_deployments', 0):.1f}\n" +
                (f"Latest upload: {summary['latest_upload']}" if summary.get('latest_upload') else ""),
                title="📊 Configuration Statistics",
                border_style="cyan"
            ))
            
        except Exception as e:
            console.print(f"[red]❌ Summary failed: {e}[/red]")
            raise SystemExit(1)
    
    asyncio.run(run_summary())

# SharePoint Discovery Commands

@cli.command()
@click.argument('site_url')
@click.option('--tenant-id', help='Azure tenant ID (or use env: AZURE_TENANT_ID)')
@click.option('--client-id', help='Azure client ID (or use env: AZURE_CLIENT_ID)')
@click.option('--client-secret', help='Azure client secret (or use env: AZURE_CLIENT_SECRET)')
@click.option('--username', help='SharePoint username')
@click.option('--password', help='SharePoint password')
@click.option('--output', help='Output file to save discovery results as JSON')
@click.option('--verbose', is_flag=True, help='Show detailed information')
def discover_sharepoint(site_url: str, tenant_id: str, client_id: str, client_secret: str, 
                       username: str, password: str, output: str, verbose: bool):
    """Discover SharePoint site information from a URL.
    
    This command analyzes a SharePoint site and discovers:
    - Site metadata (ID, name, web ID)
    - Document libraries and their contents
    - Lists and their contents  
    - Site pages
    
    Examples:
    
    \b
    # Using service principal authentication:
    document-loader discover-sharepoint \\
      "https://company.sharepoint.com/sites/marketing" \\
      --tenant-id "your-tenant-id" \\
      --client-id "your-client-id" \\
      --client-secret "your-secret"
    
    \b
    # Using username/password:
    document-loader discover-sharepoint \\
      "https://company.sharepoint.com/sites/marketing" \\
      --username "user@company.com" \\
      --password "your-password"
    
    \b
    # Save results to file:
    document-loader discover-sharepoint \\
      "https://company.sharepoint.com/sites/marketing" \\
      --tenant-id "your-tenant-id" \\
      --client-id "your-client-id" \\
      --client-secret "your-secret" \\
      --output "site-discovery.json"
    """
    async def run_discovery():
        try:
            from src.utils.sharepoint_discovery import SharePointDiscovery
        except ImportError:
            console.print("[red]SharePoint discovery utilities not available[/red]")
            return
        
        # Build auth config from environment and parameters
        auth_config = {}
        
        # Try service principal auth first
        tenant_id = tenant_id or os.getenv('AZURE_TENANT_ID')
        client_id = client_id or os.getenv('AZURE_CLIENT_ID') 
        client_secret = client_secret or os.getenv('AZURE_CLIENT_SECRET')
        
        if all([tenant_id, client_id, client_secret]):
            auth_config = {
                'tenant_id': tenant_id,
                'client_id': client_id,
                'client_secret': client_secret
            }
        elif username and password:
            auth_config = {
                'username': username,
                'password': password
            }
        else:
            console.print("[red]Error: Authentication required[/red]")
            console.print("\n[yellow]Provide either:[/yellow]")
            console.print("  1. Service Principal: --tenant-id, --client-id, --client-secret")
            console.print("  2. User Credentials: --username, --password")
            console.print("\n[yellow]Or set environment variables:[/yellow]")
            console.print("  AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
            return
        
        try:
            console.print(Panel(
                f"[bold blue]Discovering SharePoint Site[/bold blue]\n\n"
                f"URL: [green]{site_url}[/green]\n"
                f"Auth: [yellow]{'Service Principal' if 'tenant_id' in auth_config else 'User Credentials'}[/yellow]",
                expand=False
            ))
            
            # Initialize discovery client
            discovery = SharePointDiscovery(auth_config)
            await discovery.initialize()
            
            # Discover site information
            with console.status("[bold green]Analyzing SharePoint site..."):
                site_info = await discovery.discover_site(site_url)
            
            # Print summary
            console.print("[green]✓[/green] Discovery completed successfully!")
            
            if verbose:
                summary = discovery.print_discovery_summary()
                console.print(summary)
            else:
                console.print(f"\n[bold]Site: [green]{site_info.site_name}[/green][/bold]")
                console.print(f"Site ID: [yellow]{site_info.site_id}[/yellow]")
                console.print(f"Libraries: [blue]{len(site_info.libraries)}[/blue]")
                console.print(f"Lists: [blue]{len(site_info.lists)}[/blue]")
                console.print(f"Pages: [blue]{len(site_info.pages)}[/blue]")
            
            # Save to file if requested
            if output:
                import json
                discovery_data = {
                    'site_info': {
                        'site_url': site_info.site_url,
                        'site_id': site_info.site_id,
                        'site_name': site_info.site_name,
                        'web_id': site_info.web_id,
                        'tenant_name': site_info.tenant_name
                    },
                    'libraries': site_info.libraries,
                    'lists': site_info.lists,
                    'pages': site_info.pages,
                    'discovered_at': datetime.utcnow().isoformat()
                }
                
                with open(output, 'w') as f:
                    json.dump(discovery_data, f, indent=2)
                
                console.print(f"\n[green]✓[/green] Discovery results saved to: [cyan]{output}[/cyan]")
            
            console.print(f"\n[bold cyan]Next steps:[/bold cyan]")
            console.print(f"1. Generate configuration: [yellow]document-loader generate-sharepoint-config[/yellow]")
            console.print(f"2. Create knowledge base with the generated config")
            
        except Exception as e:
            console.print(f"[red]Discovery failed: {e}[/red]")
            if verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    asyncio.run(run_discovery())

@cli.command()
@click.argument('site_url')
@click.option('--tenant-id', help='Azure tenant ID (or use env: AZURE_TENANT_ID)')
@click.option('--client-id', help='Azure client ID (or use env: AZURE_CLIENT_ID)')
@click.option('--client-secret', help='Azure client secret (or use env: AZURE_CLIENT_SECRET)')
@click.option('--username', help='SharePoint username')
@click.option('--password', help='SharePoint password')
@click.option('--libraries', help='Comma-separated list of library names to include (default: all)')
@click.option('--lists', help='Comma-separated list of list names to include (default: none)')
@click.option('--include-pages', is_flag=True, help='Include site pages')
@click.option('--output', help='Output file for generated configuration')
@click.option('--kb-name', help='Knowledge base name for the configuration')
@click.option('--rag-type', default='mock', help='RAG system type (default: mock)')
def generate_sharepoint_config(site_url: str, tenant_id: str, client_id: str, client_secret: str,
                              username: str, password: str, libraries: str, lists: str,
                              include_pages: bool, output: str, kb_name: str, rag_type: str):
    """Generate SharePoint source configuration from site discovery.
    
    This command discovers a SharePoint site and generates a complete
    configuration file that can be used to create a knowledge base.
    
    Examples:
    
    \b
    # Generate config for all libraries:
    document-loader generate-sharepoint-config \\
      "https://company.sharepoint.com/sites/marketing" \\
      --tenant-id "your-tenant-id" \\
      --client-id "your-client-id" \\
      --client-secret "your-secret" \\
      --kb-name "marketing-docs" \\
      --output "marketing-config.json"
    
    \b
    # Generate config for specific libraries:
    document-loader generate-sharepoint-config \\
      "https://company.sharepoint.com/sites/marketing" \\
      --username "user@company.com" \\
      --password "your-password" \\
      --libraries "Documents,Presentations" \\
      --kb-name "marketing-docs" \\
      --rag-type "azure_blob"
    """
    async def run_generate():
        try:
            from src.utils.sharepoint_discovery import SharePointDiscovery
        except ImportError:
            console.print("[red]SharePoint discovery utilities not available[/red]")
            return
        
        # Build auth config
        auth_config = {}
        
        # Try service principal auth first
        tenant_id = tenant_id or os.getenv('AZURE_TENANT_ID')
        client_id = client_id or os.getenv('AZURE_CLIENT_ID')
        client_secret = client_secret or os.getenv('AZURE_CLIENT_SECRET')
        
        if all([tenant_id, client_id, client_secret]):
            auth_config = {
                'tenant_id': tenant_id,
                'client_id': client_id,
                'client_secret': client_secret
            }
        elif username and password:
            auth_config = {
                'username': username,
                'password': password
            }
        else:
            console.print("[red]Error: Authentication required[/red]")
            return
        
        try:
            console.print(Panel(
                f"[bold blue]Generating SharePoint Configuration[/bold blue]\n\n"
                f"URL: [green]{site_url}[/green]\n"
                f"KB Name: [yellow]{kb_name or 'Auto-generated'}[/yellow]\n"
                f"RAG Type: [blue]{rag_type}[/blue]",
                expand=False
            ))
            
            # Initialize discovery and discover site
            discovery = SharePointDiscovery(auth_config)
            await discovery.initialize()
            
            with console.status("[bold green]Discovering site and generating configuration..."):
                site_info = await discovery.discover_site(site_url)
                
                # Parse library and list selections
                selected_libraries = None
                if libraries:
                    selected_libraries = [lib.strip() for lib in libraries.split(',')]
                
                selected_lists = None
                if lists:
                    selected_lists = [lst.strip() for lst in lists.split(',')]
                
                # Generate source configuration
                source_config = discovery.generate_source_config(
                    libraries=selected_libraries,
                    lists=selected_lists,
                    include_pages=include_pages
                )
                
                # Generate complete KB configuration
                kb_config = {
                    'name': kb_name or f"{site_info.site_name.lower().replace(' ', '-')}-kb",
                    'source_type': 'sharepoint',
                    'source_config': source_config,
                    'rag_type': rag_type,
                    'rag_config': {}
                }
            
            console.print("[green]✓[/green] Configuration generated successfully!")
            
            # Display configuration summary
            console.print(f"\n[bold]Configuration Summary:[/bold]")
            console.print(f"Knowledge Base: [green]{kb_config['name']}[/green]")
            console.print(f"Site: [yellow]{site_info.site_name}[/yellow]")
            console.print(f"Sources: [blue]{len(source_config['sources'])}[/blue]")
            
            if source_config['sources']:
                console.print("\n[bold]Included Sources:[/bold]")
                for source in source_config['sources']:
                    console.print(f"  - {source['title']} ({source['type']}, {source.get('item_count', 0)} items)")
            
            # Save or display configuration
            if output:
                import json
                with open(output, 'w') as f:
                    json.dump(kb_config, f, indent=2)
                console.print(f"\n[green]✓[/green] Configuration saved to: [cyan]{output}[/cyan]")
                
                console.print(f"\n[bold cyan]Next steps:[/bold cyan]")
                console.print(f"1. Review the configuration file: [yellow]{output}[/yellow]")
                console.print(f"2. Create knowledge base: [yellow]document-loader create-kb --name {kb_config['name']} --source-type sharepoint --source-config @{output} --rag-type {rag_type}[/yellow]")
            else:
                # Display configuration
                console.print(f"\n[bold]Generated Configuration:[/bold]")
                from rich.syntax import Syntax
                syntax = Syntax(json.dumps(kb_config, indent=2), "json", theme="monokai")
                console.print(syntax)
                
                console.print(f"\n[yellow]Tip:[/yellow] Use --output to save this configuration to a file")
            
        except Exception as e:
            console.print(f"[red]Configuration generation failed: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    asyncio.run(run_generate())

# Add multi-source commands to the CLI
cli.add_command(multi_source)

# Add config asset management commands to the CLI
from src.cli.config_commands import config
cli.add_command(config)

# Add database inspection commands to the CLI
from src.cli.db_commands import db
cli.add_command(db)

# Add analytics commands to the CLI
cli.add_command(analytics)

# Add scheduler commands to the CLI
from src.cli.scheduler_commands import scheduler
cli.add_command(scheduler)

# Add connectivity commands to the CLI
from src.cli.connectivity_commands import connectivity
cli.add_command(connectivity)

def main():
    """Entry point for the CLI."""
    import sys
    
    # Add ASCII art banner
    banner = r"""
====================================================
     ____                                        __  
    / __ \____  _______  ______ ___  ___  ____  / /_ 
   / / / / __ \/ ___/ / / / __ `__ \/ _ \/ __ \/ __/
  / /_/ / /_/ / /__/ /_/ / / / / / /  __/ / / / /_  
 /_____/\____/\___/\__,_/_/ /_/ /_/\___/_/ /_/\__/   
                                                     
        Document Loader for RAG Systems
====================================================
"""
    console.print(banner, style="bold blue")
    
    # Show colored help for both no arguments and --help
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h']):
        console.print("\n[bold]Document Management System for RAG systems[/bold]\n")
        console.print("[bold cyan]QUICK START:[/bold cyan]\n")
        
        steps = [
            ("0", "./setup-database.sh", "Install PostgreSQL and set up database/users"),
            ("1", "document-loader check-connection", "Verify database connectivity"),
            ("2", "document-loader create-schema --name finance-dept", "Create isolated schema for RAG use case"),
            ("3", "document-loader list-schemas", "List all RAG schemas"),
            ("4", "document-loader --schema finance-dept config upload \\\n     --file configs/my-config.json \\\n     --name my-config", "Upload config to specific schema"),
            ("5", "document-loader --schema finance-dept multi-source create-multi-kb \\\n     --config-name my-config", "Create knowledge base in isolated schema"),
            ("6", "document-loader --schema finance-dept multi-source sync-multi-kb \\\n     --config-name my-config", "Sync documents in isolated environment"),
            ("7", "document-loader --schema finance-dept list-schemas", "Check schema status and isolation"),
            ("8", "document-loader drop-schema --name finance-dept", "Clean up when done"),
        ]
        
        for num, cmd, desc in steps:
            console.print(f"[bold yellow]{num}.[/bold yellow] [bold green]{cmd}[/bold green]  [dim]# {desc}[/dim]\n")
        
        console.print("\n[bold cyan]AVAILABLE COMMANDS:[/bold cyan]")
        commands = [
            ("check-connection", "Test database connectivity"),
            ("create-schema", "Create schema for RAG use case"),
            ("list-schemas", "List all RAG schemas"),
            ("drop-schema", "Drop RAG schema and data"),
            ("schema-info", "Show current schema configuration"),
            ("create-db", "Create database and schema"),
            
            # Multi-Source Commands
            ("multi-source create-template", "Generate multi-source config template"),
            ("multi-source create-multi-kb", "Create multi-source knowledge base"),
            ("multi-source sync-multi-kb", "Sync multi-source knowledge base"),
            ("multi-source status-multi-kb", "Show multi-source KB status"),
            ("multi-source list-multi-kb", "List all multi-source KBs"),
            ("multi-source delete-multi-kb", "Delete multi-source KB and data"),
            
            # Config Asset Management
            ("config upload", "Upload configuration to PostgreSQL"),
            ("config list", "List stored configurations"),
            ("config show", "Show configuration details"),
            ("config export", "Export configuration to file"),
            ("config delete", "Delete stored configuration"),
            ("config stats", "Show configuration statistics"),
            
            # Database Inspection
            ("db tables", "List database tables with statistics"),
            ("db schema", "Show complete database schema"),
            ("db sync-runs", "Show sync run history and status"),
            ("db files", "Show file records and processing status"),
            ("db registry", "Show registered source and RAG types"),
            ("db stats", "Show database statistics and health"),
            ("db integrity", "Check database integrity"),
            ("db cleanup", "Clean up orphaned records"),
            
            # Analytics Commands
            ("analytics knowledge-base", "Generate KB-specific analytics"),
            ("analytics business-summary", "Generate business-level analytics"),
            ("analytics trends", "Show performance trends"),
            
            # Scheduler Commands  
            ("scheduler start", "Start the config-based scheduler service"),
            ("scheduler stop", "Stop the scheduler service"),
            ("scheduler status", "Show scheduler status and active schedules"),
            ("scheduler executions", "Show recent scheduled executions"),
            ("scheduler trigger", "Manually trigger a scheduled sync"),
            ("scheduler reload", "Reload scheduler configurations"),
            ("scheduler schedule-info", "Show detailed schedule information"),
            
            # Connectivity Commands
            ("connectivity check", "Test RAG system connectivity with comprehensive tests"),
            
            # Legacy Single-Source Commands
            ("create-kb", "Create single-source knowledge base (legacy)"),
            ("list-kb", "List single-source knowledge bases"),
            ("info", "Show KB details"),
            ("status", "Show sync history"),
            ("scan", "Preview what will be synced"),
            ("sync", "Sync single-source KB documents"),
            ("init-azure", "Initialize Azure resources"),
            ("update-kb", "Update KB configuration"),
            ("delete-kb", "Delete knowledge base and data"),
            
            # SharePoint Discovery
            ("discover-sharepoint", "Discover SharePoint site from URL"),
            ("generate-sharepoint-config", "Generate SharePoint config from discovery"),
            
            ("quickstart", "Show color-coded guide"),
            ("--help", "Show this message and exit"),
        ]
        
        for cmd, desc in commands:
            console.print(f"  [green]{cmd:<20}[/green] {desc}")
        
        console.print("\n[bold cyan]OPTIONS:[/bold cyan]")
        console.print("  [green]--verbose[/green]            Enable verbose logging (DEBUG level)")
        console.print("  [green]--database, -d[/green]       Database name override (for multi-tenant deployments)")
        console.print("  [green]--schema, -s[/green]         Schema name for isolated RAG use cases")
        console.print("  [green]--version[/green]            Show the version and exit")
        console.print("  [green]--help[/green]               Show this message and exit")
        
        console.print("\n[bold cyan]ADDITIONAL INFO:[/bold cyan]")
        console.print("  [yellow]RAG types:[/yellow] mock | azure_blob | file_system_storage")
        console.print("  [yellow]Source types:[/yellow] file_system | sharepoint | onedrive | enterprise_sharepoint")
        console.print("  [yellow]Multi-source:[/yellow] Combine multiple sources in one knowledge base")
        console.print("  [yellow]Config storage:[/yellow] Store configurations in PostgreSQL as assets")
        
        console.print("\n[dim]For detailed help on any command:[/dim]")
        console.print("  [yellow]document-loader <command> --help[/yellow]")
        console.print("  [yellow]document-loader multi-source --help[/yellow]")
        console.print("  [yellow]document-loader config --help[/yellow]")
        console.print("\n[dim]Examples:[/dim]")
        console.print("  [yellow]document-loader create-schema --name finance-dept[/yellow]")
        console.print("  [yellow]document-loader --schema finance-dept list-schemas[/yellow]")
        console.print("  [yellow]document-loader multi-source create-multi-kb --help[/yellow]")
        console.print("  [yellow]document-loader config upload --help[/yellow]\n")
        return
    
    cli()

if __name__ == '__main__':
    main()