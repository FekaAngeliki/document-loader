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
from src.core.batch_runner import BatchRunner
from src.core.scanner import FileScanner
from src.data.schema import create_schema_sql
from src.core.factory import SourceFactory, RAGFactory

# Setup rich console
console = Console()

# Setup logging with rich handler
log_level = os.getenv('DOCUMENT_LOADER_LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

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
def cli():
    """Document Management System for RAG systems.
    
    Quick start:
    1. Check your database connection: document-loader check-connection
    2. Create database and schema: document-loader create-db
    3. Create a knowledge base: document-loader create-kb
    4. List knowledge bases: document-loader list-kb
    5. Initialize Azure storage (if using azure_blob): document-loader init-azure --kb-name <name>
    6. Update configuration: document-loader update-kb --name <name>
    7. Sync a knowledge base: document-loader sync --kb-name <name>
    
    For more help on any command: document-loader <command> --help
    """
    pass

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
def create_db(no_schema: bool):
    """Create the database and schema if they don't exist."""
    async def run_create():
        config = DatabaseConfig()
        
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
def check_connection():
    """Check database connectivity."""
    async def run_check():
        config = DatabaseConfig()
        
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
@click.option('--kb-name', required=True, help='Knowledge base name')
@click.option('--run-once', is_flag=True, help='Run sync once instead of scheduled')
def sync(kb_name: str, run_once: bool):
    """Synchronize a knowledge base."""
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
@click.option('--source-type', default='file_system', help='Source type (default: file_system)')
@click.option('--source-config', required=True, help='Source configuration as JSON')
@click.option('--rag-type', default='mock', help='RAG system type (default: mock)')
@click.option('--rag-config', default='{}', help='RAG configuration as JSON')
def create_kb(name: str, source_type: str, source_config: str, rag_type: str, rag_config: str):
    """Create a new knowledge base."""
    async def run_create():
        db = await get_database()
        try:
            repository = Repository(db)
            
            # Parse configurations
            try:
                source_config_dict = json.loads(source_config)
                rag_config_dict = json.loads(rag_config)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error parsing JSON configuration: {e}[/red]")
                await db.disconnect()
                return
            
            # Display configuration for confirmation
            console.print(Panel.fit(
                f"[bold]Creating Knowledge Base[/bold]\n\n"
                f"Name: [green]{name}[/green]\n"
                f"Source Type: [blue]{source_type}[/blue]\n"
                f"RAG Type: [blue]{rag_type}[/blue]",
                title="Configuration",
                border_style="blue"
            ))
            
            console.print("\n[bold]Source Configuration:[/bold]")
            syntax = Syntax(json.dumps(source_config_dict, indent=2), "json", theme="monokai")
            console.print(syntax)
            
            kb = KnowledgeBase(
                name=name,
                source_type=source_type,
                source_config=source_config_dict,
                rag_type=rag_type,
                rag_config=rag_config_dict
            )
            
            with console.status("[bold green]Creating knowledge base..."):
                kb_id = await repository.create_knowledge_base(kb)
            
            console.print(f"\n[green]✓[/green] Created knowledge base '[bold]{name}[/bold]' with ID {kb_id}")
            
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
@click.option('--source-type', help='New source type')
@click.option('--source-config', help='New source configuration as JSON')
@click.option('--rag-type', help='New RAG system type')
@click.option('--rag-config', help='New RAG configuration as JSON')
def update_kb(name: str, source_type: str, source_config: str, rag_type: str, rag_config: str):
    """Update an existing knowledge base configuration."""
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
                # Validate source type exists
                valid_source_types = await repository.get_source_types()
                if source_type not in [st['name'] for st in valid_source_types]:
                    console.print(f"[red]Invalid source type: '{source_type}'[/red]")
                    console.print(f"[yellow]Valid source types: {', '.join([st['name'] for st in valid_source_types])}[/yellow]")
                    return
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
            
            if rag_type:
                # Validate RAG type exists
                valid_rag_types = await repository.get_rag_types()
                if rag_type not in [rt['name'] for rt in valid_rag_types]:
                    console.print(f"[red]Invalid RAG type: '{rag_type}'[/red]")
                    console.print(f"[yellow]Valid RAG types: {', '.join([rt['name'] for rt in valid_rag_types])}[/yellow]")
                    return
                updates['rag_type'] = rag_type
            
            if rag_config:
                try:
                    rag_config_dict = json.loads(rag_config)
                    # Basic validation - ensure it's a dictionary
                    if not isinstance(rag_config_dict, dict):
                        console.print(f"[red]RAG config must be a JSON object[/red]")
                        return
                    updates['rag_config'] = rag_config_dict
                except json.JSONDecodeError as e:
                    console.print(f"[red]Error parsing RAG config JSON: {e}[/red]")
                    return
            
            if not updates:
                console.print("[yellow]No updates provided[/yellow]")
                return
            
            # Display current configuration
            console.print(Panel.fit(
                f"[bold]Current Configuration[/bold]\n\n"
                f"Name: [green]{kb.name}[/green]\n"
                f"Source Type: [blue]{kb.source_type}[/blue]\n"
                f"RAG Type: [blue]{kb.rag_type}[/blue]",
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
            if 'rag_type' in updates:
                console.print(f"  RAG Type: [red]{kb.rag_type}[/red] → [green]{updates['rag_type']}[/green]")
            if 'rag_config' in updates:
                console.print("  RAG Config: [green]Updated[/green]")
                syntax = Syntax(json.dumps(updates['rag_config'], indent=2), "json", theme="monokai")
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
@click.option('--source-type', default='file_system', help='Source type (file_system or sharepoint)')
@click.option('--source-config', default='{}', help='Additional source configuration as JSON')
@click.option('--table', is_flag=True, help='Show results in a table format')
@click.option('--recursive/--no-recursive', default=True, help='Scan recursively')
@click.option('--update-db', is_flag=True, help='Update database as if this were a real sync')
@click.option('--kb-name', help='Knowledge base name (uses KB config if --path not provided)')
def scan(path: str, source_type: str, source_config: str, table: bool, recursive: bool, update_db: bool, kb_name: str):
    """Scan files and calculate hashes.
    
    If --kb-name is provided without --path, uses the knowledge base configuration.
    If both are provided, --path overrides the KB config.
    """
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

def main():
    """Entry point for the CLI."""
    # Add ASCII art banner
    banner = """
╔═══════════════════════════════════════════════════════════╗
║       ____                                        __      ║
║      / __ \\____  _______  ______ ___  ___  ____  / /_     ║
║     / / / / __ \\/ ___/ / / / __ `__ \\/ _ \\/ __ \\/ __/     ║
║    / /_/ / /_/ / /__/ /_/ / / / / / /  __/ / / / /_       ║
║   /_____/\\____/\\___/\\__,_/_/ /_/ /_/\\___/_/ /_/\\__/      ║
║                                                           ║
║              [Document Loader for RAG Systems]            ║
╚═══════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold blue")
    cli()

if __name__ == '__main__':
    main()