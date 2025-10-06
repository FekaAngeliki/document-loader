"""
Database content inspection commands

Provides commands to view and inspect PostgreSQL database content including
tables, sync runs, file records, and system registry information.
"""

import click
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

from ..data.database import Database, DatabaseConfig
from ..data.repository import Repository
from ..data.multi_source_repository import MultiSourceRepository

console = Console()

async def get_database(database_name: str = None):
    """Get database connection."""
    config = DatabaseConfig(database_name)
    db = Database(config)
    await db.connect()
    return db

async def get_all_databases():
    """Get connections to all configured databases."""
    databases = {}
    available_dbs = DatabaseConfig.get_available_databases()
    
    for db_name in available_dbs:
        try:
            config = DatabaseConfig(db_name)
            db = Database(config)
            await db.connect()
            databases[db_name] = db
        except Exception as e:
            console.print(f"[red]Failed to connect to database '{db_name}': {e}[/red]")
    
    return databases

async def close_all_databases(databases: dict):
    """Close all database connections."""
    for db in databases.values():
        try:
            await db.disconnect()
        except Exception:
            pass

@click.group()
@click.option('--database', '-d', help='Target specific database name')
@click.option('--all-databases', '--all', is_flag=True, help='Run command on all databases')
@click.pass_context
def db(ctx, database: str, all_databases: bool):
    """Database content inspection commands."""
    # Store options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['database'] = database
    ctx.obj['all_databases'] = all_databases

@db.command()
def list_databases():
    """List all available database instances."""
    available_dbs = DatabaseConfig.get_available_databases()
    default_db = DatabaseConfig.get_default_database()
    
    if not available_dbs:
        console.print("[yellow]No databases configured[/yellow]")
        return
    
    table = Table(
        title="Available Database Instances",
        style="cyan",
        header_style="bold magenta",
        box=box.ROUNDED
    )
    table.add_column("Database Name", style="green")
    table.add_column("Status", style="blue", justify="center")
    table.add_column("Description", style="white")
    
    async def check_databases():
        for db_name in available_dbs:
            try:
                config = DatabaseConfig(db_name)
                # Try to connect briefly
                import asyncpg
                conn = await asyncpg.connect(config.get_connection_string())
                await conn.close()
                status = "[green]✓ Available[/green]"
            except Exception as e:
                status = f"[red]✗ Error[/red]"
            
            is_default = " (default)" if db_name == default_db else ""
            description = f"Host: {config.host}:{config.port}{is_default}"
            
            table.add_row(db_name, status, description)
        
        console.print(table)
        console.print(f"\n[bold]Total databases:[/bold] {len(available_dbs)}")
        console.print(f"[bold]Default database:[/bold] {default_db}")
    
    asyncio.run(check_databases())

@db.command()
@click.option('--with-counts', is_flag=True, help='Include row counts for each table')
@click.option('--with-sizes', is_flag=True, help='Include table sizes')
@click.pass_context
def tables(ctx, with_counts: bool, with_sizes: bool):
    """List all database tables with optional statistics."""
    async def run_tables():
        # Get database selection from context
        database_name = ctx.obj.get('database')
        all_databases = ctx.obj.get('all_databases')
        
        if all_databases:
            # Run on all databases
            databases = await get_all_databases()
            try:
                for db_name, database in databases.items():
                    console.print(f"\n[bold blue]Database: {db_name}[/bold blue]")
                    await _show_tables_for_database(database, db_name, with_counts, with_sizes)
            finally:
                await close_all_databases(databases)
        else:
            # Run on single database
            database = await get_database(database_name)
            try:
                db_display_name = database_name or DatabaseConfig.get_default_database()
                await _show_tables_for_database(database, db_display_name, with_counts, with_sizes)
            finally:
                await database.disconnect()
    
    asyncio.run(run_tables())

