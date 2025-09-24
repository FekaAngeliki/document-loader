#!/usr/bin/env python3
"""
Working PostgreSQL database viewer for sync data.
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


async def view_db_working():
    """Working view of database content."""
    
    print("🗄️  PostgreSQL Database - Sync Content")
    print("=" * 50)
    
    # Connect to database
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        print("✅ Database connected")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    try:
        # Use the connection pool directly
        async with db.pool.acquire() as conn:
            
            # 1. List all tables
            print(f"\n1️⃣ Database Tables:")
            print("-" * 25)
            
            tables = await conn.fetch("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename;
            """)
            
            table_list = [table['tablename'] for table in tables]
            print(f"   📊 Found {len(tables)} tables:")
            for table in table_list:
                print(f"      • {table}")
            
            # 2. Multi-source knowledge bases
            if 'multi_source_knowledge_base' in table_list:
                print(f"\n2️⃣ Multi-Source Knowledge Bases:")
                print("-" * 40)
                
                multi_kbs = await conn.fetch("""
                    SELECT id, name, description, rag_type, created_at
                    FROM multi_source_knowledge_base 
                    ORDER BY created_at DESC;
                """)
                
                for kb in multi_kbs:
                    print(f"   📚 {kb['name']} (ID: {kb['id']})")
                    print(f"      Description: {kb['description']}")
                    print(f"      RAG Type: {kb['rag_type']}")
                    print(f"      Created: {kb['created_at']}")
                    print()
            
            # 3. Regular knowledge bases
            if 'knowledge_base' in table_list:
                print(f"3️⃣ Regular Knowledge Bases:")
                print("-" * 30)
                
                kbs = await conn.fetch("""
                    SELECT id, name, source_type, rag_type, created_at
                    FROM knowledge_base 
                    ORDER BY created_at DESC
                    LIMIT 5;
                """)
                
                if kbs:
                    for kb in kbs:
                        print(f"   📚 {kb['name']} (ID: {kb['id']})")
                        print(f"      {kb['source_type']} → {kb['rag_type']}")
                        print(f"      Created: {kb['created_at']}")
                        print()
                else:
                    print(f"   ✅ No regular knowledge bases")
            
            # 4. Sync runs
            if 'sync_run' in table_list:
                print(f"4️⃣ Sync Runs:")
                print("-" * 20)
                
                syncs = await conn.fetch("""
                    SELECT sr.id, sr.knowledge_base_id, sr.start_time, sr.end_time, 
                           sr.total_files, sr.new_files, sr.modified_files, sr.status,
                           kb.name as kb_name
                    FROM sync_run sr
                    LEFT JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
                    ORDER BY sr.start_time DESC
                    LIMIT 10;
                """)
                
                if syncs:
                    for sync in syncs:
                        kb_name = sync['kb_name'] or f"KB-{sync['knowledge_base_id']}"
                        print(f"   🏃 Sync {sync['id']} - {kb_name}")
                        print(f"      Status: {sync['status']}")
                        print(f"      Files: {sync['total_files']} total, {sync['new_files']} new, {sync['modified_files']} modified")
                        print(f"      Time: {sync['start_time']} → {sync['end_time'] or 'Running'}")
                        print()
                else:
                    print(f"   ✅ No sync runs found")
            
            # 5. File records
            if 'file_record' in table_list:
                print(f"5️⃣ File Records:")
                print("-" * 20)
                
                files = await conn.fetch("""
                    SELECT fr.id, fr.knowledge_base_id, fr.source_uri, fr.rag_uri, 
                           fr.file_size, fr.status, fr.upload_time, fr.file_hash,
                           kb.name as kb_name
                    FROM file_record fr
                    LEFT JOIN knowledge_base kb ON fr.knowledge_base_id = kb.id
                    ORDER BY fr.upload_time DESC
                    LIMIT 15;
                """)
                
                if files:
                    print(f"   📊 Found {len(files)} recent file records:")
                    for file_rec in files:
                        kb_name = file_rec['kb_name'] or f"KB-{file_rec['knowledge_base_id']}"
                        print(f"\n   📄 File {file_rec['id']} - {kb_name}")
                        print(f"      Source: {file_rec['source_uri']}")
                        print(f"      RAG URI: {file_rec['rag_uri']}")
                        print(f"      Size: {file_rec['file_size']:,} bytes")
                        print(f"      Status: {file_rec['status']}")
                        print(f"      Hash: {file_rec['file_hash'][:16]}...")
                        print(f"      Uploaded: {file_rec['upload_time']}")
                else:
                    print(f"   ✅ No file records found")
            
            # 6. Check for multi-source specific tables
            multi_tables = [t for t in table_list if 'multi' in t or 'enhanced' in t]
            if multi_tables:
                print(f"\n6️⃣ Multi-Source Specific Tables:")
                print("-" * 40)
                
                for table_name in multi_tables:
                    print(f"   📋 Table: {table_name}")
                    
                    try:
                        # Get count
                        count_result = await conn.fetchrow(f"SELECT COUNT(*) as count FROM {table_name};")
                        count = count_result['count']
                        print(f"      📊 Records: {count}")
                        
                        if count > 0:
                            # Get sample
                            sample = await conn.fetch(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 3;")
                            for row in sample:
                                print(f"         ID {row.get('id', 'N/A')}: {dict(row)}")
                    except Exception as e:
                        print(f"      ⚠️  Cannot access: {e}")
                    print()
            
            # 7. Database stats
            print(f"7️⃣ Database Statistics:")
            print("-" * 30)
            
            for table_name in ['knowledge_base', 'sync_run', 'file_record', 'multi_source_knowledge_base']:
                if table_name in table_list:
                    try:
                        count_result = await conn.fetchrow(f"SELECT COUNT(*) as count FROM {table_name};")
                        count = count_result['count']
                        print(f"   📊 {table_name}: {count} records")
                    except Exception as e:
                        print(f"   ⚠️  {table_name}: Cannot count - {e}")
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(view_db_working())