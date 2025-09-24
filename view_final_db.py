#!/usr/bin/env python3
"""
Final PostgreSQL database viewer - shows what was actually synced.
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


async def view_final_db():
    """Final view of database showing sync results."""
    
    print("🗄️  PostgreSQL Database - Sync Results")
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
        async with db.pool.acquire() as conn:
            
            # 1. Multi-source knowledge bases (what we created)
            print(f"\n1️⃣ Multi-Source Knowledge Bases:")
            print("-" * 40)
            
            multi_kbs = await conn.fetch("""
                SELECT id, name, description, rag_type, created_at
                FROM multi_source_knowledge_base 
                WHERE name IN ('PremiumRMs-kb', 'InternalAudit-kb')
                ORDER BY created_at DESC;
            """)
            
            for kb in multi_kbs:
                print(f"   📚 {kb['name']} (ID: {kb['id']})")
                print(f"      RAG Type: {kb['rag_type']}")
                print(f"      Created: {kb['created_at']}")
                print()
            
            # 2. Check file_record table schema first
            print(f"2️⃣ File Record Table Schema:")
            print("-" * 35)
            
            columns = await conn.fetch("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'file_record'
                ORDER BY ordinal_position;
            """)
            
            print(f"   📊 File record columns:")
            for col in columns:
                print(f"      • {col['column_name']} ({col['data_type']})")
            
            # 3. Get file records with correct column names
            print(f"\n3️⃣ File Records (Synced Files):")
            print("-" * 40)
            
            # First check what columns actually exist
            sample_record = await conn.fetchrow("SELECT * FROM file_record LIMIT 1;")
            if sample_record:
                available_columns = list(sample_record.keys())
                print(f"   📋 Available columns: {available_columns}")
                
                # Now get the actual records
                files = await conn.fetch("""
                    SELECT * FROM file_record 
                    ORDER BY id DESC
                    LIMIT 10;
                """)
                
                if files:
                    print(f"\n   📄 Found {len(files)} file records:")
                    for i, file_rec in enumerate(files, 1):
                        print(f"\n   📄 File {i}:")
                        for key, value in file_rec.items():
                            if key == 'file_hash' and value:
                                print(f"      {key}: {value[:16]}...")
                            elif key in ['source_uri', 'rag_uri'] and value and len(str(value)) > 60:
                                print(f"      {key}: {str(value)[:60]}...")
                            else:
                                print(f"      {key}: {value}")
                else:
                    print(f"   ✅ No file records found")
            else:
                print(f"   ✅ File record table is empty")
            
            # 4. Multi-source sync runs
            print(f"\n4️⃣ Multi-Source Sync Runs:")
            print("-" * 35)
            
            try:
                multi_syncs = await conn.fetch("""
                    SELECT * FROM multi_source_sync_run 
                    ORDER BY start_time DESC
                    LIMIT 5;
                """)
                
                if multi_syncs:
                    for sync in multi_syncs:
                        print(f"   🏃 Multi-Sync {sync['id']}:")
                        for key, value in sync.items():
                            print(f"      {key}: {value}")
                        print()
                else:
                    print(f"   ✅ No multi-source sync runs found")
                    
            except Exception as e:
                print(f"   ⚠️  Multi-source sync table: {e}")
            
            # 5. Source definitions
            print(f"5️⃣ Source Definitions:")
            print("-" * 30)
            
            try:
                sources = await conn.fetch("""
                    SELECT * FROM source_definition 
                    ORDER BY id DESC
                    LIMIT 10;
                """)
                
                if sources:
                    for source in sources:
                        print(f"   📁 Source {source['id']}:")
                        for key, value in source.items():
                            if key == 'source_config' and value:
                                # Parse JSON if it's a string
                                if isinstance(value, str):
                                    import json
                                    try:
                                        config = json.loads(value)
                                        print(f"      {key}: {list(config.keys())} keys")
                                    except:
                                        print(f"      {key}: {str(value)[:100]}...")
                                else:
                                    print(f"      {key}: {value}")
                            else:
                                print(f"      {key}: {value}")
                        print()
                else:
                    print(f"   ✅ No source definitions found")
                    
            except Exception as e:
                print(f"   ⚠️  Source definition table: {e}")
            
            # 6. Summary statistics
            print(f"6️⃣ Database Summary:")
            print("-" * 25)
            
            # Count records in each table
            tables_to_count = [
                'multi_source_knowledge_base',
                'knowledge_base', 
                'file_record',
                'sync_run',
                'source_definition'
            ]
            
            for table in tables_to_count:
                try:
                    count_result = await conn.fetchrow(f"SELECT COUNT(*) as count FROM {table};")
                    count = count_result['count']
                    print(f"   📊 {table}: {count} records")
                except Exception as e:
                    print(f"   ⚠️  {table}: {e}")
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(view_final_db())