async def _show_tables_for_database(database, db_name: str, with_counts: bool, with_sizes: bool):
    """Show tables for a specific database."""
    try:
        # Get table information
        query = """
            SELECT 
                tablename as table_name,
                schemaname as schema_name
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """
        
        tables_info = await database.fetch(query)
        
        if not tables_info:
            console.print("[yellow]No tables found in the database[/yellow]")
            return
        
        # Create table display
        table = Table(
            title=f"Database Tables - {db_name}",
            style="cyan",
            header_style="bold magenta",
            box=box.ROUNDED
        )
        table.add_column("Table Name", style="green", no_wrap=True)
        
        if with_counts:
            table.add_column("Rows", style="blue", justify="right")
        if with_sizes:
            table.add_column("Size", style="yellow", justify="right")
        
        table.add_column("Description", style="white")
        
        # Table descriptions
        descriptions = {
            'knowledge_base': 'Single-source knowledge bases',
            'multi_source_knowledge_base': 'Multi-source knowledge bases',
            'sync_run': 'Synchronization run history',
            'file_record': 'Individual file tracking records',
            'source_type': 'Registered source implementations',
            'rag_type': 'Registered RAG system implementations',
            'config_asset': 'Stored configuration files',
            'config_deployment': 'Configuration deployment tracking',
            'source_definition': 'Source definitions within multi-source KBs'
        }
        
        for table_info in tables_info:
            table_name = table_info['table_name']
            row_data = [table_name]
            
            # Get row count if requested
            if with_counts:
                try:
                    count_result = await database.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    row_data.append(str(count_result))
                except Exception:
                    row_data.append("N/A")
            
            # Get table size if requested
            if with_sizes:
                try:
                    size_query = f"""
                        SELECT pg_size_pretty(pg_total_relation_size('{table_name}')) as size
                    """
                    size_result = await database.fetchval(size_query)
                    row_data.append(size_result or "N/A")
                except Exception:
                    row_data.append("N/A")
            
            # Add description
            description = descriptions.get(table_name, "Custom table")
            row_data.append(description)
            
            table.add_row(*row_data)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error retrieving table information for {db_name}: {e}[/red]")

@db.command()
def schema():
    """Show complete database schema structure."""
    async def run_schema():
        database = await get_database()
        try:
            # Get table and column information
            query = """
                SELECT 
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position,
                    COALESCE(
                        STRING_AGG(DISTINCT tc.constraint_type, ', '),
                        ''
                    ) as constraint_types
                FROM information_schema.columns c
                LEFT JOIN information_schema.key_column_usage kcu 
                    ON c.table_name = kcu.table_name 
                    AND c.column_name = kcu.column_name
                    AND c.table_schema = kcu.table_schema
                LEFT JOIN information_schema.table_constraints tc 
                    ON kcu.constraint_name = tc.constraint_name
                    AND kcu.table_schema = tc.table_schema
                WHERE c.table_schema = 'public'
                GROUP BY c.table_name, c.column_name, c.data_type, c.is_nullable, c.column_default, c.ordinal_position
                ORDER BY c.table_name, c.ordinal_position;
            """
            
            schema_info = await database.fetch(query)
            
            if not schema_info:
                console.print("[yellow]No schema information found[/yellow]")
                return
            
            # Group by table
            tables_schema = {}
            for row in schema_info:
                table_name = row['table_name']
                if table_name not in tables_schema:
                    tables_schema[table_name] = []
                
                if row['column_name']:  # Skip rows without column info
                    tables_schema[table_name].append({
                        'column': row['column_name'],
                        'type': row['data_type'],
                        'nullable': row['is_nullable'],
                        'default': row['column_default'],
                        'constraint': row['constraint_types']
                    })
            
            # Display schema for each table
            for table_name, columns in tables_schema.items():
                if not columns:
                    continue
                    
                table = Table(
                    title=f"Table: {table_name}",
                    style="blue",
                    header_style="bold white",
                    box=box.ROUNDED
                )
                table.add_column("Column", style="green")
                table.add_column("Type", style="yellow")
                table.add_column("Nullable", style="cyan", justify="center")
                table.add_column("Default", style="white")
                table.add_column("Constraint", style="magenta")
                
                for col in columns:
                    nullable = "✓" if col['nullable'] == 'YES' else "✗"
                    constraint = col['constraint'] or ""
                    default = col['default'] or ""
                    
                    table.add_row(
                        col['column'],
                        col['type'],
                        nullable,
                        default,
                        constraint
                    )
                
                console.print(table)
                console.print()  # Add spacing between tables
            
        except Exception as e:
            console.print(f"[red]Error retrieving schema information: {e}[/red]")
        finally:
            await database.disconnect()
    
    asyncio.run(run_schema())

