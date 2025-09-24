#!/usr/bin/env python3
"""
Simple Database Viewer for PostgreSQL
A lightweight alternative to pgAdmin for viewing the document-loader database
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from dotenv import load_dotenv
load_dotenv()

import asyncpg

class DatabaseViewer:
    def __init__(self):
        self.connection = None
    
    async def connect(self):
        """Connect to the database."""
        try:
            self.connection = await asyncpg.connect(
                host=os.getenv('DOCUMENT_LOADER_DB_HOST', 'localhost'),
                port=int(os.getenv('DOCUMENT_LOADER_DB_PORT', '5432')),
                database=os.getenv('DOCUMENT_LOADER_DB_NAME', 'document_loader'),
                user=os.getenv('DOCUMENT_LOADER_DB_USER', 'feka'),
                password=os.getenv('DOCUMENT_LOADER_DB_PASSWORD', '123456')
            )
            print("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    async def close(self):
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            print("🔌 Database connection closed")
    
    async def show_tables(self):
        """Display all tables in the database."""
        print("\n" + "="*60)
        print("📋 DATABASE TABLES")
        print("="*60)
        
        query = """
        SELECT 
            table_name,
            (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns,
            pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
        FROM information_schema.tables t 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        
        rows = await self.connection.fetch(query)
        
        print(f"{'Table Name':<30} {'Columns':<10} {'Size':<10}")
        print("-" * 60)
        for row in rows:
            print(f"{row['table_name']:<30} {row['columns']:<10} {row['size']:<10}")
    
    async def show_multi_source_kbs(self):
        """Show multi-source knowledge bases."""
        print("\n" + "="*60)
        print("🗂️  MULTI-SOURCE KNOWLEDGE BASES")
        print("="*60)
        
        query = """
        SELECT 
            id, name, description, rag_type,
            created_at, updated_at,
            (SELECT count(*) FROM source_definition WHERE multi_source_kb_id = ms.id) as source_count
        FROM multi_source_knowledge_base ms
        ORDER BY created_at DESC
        """
        
        rows = await self.connection.fetch(query)
        
        if not rows:
            print("No multi-source knowledge bases found")
            return
        
        for row in rows:
            print(f"\n📁 KB #{row['id']}: {row['name']}")
            print(f"   Description: {row['description'] or 'None'}")
            print(f"   RAG Type: {row['rag_type']}")
            print(f"   Sources: {row['source_count']}")
            print(f"   Created: {row['created_at']}")
    
    async def show_sources(self, kb_id=None):
        """Show source definitions."""
        print("\n" + "="*60)
        print("📂 SOURCE DEFINITIONS")
        print("="*60)
        
        if kb_id:
            query = """
            SELECT source_id, source_type, enabled, sync_schedule, metadata_tags
            FROM source_definition 
            WHERE multi_source_kb_id = $1
            ORDER BY source_id
            """
            rows = await self.connection.fetch(query, kb_id)
        else:
            query = """
            SELECT 
                sd.source_id, sd.source_type, sd.enabled, sd.sync_schedule,
                sd.metadata_tags, ms.name as kb_name
            FROM source_definition sd
            JOIN multi_source_knowledge_base ms ON sd.multi_source_kb_id = ms.id
            ORDER BY ms.name, sd.source_id
            """
            rows = await self.connection.fetch(query)
        
        if not rows:
            print("No source definitions found")
            return
        
        for row in rows:
            status = "✅ Enabled" if row['enabled'] else "⏸️  Disabled"
            print(f"\n📂 {row['source_id']} ({row['source_type']})")
            if not kb_id:
                print(f"   KB: {row['kb_name']}")
            print(f"   Status: {status}")
            print(f"   Schedule: {row['sync_schedule'] or 'None'}")
            if row['metadata_tags']:
                print(f"   Tags: {dict(row['metadata_tags'])}")
    
    async def show_source_types(self):
        """Show available source types."""
        print("\n" + "="*60)
        print("🔧 AVAILABLE SOURCE TYPES")
        print("="*60)
        
        query = "SELECT name, class_name FROM source_type ORDER BY name"
        rows = await self.connection.fetch(query)
        
        for row in rows:
            print(f"• {row['name']}")
            print(f"  Class: {row['class_name']}")
    
    async def show_rag_types(self):
        """Show available RAG types."""
        print("\n" + "="*60)
        print("🤖 AVAILABLE RAG TYPES")
        print("="*60)
        
        query = "SELECT name, class_name FROM rag_type ORDER BY name"
        rows = await self.connection.fetch(query)
        
        for row in rows:
            print(f"• {row['name']}")
            print(f"  Class: {row['class_name']}")
    
    async def show_file_records(self, limit=10):
        """Show recent file records."""
        print("\n" + "="*60)
        print(f"📄 RECENT FILE RECORDS (Last {limit})")
        print("="*60)
        
        query = """
        SELECT 
            original_uri, uuid_filename, file_size, status,
            source_id, source_type, upload_time
        FROM file_record 
        ORDER BY upload_time DESC 
        LIMIT $1
        """
        
        rows = await self.connection.fetch(query, limit)
        
        if not rows:
            print("No file records found")
            return
        
        for row in rows:
            print(f"\n📄 {row['original_uri']}")
            print(f"   UUID: {row['uuid_filename']}")
            print(f"   Source: {row['source_id']} ({row['source_type']})")
            print(f"   Size: {row['file_size']} bytes")
            print(f"   Status: {row['status']}")
            print(f"   Uploaded: {row['upload_time']}")
    
    async def interactive_mode(self):
        """Interactive database exploration mode."""
        print("\n🔍 Interactive Database Viewer")
        print("Commands: tables, kbs, sources, types, files, quit")
        
        while True:
            try:
                command = input("\ndb> ").strip().lower()
                
                if command in ['quit', 'exit', 'q']:
                    break
                elif command in ['tables', 't']:
                    await self.show_tables()
                elif command in ['kbs', 'kb']:
                    await self.show_multi_source_kbs()
                elif command in ['sources', 's']:
                    await self.show_sources()
                elif command in ['types', 'type']:
                    await self.show_source_types()
                    await self.show_rag_types()
                elif command in ['files', 'f']:
                    await self.show_file_records()
                elif command == 'help':
                    print("Available commands:")
                    print("  tables - Show all database tables")
                    print("  kbs    - Show multi-source knowledge bases")
                    print("  sources - Show source definitions")
                    print("  types  - Show available source and RAG types")
                    print("  files  - Show recent file records")
                    print("  quit   - Exit viewer")
                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except EOFError:
                break

async def main():
    """Main function to run the database viewer."""
    print("PostgreSQL Database Viewer for Document Loader")
    print("=" * 60)
    
    viewer = DatabaseViewer()
    
    if not await viewer.connect():
        return
    
    try:
        # Show overview
        await viewer.show_tables()
        await viewer.show_multi_source_kbs()
        await viewer.show_sources()
        await viewer.show_source_types()
        await viewer.show_rag_types()
        await viewer.show_file_records(5)
        
        # Enter interactive mode
        await viewer.interactive_mode()
        
    finally:
        await viewer.close()

if __name__ == "__main__":
    asyncio.run(main())