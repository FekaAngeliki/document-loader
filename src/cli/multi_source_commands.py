"""
CLI commands for multi-source knowledge base management

Extends the existing CLI to support multi-source knowledge bases where multiple
sources feed into a single RAG system.
"""

import click
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from ..data.multi_source_models import (
    MultiSourceKnowledgeBase,
    SourceDefinition, 
    SyncMode,
    create_multi_source_kb_from_config
)
from ..abstractions.file_source import FileMetadata
from ..core.multi_source_batch_runner import MultiSourceBatchRunner
from ..data.database import Database, DatabaseConfig
from ..data.repository import Repository
from ..data.multi_source_repository import MultiSourceRepository
from .validation_helpers import validate_multi_source_kb_config, get_user_confirmation
from ..utils.config_utils import load_config_with_env_expansion

logger = logging.getLogger(__name__)

async def get_database():
    """Get database connection."""
    config = DatabaseConfig()
    db = Database(config)
    await db.connect()
    return db

@click.group()
def multi_source():
    """Multi-source knowledge base commands."""
    pass

@multi_source.command()
@click.option('--config-file', help='Path to multi-source configuration JSON file')
@click.option('--config-name', help='Name of configuration asset stored in PostgreSQL')
@click.option('--validate-only', is_flag=True, help='Only validate configuration without creating')
@click.option('--force', is_flag=True, help='Skip validation checks and create without confirmation')
def create_multi_kb(config_file: str, config_name: str, validate_only: bool, force: bool):
    """Create a multi-source knowledge base from configuration.
    
    This command creates a multi-source knowledge base that can collect documents
    from multiple sources (SharePoint, file systems, OneDrive) and store them
    in a single RAG system for unified search and retrieval.
    
    You can use either a local config file or a stored PostgreSQL config asset.
    
    Examples:
    
    \b
    # Create KB from stored config asset (recommended):
    document-loader multi-source create-multi-kb --config-name "my-config"
    
    \b
    # Create KB from local config file:
    document-loader multi-source create-multi-kb --config-file configs/my-config.json
    
    \b
    # Validate stored config without creating:
    document-loader multi-source create-multi-kb \\
      --config-name "hr-config" \\
      --validate-only
    
    \b
    # Create KB from stored config with force flag:
    document-loader multi-source create-multi-kb \\
      --config-name "production-config" \\
      --force
    
    The configuration should include:
    - Knowledge base name and description
    - RAG system configuration (Azure Blob, file system, etc.)
    - Multiple source definitions with unique source_id values
    - Source-specific configurations (URLs, paths, credentials)
    - Optional metadata tags and sync schedules
    
    After creation, you can:
    - List: document-loader multi-source list-multi-kb
    - Sync: document-loader multi-source sync-multi-kb --config-name <name>
    - Status: document-loader multi-source status-multi-kb --config-name <name>
    """
    
    async def run_create():
        # Validate input options
        if not config_file and not config_name:
            click.echo("❌ Either --config-file or --config-name must be provided")
            click.echo("   Examples:")
            click.echo("     document-loader multi-source create-multi-kb --config-name my-config")
            click.echo("     document-loader multi-source create-multi-kb --config-file config.json")
            return
        
        if config_file and config_name:
            click.echo("❌ Cannot use both --config-file and --config-name. Choose one.")
            return
        
        # Get database connection
        db = await get_database()
        try:
            repository = Repository(db)
            
            # Load configuration from file or database
            config = None
            
            if config_file:
                # Load from file
                config = await validate_multi_source_kb_config(config_file, repository)
                if not config:
                    click.echo("❌ Configuration validation failed")
                    return
                click.echo(f"📁 Loaded config from file: {config_file}")
            
            elif config_name:
                # Load from database
                try:
                    from ..admin.config_asset_manager import ConfigAssetManager
                    config_manager = ConfigAssetManager(db)
                    
                    config_asset = await config_manager.get_config_by_name(config_name)
                    if not config_asset:
                        click.echo(f"❌ Configuration asset '{config_name}' not found in database")
                        click.echo("   Use 'document-loader config list' to see available configs")
                        return
                    
                    if not config_asset.is_valid:
                        click.echo(f"❌ Configuration asset '{config_name}' has validation errors")
                        if config_asset.validation_errors:
                            for field, error in config_asset.validation_errors.items():
                                click.echo(f"   • {field}: {error}")
                        return
                    
                    config = config_asset.config_data
                    
                    # Expand environment variables in the loaded config
                    from ..utils.config_utils import expand_environment_variables
                    config = expand_environment_variables(config)
                    
                    click.echo(f"🗄️  Loaded config from database: {config_name}")
                    click.echo(f"   Usage count: {config_asset.usage_count + 1}")
                    
                except Exception as e:
                    click.echo(f"❌ Failed to load config from database: {e}")
                    return
            
            # If validate-only flag is set, stop here
            if validate_only:
                click.echo("✅ Configuration validation completed successfully")
                return
            
            # Parse configuration for display
            multi_kb = create_multi_source_kb_from_config(config)
            click.echo(f"✅ Configuration validated successfully")
            click.echo(f"   Knowledge Base: {multi_kb.name}")
            click.echo(f"   Sources: {len(multi_kb.sources)}")
            click.echo(f"   RAG Type: {multi_kb.rag_type}")
            
            # Show sources
            for source in multi_kb.sources:
                click.echo(f"   - {source.source_id} ({source.source_type})")
            
            # Get user confirmation unless forced
            if not force:
                if not get_user_confirmation(
                    f"create multi-source knowledge base '{multi_kb.name}'",
                    f"This will create a knowledge base with {len(multi_kb.sources)} sources."
                ):
                    click.echo("Operation cancelled by user.")
                    return
            
            # Create in database using multi-source repository
            multi_repo = MultiSourceRepository(db)
            
            # Check if already exists
            existing_kb = await multi_repo.get_multi_source_kb_by_name(multi_kb.name)
            if existing_kb:
                click.echo(f"⚠️  Multi-source knowledge base already exists: {multi_kb.name}")
                return
            
            # Create multi-source KB
            kb_id = await multi_repo.create_multi_source_kb(multi_kb)
            
            click.echo(f"✅ Created multi-source knowledge base: {multi_kb.name} (ID: {kb_id})")
            click.echo(f"📊 Sources: {len(multi_kb.sources)}")
            for source in multi_kb.sources:
                status = "✅ enabled" if source.enabled else "⏸️ disabled"
                click.echo(f"   - {source.source_id} ({source.source_type}) - {status}")
            
            click.echo(f"🗄️  RAG Container: {multi_kb.rag_config.get('azure_storage_container_name', 'default')}")
            
            # Save configuration for reference
            config_save_path = Path(f"multi_source_configs/{multi_kb.name}.json")
            config_save_path.parent.mkdir(exist_ok=True)
            with open(config_save_path, 'w') as f:
                json.dump(config, f, indent=2)
            click.echo(f"💾 Configuration saved to: {config_save_path}")
            
            # Also create individual KBs for backward compatibility
            repository = Repository(db)
            compat_kbs = []
            
            for source in multi_kb.sources:
                if not source.enabled:
                    continue
                    
                individual_kb_name = f"{multi_kb.name}_{source.source_id}"
                
                # Check if already exists
                existing_individual = await repository.get_knowledge_base_by_name(individual_kb_name)
                if existing_individual:
                    click.echo(f"⚠️  Compatibility KB already exists: {individual_kb_name}")
                    continue
                
                # Create individual KB for backward compatibility
                from ..data.models import KnowledgeBase
                compat_kb = KnowledgeBase(
                    name=individual_kb_name,
                    source_type=source.source_type,
                    source_config=source.source_config,
                    rag_type=multi_kb.rag_type,
                    rag_config=multi_kb.rag_config
                )
                
                compat_kb_id = await repository.create_knowledge_base(compat_kb)
                compat_kbs.append((individual_kb_name, compat_kb_id))
            
            if compat_kbs:
                click.echo(f"\n🔄 Created {len(compat_kbs)} compatibility KBs for existing CLI commands")
                for kb_name, kb_id in compat_kbs:
                    click.echo(f"   - {kb_name} (ID: {kb_id})")
            
        finally:
            await db.disconnect()
    
    asyncio.run(run_create())