@db.command()
@click.option('--kb-id', type=int, help='Filter by knowledge base ID')
@click.option('--kb-name', help='Filter by knowledge base name')
@click.option('--status', help='Filter by status (running, completed, failed)')
@click.option('--failed', is_flag=True, help='Show only failed sync runs')
@click.option('--limit', default=50, help='Limit number of results')
@click.option('--detailed', is_flag=True, help='Show detailed information')
def sync_runs(kb_id: int, kb_name: str, status: str, failed: bool, limit: int, detailed: bool):
    """Show sync run history and statistics."""
    async def run_sync_runs():
        database = await get_database()
        try:
            repository = Repository(database)
            
            # Build query conditions
            conditions = []
            params = []
            param_count = 0
            
            # Base query
            query = """
                SELECT 
                    sr.id,
                    sr.knowledge_base_id,
                    kb.name as kb_name,
                    sr.start_time,
                    sr.end_time,
                    sr.status,
                    sr.total_files,
                    sr.new_files,
                    sr.modified_files,
                    sr.deleted_files,
                    sr.error_message,
                    EXTRACT(EPOCH FROM (sr.end_time - sr.start_time)) as duration_seconds
                FROM sync_run sr
                JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
            """
            
            # Add filters
            if kb_id:
                param_count += 1
                conditions.append(f"sr.knowledge_base_id = ${param_count}")
                params.append(kb_id)
            
            if kb_name:
                param_count += 1
                conditions.append(f"kb.name = ${param_count}")
                params.append(kb_name)
            
            if status:
                param_count += 1
                conditions.append(f"sr.status = ${param_count}")
                params.append(status)
            
            if failed:
                param_count += 1
                conditions.append(f"sr.status = ${param_count}")
                params.append('failed')
            
            # Add WHERE clause if there are conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add ordering and limit
            query += f" ORDER BY sr.start_time DESC LIMIT ${param_count + 1}"
            params.append(limit)
            
            sync_runs_data = await database.fetch(query, *params)
            
            if not sync_runs_data:
                console.print("[yellow]No sync runs found matching the criteria[/yellow]")
                return
            
            # Create summary table
            table = Table(
                title=f"Sync Runs (Last {len(sync_runs_data)})",
                style="cyan",
                header_style="bold magenta",
                box=box.ROUNDED
            )
            table.add_column("ID", style="blue", justify="right")
            table.add_column("Knowledge Base", style="green")
            table.add_column("Started", style="yellow")
            table.add_column("Duration", style="white", justify="right")
            table.add_column("Status", style="white", justify="center")
            table.add_column("Files", style="cyan", justify="right")
            table.add_column("Changes", style="blue")
            
            if detailed:
                table.add_column("Error", style="red")
            
            for run in sync_runs_data:
                # Calculate duration
                duration = "N/A"
                if run['duration_seconds']:
                    duration = f"{run['duration_seconds']:.1f}s"
                elif run['end_time'] is None and run['status'] == 'running':
                    duration = "Running..."
                
                # Format status with colors
                status_display = run['status']
                if run['status'] == 'completed':
                    status_display = f"[green]{run['status']}[/green]"
                elif run['status'] == 'failed':
                    status_display = f"[red]{run['status']}[/red]"
                elif run['status'] == 'running':
                    status_display = f"[yellow]{run['status']}[/yellow]"
                
                # Format changes
                changes = []
                if run['new_files']:
                    changes.append(f"[green]+{run['new_files']}[/green]")
                if run['modified_files']:
                    changes.append(f"[blue]~{run['modified_files']}[/blue]")
                if run['deleted_files']:
                    changes.append(f"[red]-{run['deleted_files']}[/red]")
                changes_str = " ".join(changes) if changes else "[dim]No changes[/dim]"
                
                row_data = [
                    str(run['id']),
                    run['kb_name'],
                    run['start_time'].strftime("%Y-%m-%d %H:%M"),
                    duration,
                    status_display,
                    str(run['total_files'] or 0),
                    changes_str
                ]
                
                if detailed and run['error_message']:
                    # Truncate long error messages
                    error_msg = run['error_message']
                    if len(error_msg) > 50:
                        error_msg = error_msg[:47] + "..."
                    row_data.append(error_msg)
                elif detailed:
                    row_data.append("")
                
                table.add_row(*row_data)
            
            console.print(table)
            
            # Show summary statistics
            total_runs = len(sync_runs_data)
            completed = sum(1 for r in sync_runs_data if r['status'] == 'completed')
            failed_count = sum(1 for r in sync_runs_data if r['status'] == 'failed')
            running = sum(1 for r in sync_runs_data if r['status'] == 'running')
            
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"Total runs: {total_runs}")
            console.print(f"[green]Completed: {completed}[/green] | [red]Failed: {failed_count}[/red] | [yellow]Running: {running}[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Error retrieving sync runs: {e}[/red]")
        finally:
            await database.disconnect()
    
    asyncio.run(run_sync_runs())

