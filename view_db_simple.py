#!/usr/bin/env python3
"""
Simple PostgreSQL database viewer for sync data.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and load dotenv
from dotenv import load_dotenv
load_dotenv()

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository


async def view_db_simple():
    """Simple view of database content."""
    
    print("🗄️  PostgreSQL Database - Simple Viewer")
    print("=" * 50)
    
    # Connect to database
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        multi_repo = MultiSourceRepository(db)
        
        print("✅ Database connected")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    try:
        # 1. Check multi-source KBs
        print(f"\n1️⃣ Multi-Source Knowledge Bases:")
        print("-" * 40)
        
        # Try to get PremiumRMs-kb specifically
        try:
            premium_kb = await multi_repo.get_multi_source_kb_by_name("PremiumRMs-kb")
            if premium_kb:
                print(f"   📚 {premium_kb.name} (ID: {premium_kb.id})")
                print(f"      Description: {premium_kb.description}")
                print(f"      RAG Type: {premium_kb.rag_type}")
                print(f"      Sources: {len(premium_kb.sources)}")
                
                for i, source in enumerate(premium_kb.sources, 1):
                    print(f"         Source {i}: {source.source_id} ({source.source_type})")
                    print(f"         Site ID: {source.source_config.get('site_id', 'Not set')}")
                
            else:
                print(f"   ❌ PremiumRMs-kb not found")
        except Exception as e:
            print(f"   ❌ Error checking PremiumRMs-kb: {e}")
        
        # Also check InternalAudit-kb
        try:
            audit_kb = await multi_repo.get_multi_source_kb_by_name("InternalAudit-kb")
            if audit_kb:
                print(f"\n   📚 {audit_kb.name} (ID: {audit_kb.id})")
                print(f"      Description: {audit_kb.description}")
                print(f"      RAG Type: {audit_kb.rag_type}")
                print(f"      Sources: {len(audit_kb.sources)}")
        except Exception as e:
            print(f"   ❌ Error checking InternalAudit-kb: {e}")
        
        # 2. Use raw connection to check tables
        print(f"\n2️⃣ Database Tables (Raw Query):")
        print("-" * 35)
        
        # Get connection pool
        pool = db._pool
        if pool:
            async with pool.acquire() as conn:
                # List tables
                tables = await conn.fetch("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    ORDER BY tablename;
                """)
                
                print(f"   📊 Found {len(tables)} tables:")
                for table in tables:
                    print(f"      • {table['tablename']}")
                
                # Check knowledge_base table
                print(f"\n3️⃣ Knowledge Base Records:")
                print("-" * 30)
                
                try:
                    kb_records = await conn.fetch("""
                        SELECT id, name, source_type, rag_type, created_at
                        FROM knowledge_base 
                        ORDER BY created_at DESC
                        LIMIT 5;
                    """)
                    
                    if kb_records:
                        for kb in kb_records:
                            print(f"   📚 {kb['name']} (ID: {kb['id']})")
                            print(f"      {kb['source_type']} → {kb['rag_type']}")
                            print(f"      Created: {kb['created_at']}")
                            print()
                    else:
                        print(f"   ✅ No regular knowledge bases found")
                        
                except Exception as e:
                    print(f"   ⚠️  Knowledge base table: {e}")
                
                # Check sync_run table
                print(f"4️⃣ Recent Sync Runs:")
                print("-" * 25)
                
                try:
                    sync_records = await conn.fetch("""
                        SELECT id, knowledge_base_id, start_time, end_time, 
                               total_files, new_files, status
                        FROM sync_run 
                        ORDER BY start_time DESC
                        LIMIT 5;
                    """)
                    
                    if sync_records:
                        for sync in sync_records:
                            print(f"   🏃 Sync {sync['id']} (KB: {sync['knowledge_base_id']})")
                            print(f"      Status: {sync['status']}")
                            print(f"      Files: {sync['total_files']} total, {sync['new_files']} new")
                            print(f"      Time: {sync['start_time']} → {sync['end_time'] or 'Running'}")
                            print()
                    else:
                        print(f"   ✅ No sync runs found")
                        
                except Exception as e:
                    print(f"   ⚠️  Sync run table: {e}")
                
                # Check file_record table
                print(f"5️⃣ Recent File Records:")
                print("-" * 30)
                
                try:
                    file_records = await conn.fetch("""
                        SELECT id, knowledge_base_id, source_uri, rag_uri, 
                               file_size, status, upload_time
                        FROM file_record 
                        ORDER BY upload_time DESC
                        LIMIT 10;
                    """)
                    
                    if file_records:
                        for file_rec in file_records:
                            print(f"   📄 File {file_rec['id']} (KB: {file_rec['knowledge_base_id']})")
                            print(f"      Source: {file_rec['source_uri']}")
                            print(f"      RAG: {file_rec['rag_uri']}")
                            print(f"      Size: {file_rec['file_size']} bytes")
                            print(f"      Status: {file_rec['status']}")
                            print(f"      Uploaded: {file_rec['upload_time']}")
                            print()
                    else:
                        print(f"   ✅ No file records found")
                        
                except Exception as e:
                    print(f"   ⚠️  File record table: {e}")
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(view_db_simple())