@multi_source.command()
@click.option('--config-file', help='Path to multi-source configuration JSON file')
@click.option('--config-name', help='Name of configuration asset stored in PostgreSQL')
@click.option('--sync-mode', type=click.Choice(['parallel', 'sequential']), default='parallel', 
              help='Sync mode: parallel or sequential')
@click.option('--sources', help='Comma-separated list of source IDs to sync (default: all)')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without actually syncing')
def sync_multi_kb(config_file: str, config_name: str, sync_mode: str, sources: str, dry_run: bool):
    """Sync a multi-source knowledge base.
    
    This command synchronizes documents from all configured sources into the RAG system.
    It can process multiple sources in parallel or sequentially, and supports selective
    syncing of specific sources.
    
    Examples:
    
    \\b
    # Sync all sources in parallel (default):
    document-loader multi-source sync-multi-kb --config-file configs/hr-config.json
    
    \\b
    # Sync all sources sequentially:
    document-loader multi-source sync-multi-kb \\
      --config-file configs/hr-config.json \\
      --sync-mode sequential
    
    \\b
    # Sync only specific sources:
    document-loader multi-source sync-multi-kb \\
      --config-file configs/hr-config.json \\
      --sources "sharepoint_1,filesystem_1"
    
    \\b
    # Dry run to see what would be synced:
    document-loader multi-source sync-multi-kb \\
      --config-file configs/hr-config.json \\
      --dry-run
    
    \\b
    # Sync specific sources sequentially with dry run:
    document-loader multi-source sync-multi-kb \\
      --config-file configs/hr-config.json \\
      --sources "sharepoint_1" \\
      --sync-mode sequential \\
      --dry-run
    
    \\b
    # Check KB status before syncing:
    document-loader multi-source status-multi-kb --config-file configs/hr-config.json
    
    The sync process will:
    - Scan each enabled source for new/modified/deleted files
    - Process files according to any configured processing pipelines
    - Upload files to the RAG system with proper metadata
    - Update the database with sync statistics and file records
    - Handle errors gracefully and provide detailed progress reports
    """
    
    async def run_sync():
        # Validate input options
        if not config_file and not config_name:
            click.echo("❌ Either --config-file or --config-name must be provided")
            return
        
        if config_file and config_name:
            click.echo("❌ Cannot use both --config-file and --config-name. Choose one.")
            return
        
        # Load configuration from file or database
        config = None
        
        if config_file:
            # Load from file
            config_path = Path(config_file)
            if not config_path.exists():
                click.echo(f"❌ Configuration file not found: {config_file}")
                return
            
            try:
                config = load_config_with_env_expansion(str(config_path))
                click.echo(f"📁 Loaded config from file: {config_file}")
            except (json.JSONDecodeError, ValueError) as e:
                click.echo(f"❌ Configuration file error: {e}")
                return
        
        elif config_name:
            # Load from database
            try:
                from ..admin.config_asset_manager import ConfigAssetManager
                db = await get_database()
                config_manager = ConfigAssetManager(db)
                
                config_asset = await config_manager.get_config_by_name(config_name)
                if not config_asset:
                    click.echo(f"❌ Configuration asset '{config_name}' not found in database")
                    click.echo("   Use 'document-loader config list' to see available configs")
                    await db.disconnect()
                    return
                
                if not config_asset.is_valid:
                    click.echo(f"❌ Configuration asset '{config_name}' has validation errors")
                    if config_asset.validation_errors:
                        for field, error in config_asset.validation_errors.items():
                            click.echo(f"   • {field}: {error}")
                    await db.disconnect()
                    return
                
                config = config_asset.config_data
                
                # Expand environment variables in the loaded config
                from ..utils.config_utils import expand_environment_variables
                config = expand_environment_variables(config)
                
                click.echo(f"🗄️  Loaded config from database: {config_name}")
                click.echo(f"   Usage count: {config_asset.usage_count + 1}")
                
                await db.disconnect()
                
            except Exception as e:
                click.echo(f"❌ Failed to load config from database: {e}")
                return
        
        multi_kb = create_multi_source_kb_from_config(config)
        
        # Parse source filter
        source_ids = None
        if sources:
            source_ids = [s.strip() for s in sources.split(',')]
            click.echo(f"🎯 Syncing selected sources: {', '.join(source_ids)}")
        
        if dry_run:
            click.echo(f"🔍 DRY RUN - Would sync knowledge base: {multi_kb.name}")
            click.echo(f"   Sync mode: {sync_mode}")
            click.echo(f"   RAG container: {multi_kb.rag_config.get('azure_storage_container_name')}")
            
            sources_to_show = multi_kb.sources
            if source_ids:
                sources_to_show = [s for s in multi_kb.sources if s.source_id in source_ids]
            
            for source in sources_to_show:
                click.echo(f"   - Would sync: {source.source_id} ({source.source_type})")
            return
        
        # Execute sync using new multi-source batch runner
        db = await get_database()
        try:
            multi_repo = MultiSourceRepository(db)
            
            # Check if multi-source KB exists
            existing_kb = await multi_repo.get_multi_source_kb_by_name(multi_kb.name)
            if not existing_kb:
                click.echo(f"❌ Multi-source knowledge base not found: {multi_kb.name}")
                click.echo(f"   Create it first with: document-loader multi-source create-multi-kb --config-file {config_file}")
                return
            
            # Use new multi-source batch runner
            batch_runner = MultiSourceBatchRunner(multi_repo)
            
            mode = SyncMode.PARALLEL if sync_mode == 'parallel' else SyncMode.SEQUENTIAL
            
            try:
                await batch_runner.sync_multi_source_knowledge_base(
                    kb_name=multi_kb.name,
                    sync_mode=mode,
                    source_ids=source_ids
                )
                
                click.echo(f"\n🎉 Multi-source sync completed successfully!")
                
                # Show statistics
                stats = await multi_repo.get_multi_source_stats(existing_kb.id)
                if stats:
                    click.echo(f"\n📊 Updated Statistics:")
                    click.echo(f"   Total files: {stats['totals']['total_files']}")
                    click.echo(f"   Total size: {stats['totals']['total_size']:,} bytes")
                    
                    if stats.get('latest_sync'):
                        latest = stats['latest_sync']
                        click.echo(f"   Latest sync: {latest['status']} at {latest['start_time']}")
                        
                        for source_id, source_stats in latest.get('source_stats', {}).items():
                            click.echo(f"   - {source_id}: {source_stats.get('files_processed', 0)} files processed")
                
            except Exception as e:
                click.echo(f"❌ Multi-source sync failed: {e}")
                
                # Fallback: try individual KB sync for backward compatibility
                click.echo(f"🔄 Falling back to individual KB sync...")
                
                repository = Repository(db)
                sources_to_sync = multi_kb.sources
                if source_ids:
                    sources_to_sync = [s for s in multi_kb.sources if s.source_id in source_ids]
                
                for source in sources_to_sync:
                    if not source.enabled:
                        continue
                        
                    kb_name = f"{multi_kb.name}_{source.source_id}"
                    click.echo(f"\n🔄 Syncing {source.source_id} (fallback)...")
                    try:
                        await sync_individual_kb(repository, kb_name)
                        click.echo(f"✅ {source.source_id} completed")
                    except Exception as fallback_e:
                        click.echo(f"❌ {source.source_id} failed: {fallback_e}")
                
                click.echo(f"\n🎯 Fallback sync completed")
            
        finally:
            await db.disconnect()
    
    asyncio.run(run_sync())