@db.command()
@click.option('--kb-id', type=int, help='Filter by knowledge base ID')
@click.option('--kb-name', help='Filter by knowledge base name')
@click.option('--status', help='Filter by file status (new, modified, error, etc.)')
@click.option('--hash', help='Find files by specific hash')
@click.option('--duplicates', is_flag=True, help='Show only duplicate files (same hash)')
@click.option('--errors', is_flag=True, help='Show only files with errors')
@click.option('--limit', default=100, help='Limit number of results')
def files(kb_id: int, kb_name: str, status: str, hash: str, duplicates: bool, errors: bool, limit: int):
    """Show file records and their processing status."""
    async def run_files():
        database = await get_database()
        try:
            # Build query conditions
            conditions = []
            params = []
            param_count = 0
            
            if duplicates:
                # Query for duplicates
                query = """
                    SELECT 
                        fr.file_hash,
                        COUNT(*) as duplicate_count,
                        array_agg(fr.original_uri) as uris,
                        array_agg(kb.name) as kb_names
                    FROM file_record fr
                    JOIN sync_run sr ON fr.sync_run_id = sr.id
                    JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
                    GROUP BY fr.file_hash
                    HAVING COUNT(*) > 1
                    ORDER BY duplicate_count DESC
                    LIMIT $1
                """
                params = [limit]
            else:
                # Regular file query
                query = """
                    SELECT 
                        fr.id,
                        fr.original_uri,
                        fr.rag_uri,
                        fr.file_hash,
                        fr.uuid_filename,
                        fr.file_size,
                        fr.status,
                        fr.error_message,
                        fr.upload_time,
                        kb.name as kb_name,
                        sr.id as sync_run_id
                    FROM file_record fr
                    JOIN sync_run sr ON fr.sync_run_id = sr.id
                    JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
                """
                
                # Add filters
                if kb_id:
                    param_count += 1
                    conditions.append(f"sr.knowledge_base_id = ${param_count}")
                    params.append(kb_id)
                
                if kb_name:
                    param_count += 1
                    conditions.append(f"kb.name = ${param_count}")
                    params.append(kb_name)
                
                if status:
                    param_count += 1
                    conditions.append(f"fr.status = ${param_count}")
                    params.append(status)
                
                if hash:
                    param_count += 1
                    conditions.append(f"fr.file_hash = ${param_count}")
                    params.append(hash)
                
                if errors:
                    conditions.append(f"fr.error_message IS NOT NULL")
                
                # Add WHERE clause if there are conditions
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                # Add ordering and limit
                query += f" ORDER BY fr.upload_time DESC LIMIT ${param_count + 1}"
                params.append(limit)
            
            files_data = await database.fetch(query, *params)
            
            if not files_data:
                console.print("[yellow]No files found matching the criteria[/yellow]")
                return
            
            if duplicates:
                # Display duplicates table
                table = Table(
                    title="Duplicate Files",
                    style="red",
                    header_style="bold white",
                    box=box.ROUNDED
                )
                table.add_column("Hash", style="yellow")
                table.add_column("Count", style="red", justify="right")
                table.add_column("Knowledge Bases", style="green")
                table.add_column("Sample URIs", style="blue")
                
                for dup in files_data:
                    # Limit displayed URIs
                    uris = dup['uris'][:3]  # Show first 3 URIs
                    uri_display = "\n".join(uris)
                    if len(dup['uris']) > 3:
                        uri_display += f"\n... and {len(dup['uris']) - 3} more"
                    
                    kb_names = list(set(dup['kb_names']))  # Unique KB names
                    kb_display = ", ".join(kb_names)
                    
                    table.add_row(
                        dup['file_hash'][:16] + "...",
                        str(dup['duplicate_count']),
                        kb_display,
                        uri_display
                    )
                
                console.print(table)
            else:
                # Display regular files table
                table = Table(
                    title=f"File Records (Last {len(files_data)})",
                    style="cyan",
                    header_style="bold magenta",
                    box=box.ROUNDED
                )
                table.add_column("ID", style="blue", justify="right")
                table.add_column("Knowledge Base", style="green")
                table.add_column("Original URI", style="yellow")
                table.add_column("Status", style="white", justify="center")
                table.add_column("Size", style="cyan", justify="right")
                table.add_column("Hash", style="white")
                table.add_column("Upload Time", style="blue")
                
                if errors:
                    table.add_column("Error", style="red")
                
                for file_record in files_data:
                    # Format file size
                    size = file_record['file_size']
                    if size >= 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.1f}MB"
                    elif size >= 1024:
                        size_str = f"{size / 1024:.1f}KB"
                    else:
                        size_str = f"{size}B"
                    
                    # Format status with colors
                    status_display = file_record['status']
                    if file_record['status'] == 'uploaded':
                        status_display = f"[green]{file_record['status']}[/green]"
                    elif file_record['status'] == 'error':
                        status_display = f"[red]{file_record['status']}[/red]"
                    elif file_record['status'] == 'new':
                        status_display = f"[blue]{file_record['status']}[/blue]"
                    
                    # Truncate URI for display
                    uri = file_record['original_uri']
                    if len(uri) > 50:
                        uri = "..." + uri[-47:]
                    
                    row_data = [
                        str(file_record['id']),
                        file_record['kb_name'],
                        uri,
                        status_display,
                        size_str,
                        file_record['file_hash'][:16] + "...",
                        file_record['upload_time'].strftime("%Y-%m-%d %H:%M") if file_record['upload_time'] else "N/A"
                    ]
                    
                    if errors and file_record['error_message']:
                        error_msg = file_record['error_message']
                        if len(error_msg) > 50:
                            error_msg = error_msg[:47] + "..."
                        row_data.append(error_msg)
                    elif errors:
                        row_data.append("")
                    
                    table.add_row(*row_data)
                
                console.print(table)
                
                # Show summary
                if not duplicates:
                    total_size = sum(f['file_size'] for f in files_data)
                    if total_size >= 1024 * 1024 * 1024:
                        total_size_str = f"{total_size / (1024 * 1024 * 1024):.2f}GB"
                    elif total_size >= 1024 * 1024:
                        total_size_str = f"{total_size / (1024 * 1024):.1f}MB"
                    else:
                        total_size_str = f"{total_size / 1024:.1f}KB"
                    
                    console.print(f"\n[bold]Summary:[/bold]")
                    console.print(f"Files shown: {len(files_data)}")
                    console.print(f"Total size: {total_size_str}")
            
        except Exception as e:
            console.print(f"[red]Error retrieving file records: {e}[/red]")
        finally:
            await database.disconnect()
    
    asyncio.run(run_files())

