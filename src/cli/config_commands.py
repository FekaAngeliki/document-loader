"""
CLI Commands for Config Asset Management
"""

import click
import asyncio
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from pathlib import Path

console = Console()

@click.group()
def config():
    """Configuration asset management commands."""
    pass

@config.command()
@click.option('--file', '-f', 'file_path', required=True, type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--name', '-n', help='Name for the configuration asset (if not provided, uses name from config file)')
@click.option('--description', '-d', help='Description of the configuration')
@click.option('--tags', help='Comma-separated tags')
@click.option('--type', 'config_type', default='multi_source', help='Configuration type')
@click.option('--overwrite', is_flag=True, help='Overwrite existing configuration with same name')
def upload(file_path, name, description, tags, config_type, overwrite):
    """Upload a configuration file to PostgreSQL storage."""
    
    async def _upload():
        try:
            from ..data.database import Database, DatabaseConfig
            from ..admin.config_asset_manager import ConfigAssetManager
            
            # Load and parse the config file to extract name if needed
            with open(file_path, 'r') as f:
                config_data = json.load(f)
            
            # Use name from config file if not provided via CLI
            config_name = name
            if not config_name:
                if 'name' in config_data:
                    config_name = config_data['name']
                else:
                    console.print("❌ No name provided via --name option and no 'name' field found in config file")
                    return
            
            # Connect to database
            db_config = DatabaseConfig()
            db = Database(db_config)
            await db.connect()
            
            # Create config manager
            config_manager = ConfigAssetManager(db)
            
            # Parse tags
            tag_list = [tag.strip() for tag in tags.split(',')] if tags else []
            
            console.print(f"📤 Uploading config file: {file_path}")
            console.print(f"   Name: {config_name}")
            console.print(f"   Type: {config_type}")
            if description:
                console.print(f"   Description: {description}")
            if tag_list:
                console.print(f"   Tags: {', '.join(tag_list)}")
            if overwrite:
                console.print(f"   Mode: Overwrite existing")
            
            # Check if config exists and handle overwrite
            existing_config = await config_manager.get_config_by_name(config_name)
            if existing_config and overwrite:
                console.print(f"🔄 Overwriting existing config '{config_name}' (ID: {existing_config.id})")
                # Hard delete the existing config first
                await config_manager.delete_config(config_name, soft_delete=False)
                console.print(f"   ✅ Deleted existing config")
            elif existing_config and not overwrite:
                console.print(f"❌ Config '{config_name}' already exists. Use --overwrite to replace it.")
                await db.disconnect()
                raise click.ClickException(f"Configuration '{config_name}' already exists. Use --overwrite flag to replace it.")
            
            # Upload the config
            config_id = await config_manager.upload_config_file(
                file_path=file_path,
                name=config_name,
                description=description,
                tags=tag_list,
                config_type=config_type
            )
            
            console.print(f"✅ Config uploaded successfully with ID: {config_id}")
            
            # Show validation results
            config_asset = await config_manager.get_config_by_name(config_name)
            if config_asset:
                if config_asset.is_valid:
                    console.print("✅ Configuration is valid")
                else:
                    console.print("⚠️  Configuration has validation errors:")
                    if config_asset.validation_errors:
                        for field, error in config_asset.validation_errors.items():
                            console.print(f"   • {field}: {error}")
            
            await db.disconnect()
            
        except Exception as e:
            console.print(f"❌ Upload failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_upload())

@config.command()
@click.option('--type', 'config_type', help='Filter by configuration type')
@click.option('--tags', help='Filter by tags (comma-separated)')
@click.option('--all', 'show_all', is_flag=True, help='Show inactive configs too')
def list(config_type, tags, show_all):
    """List all stored configuration assets."""
    
    async def _list():
        try:
            from ..data.database import Database, DatabaseConfig
            from ..admin.config_asset_manager import ConfigAssetManager
            
            # Connect to database
            db_config = DatabaseConfig()
            db = Database(db_config)
            await db.connect()
            
            # Create config manager
            config_manager = ConfigAssetManager(db)
            
            # Parse filters
            tag_list = [tag.strip() for tag in tags.split(',')] if tags else None
            
            # Get configs
            configs = await config_manager.list_configs(
                config_type=config_type,
                tags=tag_list,
                active_only=not show_all
            )
            
            if not configs:
                console.print("📭 No configuration assets found")
                await db.disconnect()
                return
            
            # Create table
            table = Table(title=f"Configuration Assets ({len(configs)} found)")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="bold cyan")
            table.add_column("Type", style="green")
            table.add_column("Valid", justify="center")
            table.add_column("Size", justify="right")
            table.add_column("Used", justify="right")
            table.add_column("Created", style="dim")
            table.add_column("Tags", style="yellow")
            
            for config in configs:
                valid_icon = "✅" if config.is_valid else "❌"
                size_str = f"{config.file_size:,} B" if config.file_size else "N/A"
                used_str = str(config.usage_count) if config.usage_count else "0"
                created_str = config.created_at.strftime("%Y-%m-%d") if config.created_at else "N/A"
                tags_str = ", ".join(config.tags) if config.tags else ""
                
                table.add_row(
                    str(config.id),
                    config.name,
                    config.config_type,
                    valid_icon,
                    size_str,
                    used_str,
                    created_str,
                    tags_str
                )
            
            console.print(table)
            await db.disconnect()
            
        except Exception as e:
            console.print(f"❌ List failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_list())

@config.command()
@click.argument('name')
def show(name):
    """Show detailed information about a configuration asset."""
    
    async def _show():
        try:
            from ..data.database import Database, DatabaseConfig
            from ..admin.config_asset_manager import ConfigAssetManager
            
            # Connect to database
            db_config = DatabaseConfig()
            db = Database(db_config)
            await db.connect()
            
            # Create config manager
            config_manager = ConfigAssetManager(db)
            
            # Get config
            config = await config_manager.get_config_by_name(name)
            if not config:
                console.print(f"❌ Configuration '{name}' not found")
                await db.disconnect()
                return
            
            # Show config details
            console.print(Panel.fit(f"Configuration Asset: {config.name}", style="bold cyan"))
            
            details_table = Table(show_header=False, box=None)
            details_table.add_column("Field", style="bold")
            details_table.add_column("Value")
            
            details_table.add_row("ID", str(config.id))
            details_table.add_row("Name", config.name)
            details_table.add_row("Description", config.description or "N/A")
            details_table.add_row("Type", config.config_type)
            details_table.add_row("Version", str(config.version))
            details_table.add_row("Valid", "✅ Yes" if config.is_valid else "❌ No")
            details_table.add_row("Active", "✅ Yes" if config.is_active else "❌ No")
            details_table.add_row("File Size", f"{config.file_size:,} bytes" if config.file_size else "N/A")
            details_table.add_row("File Hash", config.file_hash[:16] + "..." if config.file_hash else "N/A")
            details_table.add_row("Original File", config.original_filename or "N/A")
            details_table.add_row("Tags", ", ".join(config.tags) if config.tags else "None")
            details_table.add_row("Usage Count", str(config.usage_count))
            details_table.add_row("Created", config.created_at.strftime("%Y-%m-%d %H:%M:%S") if config.created_at else "N/A")
            details_table.add_row("Last Used", config.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if config.last_used_at else "Never")
            
            console.print(details_table)
            
            # Show validation errors if any
            if not config.is_valid and config.validation_errors:
                console.print("\n⚠️  Validation Errors:")
                for field, error in config.validation_errors.items():
                    console.print(f"   • {field}: {error}")
            
            # Show config data (formatted JSON)
            console.print("\n📄 Configuration Data:")
            config_json = json.dumps(config.config_data, indent=2, ensure_ascii=False)
            syntax = Syntax(config_json, "json", theme="monokai", line_numbers=True)
            console.print(syntax)
            
            await db.disconnect()
            
        except Exception as e:
            console.print(f"❌ Show failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_show())

@config.command()
@click.argument('name')
@click.argument('output_path')
def export(name, output_path):
    """Export a configuration asset to a local file."""
    
    async def _export():
        try:
            from ..data.database import Database, DatabaseConfig
            from ..admin.config_asset_manager import ConfigAssetManager
            
            # Connect to database
            db_config = DatabaseConfig()
            db = Database(db_config)
            await db.connect()
            
            # Create config manager
            config_manager = ConfigAssetManager(db)
            
            console.print(f"📤 Exporting config '{name}' to {output_path}")
            
            # Export config
            success = await config_manager.export_config(name, output_path)
            
            if success:
                console.print(f"✅ Config exported successfully to {output_path}")
            else:
                console.print(f"❌ Export failed")
            
            await db.disconnect()
            
        except Exception as e:
            console.print(f"❌ Export failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_export())

@config.command()
@click.argument('name')
@click.option('--hard', is_flag=True, help='Permanently delete (cannot be undone)')
@click.option('--force', is_flag=True, help='Skip confirmation')
def delete(name, hard, force):
    """Delete a configuration asset."""
    
    async def _delete():
        try:
            from ..data.database import Database, DatabaseConfig
            from ..admin.config_asset_manager import ConfigAssetManager
            
            # Confirmation
            if not force:
                action = "permanently delete" if hard else "deactivate"
                if not click.confirm(f"Are you sure you want to {action} config '{name}'?"):
                    console.print("❌ Cancelled")
                    return
            
            # Connect to database
            db_config = DatabaseConfig()
            db = Database(db_config)
            await db.connect()
            
            # Create config manager
            config_manager = ConfigAssetManager(db)
            
            console.print(f"🗑️  Deleting config '{name}'...")
            
            # Delete config
            success = await config_manager.delete_config(name, soft_delete=not hard)
            
            if success:
                action = "deleted permanently" if hard else "deactivated"
                console.print(f"✅ Config '{name}' {action} successfully")
            else:
                console.print(f"❌ Delete failed")
            
            await db.disconnect()
            
        except Exception as e:
            console.print(f"❌ Delete failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_delete())

@config.command()
def stats():
    """Show configuration asset statistics."""
    
    async def _stats():
        try:
            from ..data.database import Database, DatabaseConfig
            from ..admin.config_asset_manager import ConfigAssetManager
            
            # Connect to database
            db_config = DatabaseConfig()
            db = Database(db_config)
            await db.connect()
            
            # Create config manager
            config_manager = ConfigAssetManager(db)
            
            # Get stats
            stats = await config_manager.get_config_stats()
            
            if not stats:
                console.print("❌ Unable to retrieve statistics")
                await db.disconnect()
                return
            
            # Create stats table
            stats_table = Table(title="Configuration Asset Statistics")
            stats_table.add_column("Metric", style="bold")
            stats_table.add_column("Value", justify="right")
            
            stats_table.add_row("Total Configs", str(stats.get('total_configs', 0)))
            stats_table.add_row("Active Configs", str(stats.get('active_configs', 0)))
            stats_table.add_row("Valid Configs", str(stats.get('valid_configs', 0)))
            stats_table.add_row("Config Types", str(stats.get('config_types', 0)))
            stats_table.add_row("Avg File Size", f"{stats.get('avg_file_size_bytes', 0):,} bytes")
            stats_table.add_row("Total Usage", str(stats.get('total_usage', 0)))
            
            if stats.get('latest_upload'):
                stats_table.add_row("Latest Upload", stats['latest_upload'].strftime("%Y-%m-%d %H:%M:%S"))
            
            console.print(stats_table)
            
            # Show type breakdown
            if stats.get('type_breakdown'):
                console.print("\n📊 Configuration Types:")
                type_table = Table()
                type_table.add_column("Type", style="cyan")
                type_table.add_column("Count", justify="right")
                
                for config_type, count in stats['type_breakdown'].items():
                    type_table.add_row(config_type, str(count))
                
                console.print(type_table)
            
            await db.disconnect()
            
        except Exception as e:
            console.print(f"❌ Stats failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_stats())