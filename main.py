#!/usr/bin/env python3
"""
Document Management System for RAG - CLI Application
"""
import click
import asyncio
import logging
from pathlib import Path
import json

from src.data.database import Database, DatabaseConfig
from src.data.repository import Repository
from src.data.models import KnowledgeBase
from src.core.batch_runner import BatchRunner
from src.data.schema import create_schema_sql

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def get_database():
    """Get database connection."""
    config = DatabaseConfig()
    db = Database(config)
    await db.connect()
    return db

@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Document Management System for RAG systems."""
    pass

@cli.command()
@click.option('--kb-name', required=True, help='Knowledge base name')
@click.option('--run-once', is_flag=True, help='Run sync once instead of scheduled')
def sync(kb_name: str, run_once: bool):
    """Synchronize a knowledge base."""
    async def run_sync():
        db = await get_database()
        try:
            repository = Repository(db)
            runner = BatchRunner(repository)
            await runner.sync_knowledge_base(kb_name)
        finally:
            await db.disconnect()
    
    click.echo(f"Syncing knowledge base: {kb_name}")
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
                click.echo("No knowledge bases found")
                return
            
            click.echo("\nAvailable knowledge bases:")
            click.echo("-" * 40)
            for kb in kbs:
                click.echo(f"Name: {kb.name}")
                click.echo(f"  Source Type: {kb.source_type}")
                click.echo(f"  RAG Type: {kb.rag_type}")
                click.echo(f"  Created: {kb.created_at}")
                click.echo("-" * 40)
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
                click.echo(f"Error parsing JSON configuration: {e}")
                return
            
            kb = KnowledgeBase(
                name=name,
                source_type=source_type,
                source_config=source_config_dict,
                rag_type=rag_type,
                rag_config=rag_config_dict
            )
            
            kb_id = await repository.create_knowledge_base(kb)
            click.echo(f"Created knowledge base '{name}' with ID {kb_id}")
        finally:
            await db.disconnect()
    
    asyncio.run(run_create())

@cli.command()
def setup():
    """Set up the database schema."""
    async def run_setup():
        db = await get_database()
        try:
            schema_sql = create_schema_sql()
            
            # Execute SQL statements one by one
            statements = schema_sql.split(';')
            for statement in statements:
                if statement.strip():
                    await db.execute(statement)
            
            click.echo("Database schema created successfully")
        except Exception as e:
            click.echo(f"Error creating schema: {e}")
        finally:
            await db.disconnect()
    
    click.echo("Setting up database...")
    asyncio.run(run_setup())

if __name__ == '__main__':
    cli()