@db.command()
def registry():
    """Show registered source and RAG system types."""
    async def run_registry():
        database = await get_database()
        try:
            # Get source types
            source_types = await database.fetch("""
                SELECT name, class_name, config_schema 
                FROM source_type 
                ORDER BY name
            """)
            
            # Get RAG types
            rag_types = await database.fetch("""
                SELECT name, class_name, config_schema 
                FROM rag_type 
                ORDER BY name
            """)
            
            # Display source types
            if source_types:
                source_table = Table(
                    title="Registered Source Types",
                    style="green",
                    header_style="bold white",
                    box=box.ROUNDED
                )
                source_table.add_column("Type Name", style="green")
                source_table.add_column("Implementation Class", style="blue")
                source_table.add_column("Config Schema", style="yellow")
                
                for source in source_types:
                    # Format schema for display
                    schema = json.loads(source['config_schema'])
                    properties = list(schema.get('properties', {}).keys())
                    schema_display = ", ".join(properties[:3])
                    if len(properties) > 3:
                        schema_display += f" (+{len(properties) - 3} more)"
                    
                    source_table.add_row(
                        source['name'],
                        source['class_name'].split('.')[-1],  # Just class name
                        schema_display or "No properties"
                    )
                
                console.print(source_table)
            
            # Display RAG types
            if rag_types:
                console.print()  # Add spacing
                rag_table = Table(
                    title="Registered RAG System Types",
                    style="blue",
                    header_style="bold white",
                    box=box.ROUNDED
                )
                rag_table.add_column("Type Name", style="blue")
                rag_table.add_column("Implementation Class", style="green")
                rag_table.add_column("Config Schema", style="yellow")
                
                for rag in rag_types:
                    # Format schema for display
                    schema = json.loads(rag['config_schema'])
                    properties = list(schema.get('properties', {}).keys())
                    schema_display = ", ".join(properties[:3])
                    if len(properties) > 3:
                        schema_display += f" (+{len(properties) - 3} more)"
                    
                    rag_table.add_row(
                        rag['name'],
                        rag['class_name'].split('.')[-1],  # Just class name
                        schema_display or "No properties"
                    )
                
                console.print(rag_table)
            
            # Summary
            console.print(f"\n[bold]Registry Summary:[/bold]")
            console.print(f"Source types: {len(source_types)}")
            console.print(f"RAG types: {len(rag_types)}")
            
        except Exception as e:
            console.print(f"[red]Error retrieving registry information: {e}[/red]")
        finally:
            await database.disconnect()
    
    asyncio.run(run_registry())