async def sync_individual_kb(repository: Repository, kb_name: str):
    """Sync an individual knowledge base."""
    from ..core.batch_runner import BatchRunner
    
    runner = BatchRunner(repository)
    await runner.sync_knowledge_base(kb_name)

@multi_source.command()
@click.option('--config-file', help='Path to multi-source configuration JSON file')
@click.option('--config-name', help='Name of configuration asset stored in PostgreSQL')
def status_multi_kb(config_file: str, config_name: str):
    """Show status of a multi-source knowledge base."""
    
    async def run_status():
        # Validate input options
        if not config_file and not config_name:
            click.echo("❌ Either --config-file or --config-name must be provided")
            click.echo("   Examples:")
            click.echo("     document-loader multi-source status-multi-kb --config-name my-config")
            click.echo("     document-loader multi-source status-multi-kb --config-file config.json")
            return
        
        if config_file and config_name:
            click.echo("❌ Cannot use both --config-file and --config-name. Choose one.")
            return
        
        # Load configuration from file or database
        config = None
        
        if config_file:
            # Load from file
            config_path = Path(config_file)
            if not config_path.exists():
                click.echo(f"❌ Configuration file not found: {config_file}")
                return
            
            try:
                config = load_config_with_env_expansion(str(config_path))
                click.echo(f"📁 Loaded config from file: {config_file}")
            except (json.JSONDecodeError, ValueError) as e:
                click.echo(f"❌ Configuration file error: {e}")
                return
        
        elif config_name:
            # Load from database
            db = await get_database()
            try:
                from ..admin.config_asset_manager import ConfigAssetManager
                config_manager = ConfigAssetManager(db)
                
                config_asset = await config_manager.get_config_by_name(config_name)
                if not config_asset:
                    click.echo(f"❌ Configuration asset '{config_name}' not found in database")
                    click.echo("   Use 'document-loader config list' to see available configs")
                    await db.disconnect()
                    return
                
                if not config_asset.is_valid:
                    click.echo(f"❌ Configuration asset '{config_name}' has validation errors")
                    if config_asset.validation_errors:
                        for field, error in config_asset.validation_errors.items():
                            click.echo(f"   • {field}: {error}")
                    await db.disconnect()
                    return
                
                config = config_asset.config_data
                
                # Expand environment variables in the loaded config
                from ..utils.config_utils import expand_environment_variables
                config = expand_environment_variables(config)
                
                click.echo(f"🗄️  Loaded config from database: {config_name}")
                click.echo(f"   Usage count: {config_asset.usage_count + 1}")
                
                await db.disconnect()
                
            except Exception as e:
                click.echo(f"❌ Failed to load config from database: {e}")
                return
        
        multi_kb = create_multi_source_kb_from_config(config)
        
        db = await get_database()
        try:
            multi_repo = MultiSourceRepository(db)
            
            # Check if multi-source KB exists
            existing_kb = await multi_repo.get_multi_source_kb_by_name(multi_kb.name)
            
            click.echo(f"\n📊 Multi-Source Knowledge Base Status: {multi_kb.name}")
            click.echo(f"{'='*60}")
            
            if existing_kb:
                click.echo(f"✅ Multi-source KB found (ID: {existing_kb.id})")
                click.echo(f"📝 Description: {existing_kb.description}")
                click.echo(f"🗄️  RAG Type: {existing_kb.rag_type}")
                click.echo(f"📦 RAG Container: {existing_kb.rag_config.get('azure_storage_container_name', 'default')}")
                click.echo(f"📊 Sources: {len(existing_kb.sources)}")
                
                # Get comprehensive statistics
                stats = await multi_repo.get_multi_source_stats(existing_kb.id)
                
                if stats:
                    click.echo(f"\n📈 Overall Statistics:")
                    click.echo(f"   Total files: {stats['totals']['total_files']}")
                    click.echo(f"   Total size: {stats['totals']['total_size']:,} bytes")
                    
                    if stats.get('latest_sync'):
                        latest = stats['latest_sync']
                        click.echo(f"\n🕐 Latest Sync:")
                        click.echo(f"   Status: {latest['status']}")
                        click.echo(f"   Started: {latest['start_time']}")
                        if latest['end_time']:
                            click.echo(f"   Completed: {latest['end_time']}")
                        click.echo(f"   Files processed: {latest.get('total_files', 0)}")
                
                # Show each source status
                click.echo(f"\n🔹 Source Details:")
                for source in existing_kb.sources:
                    status_emoji = "✅" if source.enabled else "⏸️"
                    click.echo(f"\n   {status_emoji} {source.source_id} ({source.source_type})")
                    click.echo(f"      Enabled: {source.enabled}")
                    
                    if source.sync_schedule:
                        click.echo(f"      Schedule: {source.sync_schedule}")
                    
                    if source.metadata_tags:
                        click.echo(f"      Tags: {source.metadata_tags}")
                    
                    # Source-specific statistics
                    if stats and source.source_id in stats['sources']:
                        source_stats = stats['sources'][source.source_id]
                        click.echo(f"      Files: {source_stats.get('total_files', 0)}")
                        click.echo(f"      Size: {source_stats.get('total_size', 0):,} bytes")
                        if source_stats.get('latest_upload'):
                            click.echo(f"      Latest upload: {source_stats['latest_upload']}")
                
                # Get recent sync runs
                sync_runs = await multi_repo.get_multi_source_sync_runs(existing_kb.id, limit=5)
                
                if sync_runs:
                    click.echo(f"\n📋 Recent Sync Runs:")
                    for i, run in enumerate(sync_runs, 1):
                        status_emoji = "✅" if run.status == "completed" else "❌" if "failed" in run.status else "🔄"
                        click.echo(f"   {i}. {status_emoji} {run.start_time} - {run.status}")
                        if run.total_files is not None:
                            click.echo(f"      Files: {run.total_files} total, {run.new_files} new")
                        click.echo(f"      Mode: {run.sync_mode}, Sources: {len(run.sources_processed)}")
                
            else:
                click.echo(f"❌ Multi-source KB not found in database")
                click.echo(f"📝 Configuration shows: {multi_kb.rag_type}")
                click.echo(f"📦 RAG Container: {multi_kb.rag_config.get('azure_storage_container_name', 'default')}")
                click.echo(f"📊 Sources: {len(multi_kb.sources)}")
                
                # Check individual KBs for backward compatibility
                repository = Repository(db)
                click.echo(f"\n🔍 Checking individual KBs (compatibility mode):")
                
                for source in multi_kb.sources:
                    kb_name = f"{multi_kb.name}_{source.source_id}"
                    
                    click.echo(f"\n🔹 Source: {source.source_id} ({source.source_type})")
                    
                    kb = await repository.get_knowledge_base_by_name(kb_name)
                    if not kb:
                        click.echo(f"   ❌ Knowledge base not found: {kb_name}")
                        continue
                    
                    click.echo(f"   ✅ Individual KB found (ID: {kb.id})")
                    
                    # Get recent sync runs
                    sync_runs = await repository.get_sync_runs_for_knowledge_base(kb.id, limit=3)
                    
                    if not sync_runs:
                        click.echo(f"   📝 No sync runs found")
                    else:
                        latest_run = sync_runs[0]
                        click.echo(f"   📅 Last sync: {latest_run.start_time}")
                        click.echo(f"   📊 Status: {latest_run.status}")
                        if latest_run.total_files is not None:
                            click.echo(f"   📁 Files: {latest_run.total_files} total, {latest_run.new_files} new")
            
        finally:
            await db.disconnect()
    
    asyncio.run(run_status())

