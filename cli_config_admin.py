#!/usr/bin/env python3
"""
CLI Admin Tool for Multi-Source Configuration Management

This script provides command-line interface for admins to upload, manage,
and deploy knowledge base configuration files stored in PostgreSQL.

Usage:
    python3 cli_config_admin.py upload configs/my_config.json --name my-kb --description "Production KB"
    python3 cli_config_admin.py list
    python3 cli_config_admin.py show my-kb
    python3 cli_config_admin.py deploy my-kb
    python3 cli_config_admin.py export my-kb output.json
"""

import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import getpass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from admin.config_manager import create_config_manager
from data.multi_source_models import create_multi_source_kb_from_config
from data.multi_source_repository import MultiSourceRepository
from data.database import Database, DatabaseConfig


class ConfigAdminCLI:
    """Command-line interface for configuration management."""
    
    def __init__(self):
        self.config_manager = None
        self.db = None
    
    async def initialize(self):
        """Initialize database connections."""
        try:
            self.config_manager = await create_config_manager()
            
            # Also initialize direct DB connection for repository operations
            db_config = DatabaseConfig()
            self.db = Database(db_config)
            await self.db.connect()
            
            print("✅ Connected to database")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False
    
    async def cleanup(self):
        """Clean up database connections."""
        if self.db:
            await self.db.disconnect()
    
    async def upload_config(self, args):
        """Upload a configuration file to PostgreSQL."""
        try:
            file_path = Path(args.file_path)
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            created_by = args.created_by or getpass.getuser()
            
            print(f"📤 Uploading configuration: {file_path}")
            print(f"   Admin user: {created_by}")
            
            result = await self.config_manager.upload_config_file(
                file_path=str(file_path),
                name=args.name,
                description=args.description,
                created_by=created_by
            )
            
            print(f"✅ {result['message']}")
            print(f"   Config ID: {result['config_id']}")
            print(f"   Version: {result['version']}")
            print(f"   Sources: {result['source_count']}")
            print(f"   RAG Type: {result['rag_type']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False
    
    async def list_configs(self, args):
        """List all stored configurations."""
        try:
            configs = await self.config_manager.list_configs(args.status)
            
            if not configs:
                print(f"No {args.status} configurations found")
                return True
            
            print(f"\n📋 {args.status.upper()} CONFIGURATIONS")
            print("=" * 80)
            print(f"{'Name':<25} {'Version':<8} {'Sources':<8} {'RAG Type':<15} {'Created By':<12} {'Deployed':<10}")
            print("-" * 80)
            
            for config in configs:
                deployed = "✅ Yes" if config['last_deployed_at'] else "⏸️  No"
                print(f"{config['name']:<25} {config['version']:<8} {config['source_count']:<8} {config['rag_type']:<15} {config['created_by']:<12} {deployed:<10}")
            
            print(f"\nTotal: {len(configs)} configurations")
            return True
            
        except Exception as e:
            print(f"❌ List failed: {e}")
            return False
    
    async def show_config(self, args):
        """Show detailed configuration information."""
        try:
            config = await self.config_manager.get_config(args.name, args.version)
            
            if not config:
                version_text = f" version {args.version}" if args.version else ""
                print(f"❌ Configuration '{args.name}'{version_text} not found")
                return False
            
            print(f"\n📄 CONFIGURATION: {config['name']}")
            print("=" * 60)
            print(f"Version: {config['version']}")
            print(f"Status: {config['status']}")
            print(f"Description: {config['description']}")
            print(f"Created by: {config['created_by']}")
            print(f"Created at: {config['created_at']}")
            print(f"File hash: {config['file_hash'][:16]}...")
            
            # Show configuration content
            config_content = config['config_content']
            print(f"\n📋 KNOWLEDGE BASE CONFIG:")
            print(f"Name: {config_content['name']}")
            print(f"RAG Type: {config_content['rag_type']}")
            print(f"Sources: {len(config_content['sources'])}")
            
            print(f"\n📂 SOURCES:")
            for i, source in enumerate(config_content['sources'], 1):
                enabled = "✅" if source.get('enabled', True) else "⏸️ "
                print(f"  {i}. {enabled} {source['source_id']} ({source['source_type']})")
                if 'metadata_tags' in source:
                    dept = source['metadata_tags'].get('department', 'N/A')
                    print(f"     Department: {dept}")
            
            if args.show_full:
                print(f"\n📝 FULL CONFIGURATION:")
                print(json.dumps(config_content, indent=2))
            
            return True
            
        except Exception as e:
            print(f"❌ Show failed: {e}")
            return False
    
    async def deploy_config(self, args):
        """Deploy a configuration to create a knowledge base."""
        try:
            config = await self.config_manager.get_config(args.name, args.version)
            
            if not config:
                version_text = f" version {args.version}" if args.version else ""
                print(f"❌ Configuration '{args.name}'{version_text} not found")
                return False
            
            print(f"🚀 Deploying configuration: {config['name']} v{config['version']}")
            
            # Create multi-source KB from config
            config_content = config['config_content']
            multi_kb = create_multi_source_kb_from_config(config_content)
            
            # Save to database
            repo = MultiSourceRepository(self.db)
            kb_id = await repo.create_multi_source_kb(multi_kb)
            
            # Mark config as deployed
            await self.config_manager.mark_deployed(config['id'])
            
            print(f"✅ Knowledge base created successfully!")
            print(f"   KB ID: {kb_id}")
            print(f"   Name: {multi_kb.name}")
            print(f"   Sources: {len(multi_kb.sources)}")
            print(f"   Config marked as deployed")
            
            return True
            
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False
    
    async def export_config(self, args):
        """Export a configuration to a file."""
        try:
            output_path = Path(args.output_path)
            
            success = await self.config_manager.export_config(
                args.name, 
                str(output_path), 
                args.version
            )
            
            if success:
                print(f"✅ Configuration exported to: {output_path}")
                return True
            else:
                version_text = f" version {args.version}" if args.version else ""
                print(f"❌ Configuration '{args.name}'{version_text} not found")
                return False
                
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False
    
    async def delete_config(self, args):
        """Delete (archive) a configuration."""
        try:
            if not args.force:
                version_text = f" version {args.version}" if args.version else ""
                response = input(f"Are you sure you want to delete '{args.name}'{version_text}? (y/N): ")
                if response.lower() != 'y':
                    print("❌ Delete cancelled")
                    return False
            
            success = await self.config_manager.delete_config(args.name, args.version)
            
            if success:
                version_text = f" version {args.version}" if args.version else ""
                print(f"✅ Configuration '{args.name}'{version_text} archived")
                return True
            else:
                print(f"❌ Configuration not found")
                return False
                
        except Exception as e:
            print(f"❌ Delete failed: {e}")
            return False
    
    async def show_summary(self, args):
        """Show configuration management summary."""
        try:
            summary = await self.config_manager.get_config_summary()
            
            print(f"\n📊 CONFIGURATION SUMMARY")
            print("=" * 40)
            print(f"Total configurations: {summary.get('total_configs', 0)}")
            print(f"Active configurations: {summary.get('active_configs', 0)}")
            print(f"Archived configurations: {summary.get('archived_configs', 0)}")
            print(f"Deployed configurations: {summary.get('deployed_configs', 0)}")
            print(f"Average deployments: {summary.get('avg_deployments', 0):.1f}")
            
            if summary.get('latest_upload'):
                print(f"Latest upload: {summary['latest_upload']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Summary failed: {e}")
            return False


def create_parser():
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Admin CLI for Multi-Source Configuration Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Upload a config file:
    python3 cli_config_admin.py upload configs/production.json --name prod-kb --description "Production KB"
  
  List all active configurations:
    python3 cli_config_admin.py list
  
  Show configuration details:
    python3 cli_config_admin.py show prod-kb --show-full
  
  Deploy a configuration:
    python3 cli_config_admin.py deploy prod-kb
  
  Export a configuration:
    python3 cli_config_admin.py export prod-kb exported_config.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a configuration file')
    upload_parser.add_argument('file_path', help='Path to JSON configuration file')
    upload_parser.add_argument('--name', help='Override configuration name')
    upload_parser.add_argument('--description', help='Configuration description')
    upload_parser.add_argument('--created-by', help='Admin username (defaults to current user)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List stored configurations')
    list_parser.add_argument('--status', default='active', choices=['active', 'archived', 'draft'],
                           help='Configuration status to list')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show configuration details')
    show_parser.add_argument('name', help='Configuration name')
    show_parser.add_argument('--version', type=int, help='Specific version to show')
    show_parser.add_argument('--show-full', action='store_true', help='Show full configuration JSON')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy configuration to create KB')
    deploy_parser.add_argument('name', help='Configuration name')
    deploy_parser.add_argument('--version', type=int, help='Specific version to deploy')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export configuration to file')
    export_parser.add_argument('name', help='Configuration name')
    export_parser.add_argument('output_path', help='Output file path')
    export_parser.add_argument('--version', type=int, help='Specific version to export')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete (archive) configuration')
    delete_parser.add_argument('name', help='Configuration name')
    delete_parser.add_argument('--version', type=int, help='Specific version to delete')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show configuration summary')
    
    return parser


async def main():
    """Main CLI function."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = ConfigAdminCLI()
    
    try:
        if not await cli.initialize():
            return 1
        
        # Route to appropriate command
        command_map = {
            'upload': cli.upload_config,
            'list': cli.list_configs,
            'show': cli.show_config,
            'deploy': cli.deploy_config,
            'export': cli.export_config,
            'delete': cli.delete_config,
            'summary': cli.show_summary
        }
        
        command_func = command_map.get(args.command)
        if command_func:
            success = await command_func(args)
            return 0 if success else 1
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        await cli.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))