@db.command()
@click.pass_context
def stats(ctx):
    """Show overall database statistics and health."""
    async def run_stats():
        # Get database selection from context
        database_name = ctx.obj.get('database')
        all_databases = ctx.obj.get('all_databases')
        
        if all_databases:
            # Run on all databases
            databases = await get_all_databases()
            try:
                for db_name, database in databases.items():
                    console.print(f"\n[bold blue]Database: {db_name}[/bold blue]")
                    await _show_stats_for_database(database, db_name)
            finally:
                await close_all_databases(databases)
        else:
            # Run on single database
            database = await get_database(database_name)
            try:
                db_display_name = database_name or DatabaseConfig.get_default_database()
                await _show_stats_for_database(database, db_display_name)
            finally:
                await database.disconnect()
    
    asyncio.run(run_stats())

async def _show_stats_for_database(database, db_name: str):
    """Show stats for a specific database."""
    try:
        # Get database size
        db_size_query = """
            SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
        """
        db_size = await database.fetchval(db_size_query)
        
        # Get table counts
        tables_to_count = [
            'knowledge_base', 'sync_run', 'file_record', 
            'source_type', 'rag_type'
        ]
        
        counts = {}
        for table in tables_to_count:
            try:
                count = await database.fetchval(f"SELECT COUNT(*) FROM {table}")
                counts[table] = count
            except Exception:
                counts[table] = 0
        
        # Get recent activity
        recent_sync = await database.fetchval("""
            SELECT MAX(start_time) FROM sync_run
        """)
        
        recent_file = await database.fetchval("""
            SELECT MAX(upload_time) FROM file_record
        """)
        
        # Get sync success rate (last 30 days)
        success_stats = await database.fetchrow("""
            SELECT 
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_runs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs
            FROM sync_run 
            WHERE start_time >= NOW() - INTERVAL '30 days'
        """)
        
        # Display statistics
        console.print(Panel(
            f"[bold]Database Statistics - {db_name}[/bold]\n\n"
            f"Database size: [green]{db_size}[/green]\n"
            f"Knowledge bases: [blue]{counts.get('knowledge_base', 0)}[/blue]\n"
            f"Sync runs: [cyan]{counts.get('sync_run', 0)}[/cyan]\n"
            f"File records: [yellow]{counts.get('file_record', 0)}[/yellow]\n"
            f"Source types: [green]{counts.get('source_type', 0)}[/green]\n"
            f"RAG types: [blue]{counts.get('rag_type', 0)}[/blue]",
            title=f"📊 Database Overview - {db_name}",
            border_style="cyan"
        ))
        
        # Recent activity
        activity_info = "[bold]Recent Activity[/bold]\n"
        if recent_sync:
            activity_info += f"Last sync: [green]{recent_sync.strftime('%Y-%m-%d %H:%M')}[/green]\n"
        else:
            activity_info += "Last sync: [dim]No syncs recorded[/dim]\n"
        
        if recent_file:
            activity_info += f"Last file upload: [green]{recent_file.strftime('%Y-%m-%d %H:%M')}[/green]"
        else:
            activity_info += "Last file upload: [dim]No files recorded[/dim]"
        
        console.print(Panel(
            activity_info,
            title="⚡ Activity",
            border_style="green"
        ))
        
        # Success rate (last 30 days)
        if success_stats and success_stats['total_runs'] > 0:
            success_rate = (success_stats['successful_runs'] / success_stats['total_runs']) * 100
            console.print(Panel(
                f"[bold]Sync Performance (Last 30 Days)[/bold]\n\n"
                f"Total runs: [cyan]{success_stats['total_runs']}[/cyan]\n"
                f"Successful: [green]{success_stats['successful_runs']}[/green]\n"
                f"Failed: [red]{success_stats['failed_runs']}[/red]\n"
                f"Success rate: [{'green' if success_rate >= 90 else 'yellow' if success_rate >= 70 else 'red'}]{success_rate:.1f}%[/{'green' if success_rate >= 90 else 'yellow' if success_rate >= 70 else 'red'}]",
                title="📈 Performance",
                border_style="blue"
            ))
        
    except Exception as e:
        console.print(f"[red]Error retrieving database statistics for {db_name}: {e}[/red]")