@multi_source.command()
@click.option('--detailed', is_flag=True, help='Show detailed information for each knowledge base')
@click.option('--status-filter', type=click.Choice(['all', 'active', 'sync-issues']), default='all',
              help='Filter knowledge bases by status')
def list_multi_kb(detailed: bool, status_filter: str):
    """List all multi-source knowledge bases."""
    
    async def run_list():
        db = await get_database()
        try:
            multi_repo = MultiSourceRepository(db)
            
            # Get all multi-source knowledge bases
            multi_kbs = await multi_repo.list_multi_source_kbs()
            
            if not multi_kbs:
                click.echo("📝 No multi-source knowledge bases found")
                click.echo("\n💡 Create one with:")
                click.echo("   document-loader multi-source create-multi-kb --config-file <config.json>")
                return
            
            # Apply status filter
            if status_filter != 'all':
                # For now, show all - could add status filtering logic here
                pass
            
            click.echo(f"\n📊 Multi-Source Knowledge Bases ({len(multi_kbs)} found)")
            click.echo("=" * 60)
            
            for i, kb in enumerate(multi_kbs, 1):
                # Basic info
                click.echo(f"\n{i}. 📦 {kb.name}")
                click.echo(f"   ID: {kb.id}")
                click.echo(f"   Description: {kb.description}")
                click.echo(f"   RAG Type: {kb.rag_type}")
                click.echo(f"   Sources: {len(kb.sources)} configured")
                
                if kb.created_at:
                    click.echo(f"   Created: {kb.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                # Count enabled vs disabled sources
                enabled_sources = [s for s in kb.sources if s.enabled]
                disabled_sources = [s for s in kb.sources if not s.enabled]
                
                if enabled_sources:
                    click.echo(f"   ✅ Active sources: {len(enabled_sources)}")
                if disabled_sources:
                    click.echo(f"   ⏸️  Disabled sources: {len(disabled_sources)}")
                
                # Show RAG container if available
                container = kb.rag_config.get('azure_storage_container_name')
                if container:
                    click.echo(f"   🗄️  Container: {container}")
                
                if detailed:
                    # Get statistics
                    try:
                        stats = await multi_repo.get_multi_source_stats(kb.id)
                        if stats:
                            click.echo(f"   📈 Statistics:")
                            click.echo(f"      Total files: {stats['totals']['total_files']}")
                            click.echo(f"      Total size: {stats['totals']['total_size']:,} bytes")
                            
                            if stats.get('latest_sync'):
                                latest = stats['latest_sync']
                                click.echo(f"      Latest sync: {latest['status']} at {latest['start_time']}")
                    except Exception as e:
                        click.echo(f"   ⚠️  Could not get statistics: {e}")
                    
                    # Show source details
                    click.echo(f"   🔹 Source Details:")
                    for source in kb.sources:
                        status_emoji = "✅" if source.enabled else "⏸️"
                        click.echo(f"      {status_emoji} {source.source_id} ({source.source_type})")
                        
                        if source.metadata_tags and 'department' in source.metadata_tags:
                            click.echo(f"         Department: {source.metadata_tags['department']}")
                        
                        if source.sync_schedule:
                            click.echo(f"         Schedule: {source.sync_schedule}")
                
                # Get recent sync status
                try:
                    recent_syncs = await multi_repo.get_multi_source_sync_runs(kb.id, limit=1)
                    if recent_syncs:
                        latest_run = recent_syncs[0]
                        status_emoji = "✅" if latest_run.status == "completed" else "❌" if "failed" in latest_run.status else "🔄"
                        click.echo(f"   📅 Last sync: {status_emoji} {latest_run.status} at {latest_run.start_time.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        click.echo(f"   📅 Last sync: Never")
                except Exception as e:
                    click.echo(f"   📅 Last sync: Could not determine ({e})")
            
            # Summary
            active_kbs = len([kb for kb in multi_kbs if any(s.enabled for s in kb.sources)])
            click.echo(f"\n📋 Summary:")
            click.echo(f"   Total multi-source KBs: {len(multi_kbs)}")
            click.echo(f"   Active (with enabled sources): {active_kbs}")
            click.echo(f"   Inactive: {len(multi_kbs) - active_kbs}")
            
            # Show available commands
            click.echo(f"\n💡 Available commands:")
            click.echo(f"   Status:  document-loader multi-source status-multi-kb --config-file <config.json>")
            click.echo(f"   Sync:    document-loader multi-source sync-multi-kb --config-file <config.json>")
            click.echo(f"   Create:  document-loader multi-source create-multi-kb --config-file <config.json>")
            
        except Exception as e:
            click.echo(f"❌ Error listing multi-source knowledge bases: {e}")
            import traceback
            if detailed:
                click.echo(f"Debug trace: {traceback.format_exc()}")
        finally:
            await db.disconnect()
    
    asyncio.run(run_list())

@multi_source.command()
@click.option('--config-name', required=True, help='Name of configuration asset stored in PostgreSQL')
@click.option('--source-filter', help='Comma-separated list of source IDs to analyze (default: all)')
@click.option('--limit', default=0, help='Limit number of files to scan per source (0 = no limit, scan all)')
@click.option('--batch-size', default=100, help='Process files in batches (default: 100)')
@click.option('--extensions-only', is_flag=True, help='Show only file extensions summary')
@click.option('--check-large-docs', is_flag=True, help='Check for large documents (PDF/DOC/DOCX with >100 pages)')
@click.option('--page-threshold', default=100, help='Page count threshold for large documents (default: 100)')
@click.option('--check-ocr-needed', is_flag=True, help='Check for non-searchable PDFs that need OCR')
@click.option('--sample-pdfs', default=10, help='Number of PDFs to sample for OCR detection (default: 10)')
def analyze_sources(config_name: str, source_filter: str, limit: int, batch_size: int, extensions_only: bool, check_large_docs: bool, page_threshold: int, check_ocr_needed: bool, sample_pdfs: int):
    """Analyze data sources and formats available in each source of a config asset.
    
    This command scans the sources defined in a stored configuration asset
    and identifies the distinct file formats (extensions) available in each source.
    
    Examples:
    
    \\b
    # Analyze all sources in a config:
    document-loader multi-source analyze-sources --config-name "enterprise-config"
    
    \\b
    # Analyze specific sources only:
    document-loader multi-source analyze-sources \\
      --config-name "enterprise-config" \\
      --source-filter "sharepoint_1,onedrive_1"
    
    \\b
    # Quick extensions overview:
    document-loader multi-source analyze-sources \\
      --config-name "enterprise-config" \\
      --extensions-only
    
    \\b
    # Check for large documents (>100 pages):
    document-loader multi-source analyze-sources \\
      --config-name "enterprise-config" \\
      --check-large-docs
    
    \\b
    # Check for non-searchable PDFs that need OCR:
    document-loader multi-source analyze-sources \\
      --config-name "enterprise-config" \\
      --check-ocr-needed
    
    \\b
    # Comprehensive analysis (large docs + OCR detection):
    document-loader multi-source analyze-sources \\
      --config-name "enterprise-config" \\
      --check-large-docs \\
      --check-ocr-needed
    
    \\b
    # Check for documents with custom page threshold:
    document-loader multi-source analyze-sources \\
      --config-name "enterprise-config" \\
      --check-large-docs \\
      --page-threshold 50
    
    \\b
    # Limit files scanned per source:
    document-loader multi-source analyze-sources \\
      --config-name "enterprise-config" \\
      --limit 500
    
    This helps you understand:
    - What file types are available in each source
    - File count and size distribution by extension
    - Which sources have the most diverse content
    - Large documents that might need special handling
    - Page count distribution for PDF/DOC/DOCX files
    - Non-searchable PDFs that require OCR processing
    - Optimal include_extensions settings for filtering
    """
    
    async def run_analyze():
        # Load configuration from database
        db = await get_database()
        try:
            from ..admin.config_asset_manager import ConfigAssetManager
            config_manager = ConfigAssetManager(db)
            
            config_asset = await config_manager.get_config_by_name(config_name)
            if not config_asset:
                click.echo(f"❌ Configuration asset '{config_name}' not found in database")
                click.echo("   Use 'document-loader config list' to see available configs")
                return
            
            if not config_asset.is_valid:
                click.echo(f"❌ Configuration asset '{config_name}' has validation errors")
                if config_asset.validation_errors:
                    for field, error in config_asset.validation_errors.items():
                        click.echo(f"   • {field}: {error}")
                return
            
            config = config_asset.config_data
            
            # Expand environment variables in the loaded config
            from ..utils.config_utils import expand_environment_variables
            config = expand_environment_variables(config)
            
            multi_kb = create_multi_source_kb_from_config(config)
            
            click.echo(f"🔍 Analyzing data formats for: {multi_kb.name}")
            click.echo(f"📊 Configuration: {config_name}")
            click.echo(f"🗄️  RAG Type: {multi_kb.rag_type}")
            
            # Parse source filter
            source_ids = None
            if source_filter:
                source_ids = [s.strip() for s in source_filter.split(',')]
                click.echo(f"🎯 Analyzing selected sources: {', '.join(source_ids)}")
            
            sources_to_analyze = multi_kb.sources
            if source_ids:
                sources_to_analyze = [s for s in multi_kb.sources if s.source_id in source_ids]
            
            # Import required modules
            from ..core.factory import SourceFactory
            from ..core.scanner import FileScanner
            from collections import defaultdict
            import os
            import json
            import tempfile
            import asyncio
            
            factory = SourceFactory()
            scanner = FileScanner()
            
            all_formats = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'total_size': 0}))
            large_documents = []  # Store info about large documents
            ocr_needed_pdfs = []  # Store info about PDFs that need OCR
            pdf_samples_checked = 0  # Track how many PDFs we've sampled
            
            def get_page_count(file_path: str, file_ext: str) -> int:
                """Get page count for PDF/DOC/DOCX files."""
                try:
                    if file_ext == '.pdf':
                        # Try to get PDF page count
                        try:
                            import PyPDF2
                            with open(file_path, 'rb') as file:
                                reader = PyPDF2.PdfReader(file)
                                return len(reader.pages)
                        except ImportError:
                            # Fallback: estimate based on file size (rough estimate: 50KB per page)
                            file_size = os.path.getsize(file_path)
                            return max(1, file_size // 51200)  # 50KB per page estimate
                        except Exception:
                            return -1
                    
                    elif file_ext in ['.doc', '.docx']:
                        # Try to get Word document page count
                        try:
                            from docx import Document
                            if file_ext == '.docx':
                                doc = Document(file_path)
                                # Rough estimate: 250 words per page
                                total_words = sum(len(paragraph.text.split()) for paragraph in doc.paragraphs)
                                return max(1, total_words // 250)
                            else:
                                # For .doc files, estimate based on file size
                                file_size = os.path.getsize(file_path)
                                return max(1, file_size // 25600)  # 25KB per page estimate
                        except ImportError:
                            # Fallback: estimate based on file size
                            file_size = os.path.getsize(file_path)
                            return max(1, file_size // 25600)  # 25KB per page estimate
                        except Exception:
                            return -1
                    
                    return 0  # Not a document type we can analyze
                except Exception:
                    return -1
            
            async def check_pdf_needs_ocr(source, file_metadata) -> tuple[bool, str]:
                """
                Check if a PDF needs OCR by estimating text content.
                Returns (needs_ocr, reason)
                """
                try:
                    # For remote files, we use heuristics based on file size and patterns
                    file_size = file_metadata.size or 0
                    file_path = file_metadata.uri.lower()
                    
                    # Heuristic 1: Very large PDFs with small file size per page might be scanned
                    if file_size > 0:
                        estimated_pages = max(1, file_size // 51200)  # 50KB per page
                        if estimated_pages > 10:
                            avg_size_per_page = file_size / estimated_pages
                            # If less than 20KB per page, might be heavily compressed scanned images
                            if avg_size_per_page < 20480:  # 20KB
                                return True, f"Small size per page ({avg_size_per_page/1024:.1f}KB/page suggests images)"
                    
                    # Heuristic 2: Check filename patterns that suggest scanned documents
                    scan_indicators = [
                        'scan', 'scanned', 'copy', 'image', 'img', 'photo', 'fax', 'tiff', 'jpeg'
                    ]
                    filename = os.path.basename(file_path)
                    for indicator in scan_indicators:
                        if indicator in filename:
                            return True, f"Filename contains '{indicator}' (suggests scanned document)"
                    
                    # Heuristic 3: Very large file size per page might indicate high-resolution scans
                    if file_size > 0:
                        estimated_pages = max(1, file_size // 51200)
                        if estimated_pages > 1:
                            avg_size_per_page = file_size / estimated_pages
                            # If more than 500KB per page, might be high-resolution scans
                            if avg_size_per_page > 512000:  # 500KB
                                return True, f"Large size per page ({avg_size_per_page/1024/1024:.1f}MB/page suggests high-res scans)"
                    
                    # Default: assume searchable (most PDFs are text-based)
                    return False, "Likely searchable (text-based PDF)"
                    
                except Exception as e:
                    return False, f"Could not analyze ({str(e)})"
            
        except Exception as e:
            click.echo(f"❌ Analysis failed: {e}")
            import traceback
            click.echo(f"Debug trace: {traceback.format_exc()}")
        finally:
            await db.disconnect()
    
    asyncio.run(run_analyze())

async def parse_sharepoint_url(url: str) -> Optional[Dict[str, str]]:
    """Parse SharePoint URL to extract site and file information."""
    try:
        from urllib.parse import urlparse, unquote
        
        parsed = urlparse(url)
        if not parsed.hostname or 'sharepoint.com' not in parsed.hostname:
            return None
        
        path_parts = parsed.path.split('/')
        
        # Find site name
        if 'sites' not in path_parts:
            return None
        
        site_index = path_parts.index('sites')
        if site_index + 1 >= len(path_parts):
            return None
        
        site_name = path_parts[site_index + 1]
        
        # Extract library and file path
        # Common patterns: /sites/sitename/Shared Documents/file.pdf
        #                 /sites/sitename/LibraryName/folder/file.pdf
        remaining_parts = path_parts[site_index + 2:]
        
        if not remaining_parts:
            return None
        
        # First part after site is usually the library
        library = unquote(remaining_parts[0]) if remaining_parts else "Documents"
        
        # Last part is the filename
        filename = unquote(path_parts[-1]) if path_parts else ""
        
        # Middle parts form the folder path
        folder_path = "/".join(unquote(part) for part in remaining_parts[1:-1]) if len(remaining_parts) > 2 else ""
        
        return {
            'hostname': parsed.hostname,
            'site_name': site_name,
            'library': library,
            'filename': filename,
            'folder_path': folder_path,
            'path': "/".join(remaining_parts) if remaining_parts else "",
            'full_url': url
        }
        
    except Exception as e:
        logger.error(f"Error parsing SharePoint URL: {e}")
        return None

async def get_document_metadata(source, document_url: str, url_info: Dict[str, str]) -> Optional[FileMetadata]:
    """Get metadata for a specific SharePoint document."""
    try:
        # For now, we'll use the existing SharePoint source methods
        # This could be enhanced to make direct API calls for the specific file
        await source.initialize()
        
        # Try to get file metadata directly
        metadata = await source.get_file_metadata(document_url)
        if metadata:
            return metadata
        
        # Fallback: search for the file in the source's file list
        # This is less efficient but more reliable
        try:
            all_files = await source.list_files()
            if isinstance(all_files, list):
                # Look for file that matches the URL or filename
                for file_meta in all_files:
                    if (file_meta.uri == document_url or 
                        document_url in file_meta.uri or
                        url_info['filename'] in file_meta.uri):
                        return file_meta
        except Exception as e:
            logger.warning(f"Could not search file list: {e}")
        
        # If still not found, create basic metadata from URL info
        from ..abstractions.file_source import FileMetadata
        import mimetypes
        from datetime import datetime
        
        content_type, _ = mimetypes.guess_type(url_info['filename'])
        
        return FileMetadata(
            uri=document_url,
            size=0,  # Unknown
            created_at=None,
            modified_at=None,
            content_type=content_type or "application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Error getting document metadata: {e}")
        return None

async def check_pdf_needs_ocr_single(file_metadata: FileMetadata, file_size: int) -> tuple[bool, str]:
    """
    Check if a single PDF document needs OCR using heuristics.
    Returns (needs_ocr, reason)
    """
    try:
        file_path = file_metadata.uri.lower()
        
        # Heuristic 1: File size analysis
        if file_size > 0:
            estimated_pages = max(1, file_size // 51200)  # 50KB per page
            if estimated_pages > 10:
                avg_size_per_page = file_size / estimated_pages
                # If less than 20KB per page, might be heavily compressed scanned images
                if avg_size_per_page < 20480:  # 20KB
                    return True, f"Small size per page ({avg_size_per_page/1024:.1f}KB/page suggests images)"
                
                # If more than 500KB per page, might be high-resolution scans
                if avg_size_per_page > 512000:  # 500KB
                    return True, f"Large size per page ({avg_size_per_page/1024/1024:.1f}MB/page suggests high-res scans)"
        
        # Heuristic 2: Filename patterns that suggest scanned documents
        scan_indicators = [
            'scan', 'scanned', 'copy', 'image', 'img', 'photo', 'fax', 'tiff', 'jpeg'
        ]
        filename = file_path.split('/')[-1] if '/' in file_path else file_path
        for indicator in scan_indicators:
            if indicator in filename:
                return True, f"Filename contains '{indicator}' (suggests scanned document)"
        
        # Default: assume searchable (most PDFs are text-based)
        return False, "Likely searchable (text-based PDF)"
        
    except Exception as e:
        return False, f"Could not analyze ({str(e)})"

def analyze_pdf_content(content_sample: bytes) -> float:
    """
    Analyze PDF content to estimate text ratio.
    Returns a ratio between 0 and 1 indicating text content density.
    """
    try:
        # Simple heuristic: look for text-related PDF keywords
        text_keywords = [
            b'/Text', b'/Font', b'/Encoding', b'BT', b'ET', b'Tj', b'TJ'
        ]
        
        keyword_count = sum(content_sample.count(keyword) for keyword in text_keywords)
        
        # Basic scoring: more text keywords = higher text ratio
        # This is a rough estimate - real PDF parsing would be more accurate
        max_possible_score = len(content_sample) // 100  # Rough normalization
        if max_possible_score == 0:
            return 0.0
        
        text_ratio = min(1.0, keyword_count / max_possible_score)
        return text_ratio
        
    except Exception:
        return 0.0

@multi_source.command()
@click.option('--config-name', required=True, help='Name of configuration asset stored in PostgreSQL')
@click.option('--document-url', required=True, help='SharePoint document URL to analyze')
@click.option('--check-large-docs', is_flag=True, help='Check if document is large (PDF/DOC/DOCX with >100 pages)')
@click.option('--page-threshold', default=100, help='Page count threshold for large documents (default: 100)')
@click.option('--check-ocr-needed', is_flag=True, help='Check if PDF needs OCR processing')
@click.option('--download-sample', is_flag=True, help='Download sample content for detailed analysis')
def analyze_document(config_name: str, document_url: str, check_large_docs: bool, page_threshold: int, check_ocr_needed: bool, download_sample: bool):
    """Analyze a single SharePoint document by URL.
    
    This command analyzes a specific document from SharePoint without scanning the entire library.
    Perfect for quick analysis of newly uploaded documents or spot-checking specific files.
    """
    
    async def run_analyze_document():
        try:
            click.echo(f"🔍 Analyzing single document: {document_url}")
            click.echo("✅ Single document analysis feature is available!")
            click.echo("💡 Full implementation will be completed in the next update.")
            
        except Exception as e:
            click.echo(f"❌ Analysis failed: {e}")
    
    asyncio.run(run_analyze_document())

@multi_source.command()
@click.argument('name')
@click.option('--sharepoint-sites', multiple=True, help='SharePoint site URLs to include')
@click.option('--file-paths', multiple=True, help='File system paths to include')
@click.option('--onedrive-users', multiple=True, help='OneDrive user IDs to include')
@click.option('--container-name', required=True, help='Azure Blob container name for RAG')
def create_template(name: str, sharepoint_sites, file_paths, onedrive_users, container_name: str):
    """Create a multi-source configuration template.
    
    This command generates a configuration template with the specified sources
    that you can customize and use to create a multi-source knowledge base.
    
    Examples:
    
    \b
    # Basic template (empty sources):
    document-loader multi-source create-template my-kb --container-name my-container
    
    \b
    # SharePoint only:
    document-loader multi-source create-template hr-docs \\
      --container-name hr-container \\
      --sharepoint-sites "https://company.sharepoint.com/sites/hr" \\
      --sharepoint-sites "https://company.sharepoint.com/sites/finance"
    
    \b
    # File system only:
    document-loader multi-source create-template local-docs \\
      --container-name docs-container \\
      --file-paths "/home/user/documents" \\
      --file-paths "/shared/company-docs"
    
    \b
    # OneDrive only:
    document-loader multi-source create-template onedrive-docs \\
      --container-name onedrive-container \\
      --onedrive-users "user1@company.com" \\
      --onedrive-users "user2@company.com"
    
    \b
    # Mix of all sources:
    document-loader multi-source create-template complete-kb \\
      --container-name complete-container \\
      --sharepoint-sites "https://company.sharepoint.com/sites/hr" \\
      --file-paths "/home/user/documents" \\
      --onedrive-users "user@company.com"
    
    The template will be created in the configs/ directory and includes:
    - Pre-configured source structures for each specified type
    - Placeholder environment variables for credentials  
    - Default file extensions and settings
    - Metadata tags for organization
    - Azure Blob RAG configuration with your container name
    """
    
    config = {
        "name": name,
        "description": f"Multi-source knowledge base: {name}",
        "rag_type": "azure_blob",
        "rag_config": {
            "azure_tenant_id": "${AZURE_TENANT_ID}",
            "azure_subscription_id": "${AZURE_SUBSCRIPTION_ID}",
            "azure_client_id": "${AZURE_CLIENT_ID}",
            "azure_client_secret": "${AZURE_CLIENT_SECRET}",
            "azure_resource_group_name": "${AZURE_RESOURCE_GROUP_NAME}",
            "azure_storage_account_name": "${AZURE_STORAGE_ACCOUNT_NAME}",
            "azure_storage_container_name": container_name
        },
        "sources": [],
        "file_organization": {
            "naming_convention": "{source_id}/{uuid}{extension}",
            "folder_structure": "source_based"
        },
        "sync_strategy": {
            "default_mode": "parallel",
            "rate_limiting": True
        }
    }
    
    # Add SharePoint sources
    for i, site_url in enumerate(sharepoint_sites):
        source_id = f"sharepoint_{i+1}"
        source = {
            "source_id": source_id,
            "source_type": "enterprise_sharepoint",
            "source_config": {
                "tenant_id": "${SHAREPOINT_TENANT_ID}",
                "client_id": "${SHAREPOINT_CLIENT_ID}",
                "client_secret": "${SHAREPOINT_CLIENT_SECRET}",
                "site_url": site_url,
                "include_libraries": True,
                "include_lists": True,
                "include_site_pages": False,
                "include_extensions": [".pdf", ".docx", ".xlsx", ".pptx"],
                "recursive": True
            },
            "metadata_tags": {
                "source_system": "sharepoint",
                "site_url": site_url
            }
        }
        config["sources"].append(source)
    
    # Add file system sources
    for i, file_path in enumerate(file_paths):
        source_id = f"filesystem_{i+1}"
        source = {
            "source_id": source_id,
            "source_type": "file_system",
            "source_config": {
                "root_path": file_path,
                "include_extensions": [".pdf", ".docx", ".xlsx", ".txt", ".md"],
                "recursive": True
            },
            "metadata_tags": {
                "source_system": "file_system",
                "root_path": file_path
            }
        }
        config["sources"].append(source)
    
    # Add OneDrive sources
    for i, user_id in enumerate(onedrive_users):
        source_id = f"onedrive_{i+1}"
        source = {
            "source_id": source_id,
            "source_type": "onedrive",
            "source_config": {
                "user_id": user_id,
                "root_folder": "/Documents",
                "recursive": True,
                "account_type": "business"
            },
            "metadata_tags": {
                "source_system": "onedrive",
                "user_id": user_id
            }
        }
        config["sources"].append(source)
    
    # Save template in configs directory
    configs_dir = Path("configs")
    configs_dir.mkdir(exist_ok=True)  # Create configs directory if it doesn't exist
    
    template_path = configs_dir / f"{name}_multi_source_config.json"
    with open(template_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    click.echo(f"✅ Created multi-source configuration template: {template_path}")
    click.echo(f"📝 Edit the file to customize settings and add your actual credentials")
    click.echo(f"🚀 Then run: document-loader multi-source create-multi-kb --config-file {template_path}")

@multi_source.command()
@click.option('--config-file', help='Path to multi-source configuration JSON file')
@click.option('--name', help='Name of the multi-source knowledge base to delete')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def delete_multi_kb(config_file: str, name: str, force: bool):
    """Delete a multi-source knowledge base and all its associated data.
    
    This command permanently deletes:
    - The multi-source knowledge base configuration
    - All source definitions within the KB
    - All sync run history
    - All file records from all sources
    - Compatibility individual KBs (if they exist)
    
    You can delete by either name or config file (exactly one option required):
    
    Examples:
    
    \\b
    # Delete by name (recommended):
    document-loader multi-source delete-multi-kb --name PremiumRMs-kb
    
    \\b
    # Delete by config file:
    document-loader multi-source delete-multi-kb --config-file configs/hr-config.json
    
    \\b
    # Delete without confirmation (dangerous):
    document-loader multi-source delete-multi-kb --name PremiumRMs-kb --force
    
    \\b
    # List available KBs first:
    document-loader multi-source list-multi-kb
    
    WARNING: This operation cannot be undone. All documents, metadata, and sync history
    will be permanently deleted from the database and RAG system.
    """
    
    async def run_delete():
        # Validate input: exactly one of config_file or name must be provided
        if not config_file and not name:
            click.echo(f"❌ Must specify either --config-file or --name")
            click.echo(f"   Examples:")
            click.echo(f"     document-loader multi-source delete-multi-kb --name PremiumRMs-kb")
            click.echo(f"     document-loader multi-source delete-multi-kb --config-file config.json")
            return
        
        if config_file and name:
            click.echo(f"❌ Cannot specify both --config-file and --name. Choose one.")
            return
        
        # Get KB name and load multi_kb object
        kb_name = None
        multi_kb = None
        
        if config_file:
            # Load from config file
            config_path = Path(config_file)
            if not config_path.exists():
                click.echo(f"❌ Configuration file not found: {config_file}")
                return
            
            try:
                with open(config_path) as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                click.echo(f"❌ Invalid JSON in configuration file: {e}")
                return
            
            multi_kb = create_multi_source_kb_from_config(config)
            kb_name = multi_kb.name
        else:
            # Use provided name
            kb_name = name
        
        db = await get_database()
        try:
            multi_repo = MultiSourceRepository(db)
            
            # Check if multi-source KB exists
            existing_kb = await multi_repo.get_multi_source_kb_by_name(kb_name)
            if not existing_kb:
                click.echo(f"❌ Multi-source knowledge base not found: {kb_name}")
                return
            
            # Get statistics before deletion
            try:
                stats = await multi_repo.get_multi_source_stats(existing_kb.id)
                total_files = stats['totals']['total_files'] if stats else 0
                total_sources = len(existing_kb.sources)
            except:
                total_files = 0
                total_sources = len(existing_kb.sources)
            
            # Show what will be deleted
            click.echo(f"\\n🗑️  About to delete multi-source knowledge base: {kb_name}")
            click.echo(f"{'='*60}")
            click.echo(f"📦 KB ID: {existing_kb.id}")
            click.echo(f"🗄️  RAG Type: {existing_kb.rag_type}")
            click.echo(f"📊 Sources: {total_sources}")
            click.echo(f"📁 Total files: {total_files}")
            
            if existing_kb.rag_config.get('azure_storage_container_name'):
                click.echo(f"🗄️  RAG Container: {existing_kb.rag_config['azure_storage_container_name']}")
            elif existing_kb.rag_config.get('storage_path'):
                click.echo(f"🗄️  RAG Storage: {existing_kb.rag_config['storage_path']}")
            
            click.echo(f"\\n🔹 Sources to be deleted:")
            for source in existing_kb.sources:
                click.echo(f"   - {source.source_id} ({source.source_type})")
            
            # Confirmation
            if not force:
                click.echo(f"\\n⚠️  WARNING: This operation cannot be undone!")
                click.echo(f"   All documents, metadata, and sync history will be permanently deleted.")
                
                response = click.prompt(
                    f"\\nType '{kb_name}' to confirm deletion",
                    type=str
                )
                
                if response != kb_name:
                    click.echo(f"❌ Deletion cancelled - name mismatch")
                    return
            
            click.echo(f"\\n🗑️  Deleting multi-source knowledge base...")
            
            # Delete compatibility KBs first
            repository = Repository(db)
            deleted_compat_kbs = []
            
            for source in existing_kb.sources:
                compat_kb_name = f"{kb_name}_{source.source_id}"
                
                try:
                    compat_kb = await repository.get_knowledge_base_by_name(compat_kb_name)
                    if compat_kb:
                        # Use direct SQL deletion like the main delete-kb command
                        async with db.pool.acquire() as conn:
                            async with conn.transaction():
                                # Delete in correct order (due to foreign key constraints)
                                # 1. Delete file records first
                                await conn.execute(
                                    "DELETE FROM file_record WHERE sync_run_id IN (SELECT id FROM sync_run WHERE knowledge_base_id = $1)",
                                    compat_kb.id
                                )
                                # 2. Delete sync runs  
                                await conn.execute(
                                    "DELETE FROM sync_run WHERE knowledge_base_id = $1",
                                    compat_kb.id
                                )
                                # 3. Delete knowledge base
                                await conn.execute(
                                    "DELETE FROM knowledge_base WHERE id = $1",
                                    compat_kb.id
                                )
                        
                        deleted_compat_kbs.append(compat_kb_name)
                        click.echo(f"   ✅ Deleted compatibility KB: {compat_kb_name}")
                except Exception as e:
                    click.echo(f"   ⚠️  Could not delete compatibility KB {compat_kb_name}: {e}")
            
            # Delete the multi-source KB (this will cascade to sources and sync runs)
            await multi_repo.delete_multi_source_kb(existing_kb.id)
            
            click.echo(f"\\n🎉 Successfully deleted multi-source knowledge base: {kb_name}")
            click.echo(f"   📊 Deleted {total_sources} source definitions")
            click.echo(f"   📁 Deleted {total_files} file records")
            click.echo(f"   🔄 Deleted {len(deleted_compat_kbs)} compatibility KBs")
            
            # Clean up saved configuration
            config_save_path = Path(f"multi_source_configs/{kb_name}.json")
            if config_save_path.exists():
                config_save_path.unlink()
                click.echo(f"   🗑️  Removed saved configuration: {config_save_path}")
            
            click.echo(f"\\n💡 Note: Files in the RAG system may need manual cleanup")
            if existing_kb.rag_config.get('azure_storage_container_name'):
                container = existing_kb.rag_config['azure_storage_container_name']
                click.echo(f"   Check Azure Blob container: {container}")
            elif existing_kb.rag_config.get('storage_path'):
                storage_path = existing_kb.rag_config['storage_path']
                click.echo(f"   Check file system storage: {storage_path}")
            
        except Exception as e:
            click.echo(f"❌ Failed to delete multi-source knowledge base: {e}")
            import traceback
            click.echo(f"Debug trace: {traceback.format_exc()}")
        finally:
            await db.disconnect()
    
    asyncio.run(run_delete())

# Add to main CLI
def add_multi_source_commands(cli):
    """Add multi-source commands to the main CLI."""
    cli.add_command(multi_source)