@db.command()
def integrity():
    """Check database integrity and find potential issues."""
    async def run_integrity():
        database = await get_database()
        try:
            issues = []
            
            # Check for orphaned sync runs
            orphaned_sync_runs = await database.fetchval("""
                SELECT COUNT(*) FROM sync_run sr
                WHERE NOT EXISTS (
                    SELECT 1 FROM knowledge_base kb WHERE kb.id = sr.knowledge_base_id
                )
            """)
            
            if orphaned_sync_runs > 0:
                issues.append(f"[red]Orphaned sync runs: {orphaned_sync_runs}[/red]")
            
            # Check for orphaned file records
            orphaned_file_records = await database.fetchval("""
                SELECT COUNT(*) FROM file_record fr
                WHERE NOT EXISTS (
                    SELECT 1 FROM sync_run sr WHERE sr.id = fr.sync_run_id
                )
            """)
            
            if orphaned_file_records > 0:
                issues.append(f"[red]Orphaned file records: {orphaned_file_records}[/red]")
            
            # Check for sync runs without file records
            empty_sync_runs = await database.fetchval("""
                SELECT COUNT(*) FROM sync_run sr
                WHERE sr.status = 'completed' 
                AND NOT EXISTS (
                    SELECT 1 FROM file_record fr WHERE fr.sync_run_id = sr.id
                )
            """)
            
            if empty_sync_runs > 0:
                issues.append(f"[yellow]Completed sync runs with no files: {empty_sync_runs}[/yellow]")
            
            # Check for running sync runs older than 24 hours
            stale_running_syncs = await database.fetchval("""
                SELECT COUNT(*) FROM sync_run 
                WHERE status = 'running' 
                AND start_time < NOW() - INTERVAL '24 hours'
            """)
            
            if stale_running_syncs > 0:
                issues.append(f"[yellow]Stale running sync runs (>24h): {stale_running_syncs}[/yellow]")
            
            # Check for duplicate file hashes in same KB
            duplicate_files = await database.fetchval("""
                SELECT COUNT(*) FROM (
                    SELECT file_hash, sr.knowledge_base_id
                    FROM file_record fr
                    JOIN sync_run sr ON fr.sync_run_id = sr.id
                    GROUP BY file_hash, sr.knowledge_base_id
                    HAVING COUNT(*) > 1
                ) as duplicates
            """)
            
            if duplicate_files > 0:
                issues.append(f"[yellow]File hash groups with duplicates: {duplicate_files}[/yellow]")
            
            # Display results
            if issues:
                console.print(Panel(
                    "\n".join(issues),
                    title="⚠️  Database Integrity Issues",
                    border_style="red"
                ))
                
                console.print("\n[bold]Recommendations:[/bold]")
                if orphaned_sync_runs > 0 or orphaned_file_records > 0:
                    console.print("• Run [cyan]document-loader db cleanup[/cyan] to remove orphaned records")
                if stale_running_syncs > 0:
                    console.print("• Review and possibly reset stale running sync runs")
                if duplicate_files > 0:
                    console.print("• Check [cyan]document-loader db files --duplicates[/cyan] for details")
            else:
                console.print(Panel(
                    "[green]✓ No integrity issues found[/green]\n\n"
                    "Database appears to be in good health.",
                    title="✅ Database Integrity Check",
                    border_style="green"
                ))
            
        except Exception as e:
            console.print(f"[red]Error checking database integrity: {e}[/red]")
        finally:
            await database.disconnect()
    
    asyncio.run(run_integrity())

@db.command()
@click.option('--force', is_flag=True, help='Actually perform cleanup (dry run by default)')
def cleanup(force: bool):
    """Clean up orphaned records and fix data consistency issues."""
    async def run_cleanup():
        database = await get_database()
        try:
            if not force:
                console.print("[yellow]This is a dry run. Use --force to actually perform cleanup.[/yellow]\n")
            
            cleanup_actions = []
            
            # Find orphaned sync runs
            orphaned_sync_runs = await database.fetch("""
                SELECT sr.id, sr.knowledge_base_id FROM sync_run sr
                WHERE NOT EXISTS (
                    SELECT 1 FROM knowledge_base kb WHERE kb.id = sr.knowledge_base_id
                )
            """)
            
            if orphaned_sync_runs:
                cleanup_actions.append(f"Delete {len(orphaned_sync_runs)} orphaned sync runs")
                if force:
                    for run in orphaned_sync_runs:
                        await database.execute("DELETE FROM sync_run WHERE id = $1", run['id'])
            
            # Find orphaned file records
            orphaned_file_records = await database.fetch("""
                SELECT fr.id FROM file_record fr
                WHERE NOT EXISTS (
                    SELECT 1 FROM sync_run sr WHERE sr.id = fr.sync_run_id
                )
            """)
            
            if orphaned_file_records:
                cleanup_actions.append(f"Delete {len(orphaned_file_records)} orphaned file records")
                if force:
                    for record in orphaned_file_records:
                        await database.execute("DELETE FROM file_record WHERE id = $1", record['id'])
            
            # Reset stale running sync runs
            stale_running_syncs = await database.fetch("""
                SELECT id FROM sync_run 
                WHERE status = 'running' 
                AND start_time < NOW() - INTERVAL '24 hours'
            """)
            
            if stale_running_syncs:
                cleanup_actions.append(f"Reset {len(stale_running_syncs)} stale running sync runs to 'failed'")
                if force:
                    for sync in stale_running_syncs:
                        await database.execute("""
                            UPDATE sync_run 
                            SET status = 'failed', 
                                error_message = 'Reset due to stale running status',
                                end_time = NOW()
                            WHERE id = $1
                        """, sync['id'])
            
            # Display results
            if cleanup_actions:
                action_text = "\n".join(f"• {action}" for action in cleanup_actions)
                title = "🧹 Cleanup Actions " + ("Performed" if force else "Planned")
                style = "green" if force else "yellow"
                
                console.print(Panel(
                    action_text,
                    title=title,
                    border_style=style
                ))
                
                if not force:
                    console.print("\n[dim]Use --force to actually perform these actions.[/dim]")
                else:
                    console.print("\n[green]✓ Cleanup completed successfully![/green]")
            else:
                console.print(Panel(
                    "[green]✓ No cleanup needed[/green]\n\n"
                    "Database is already clean.",
                    title="✅ Database Cleanup",
                    border_style="green"
                ))
            
        except Exception as e:
            console.print(f"[red]Error during cleanup: {e}[/red]")
        finally:
            await database.disconnect()
    
    asyncio.run(run_cleanup())