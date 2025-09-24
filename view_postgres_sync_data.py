#!/usr/bin/env python3
"""
View the PostgreSQL database content from sync operations.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and load dotenv
from dotenv import load_dotenv
load_dotenv()

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository


async def view_postgres_sync_data():
    """View PostgreSQL database content from syncs."""
    
    print("🗄️  PostgreSQL Database - Sync Data Viewer")
    print("=" * 60)
    
    # Connect to database
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        # Use raw SQL to see all tables
        print("1️⃣ Available Tables:")
        print("-" * 30)
        
        # Get all table names
        tables_query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename;
        """
        
        result = await db.execute_query(tables_query)
        table_names = [row['tablename'] for row in result]
        
        for table in table_names:
            print(f"   📊 {table}")
        
        # 2. Multi-Source Knowledge Bases
        print(f"\n2️⃣ Multi-Source Knowledge Bases:")
        print("-" * 40)
        
        multi_kb_query = """
        SELECT id, name, description, rag_type, created_at
        FROM multi_source_knowledge_base 
        ORDER BY created_at DESC;
        """
        
        try:
            multi_kbs = await db.execute_query(multi_kb_query)
            for kb in multi_kbs:
                print(f"   📚 {kb['name']} (ID: {kb['id']})")
                print(f"      Description: {kb['description']}")
                print(f"      RAG Type: {kb['rag_type']}")
                print(f"      Created: {kb['created_at']}")
                print()
        except Exception as e:
            print(f"   ℹ️  Multi-source KB table not accessible: {e}")
        
        # 3. Regular Knowledge Bases (if any)
        print(f"3️⃣ Regular Knowledge Bases:")
        print("-" * 30)
        
        kb_query = """
        SELECT id, name, description, source_type, rag_type, created_at
        FROM knowledge_base 
        ORDER BY created_at DESC
        LIMIT 10;
        """
        
        try:
            kbs = await db.execute_query(kb_query)
            if kbs:
                for kb in kbs:
                    print(f"   📚 {kb['name']} (ID: {kb['id']})")
                    print(f"      Source: {kb['source_type']} → RAG: {kb['rag_type']}")
                    print(f"      Created: {kb['created_at']}")
                    print()
            else:
                print(f"   ✅ No regular knowledge bases found")
        except Exception as e:
            print(f"   ℹ️  Knowledge base table not accessible: {e}")
        
        # 4. Sync Runs
        print(f"4️⃣ Sync Runs:")
        print("-" * 20)
        
        sync_runs_query = """
        SELECT sr.id, sr.knowledge_base_id, kb.name as kb_name, sr.start_time, sr.end_time, 
               sr.total_files, sr.new_files, sr.modified_files, sr.deleted_files, sr.status
        FROM sync_run sr
        LEFT JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
        ORDER BY sr.start_time DESC
        LIMIT 10;
        """
        
        try:
            sync_runs = await db.execute_query(sync_runs_query)
            if sync_runs:
                for run in sync_runs:
                    print(f"   🏃 Sync Run {run['id']} - {run['kb_name'] or 'Unknown KB'}")
                    print(f"      Status: {run['status']}")
                    print(f"      Start: {run['start_time']}")
                    print(f"      End: {run['end_time'] or 'Running'}")
                    print(f"      Files: {run['total_files']} total, {run['new_files']} new, {run['modified_files']} modified")
                    print()
            else:
                print(f"   ✅ No sync runs found")
        except Exception as e:
            print(f"   ℹ️  Sync runs table not accessible: {e}")
        
        # 5. File Records
        print(f"5️⃣ File Records (Recent):")
        print("-" * 30)
        
        file_records_query = """
        SELECT fr.id, fr.knowledge_base_id, kb.name as kb_name, 
               fr.source_uri, fr.rag_uri, fr.file_hash, fr.file_size, 
               fr.status, fr.upload_time
        FROM file_record fr
        LEFT JOIN knowledge_base kb ON fr.knowledge_base_id = kb.id
        ORDER BY fr.upload_time DESC
        LIMIT 15;
        """
        
        try:
            file_records = await db.execute_query(file_records_query)
            if file_records:
                for record in file_records:
                    kb_name = record['kb_name'] or 'Unknown KB'
                    print(f"   📄 {kb_name} (KB ID: {record['knowledge_base_id']})")
                    print(f"      Source: {record['source_uri']}")
                    print(f"      RAG URI: {record['rag_uri']}")
                    print(f"      Size: {record['file_size']} bytes")
                    print(f"      Status: {record['status']}")
                    print(f"      Uploaded: {record['upload_time']}")
                    print(f"      Hash: {record['file_hash'][:16]}...")
                    print()
            else:
                print(f"   ✅ No file records found")
        except Exception as e:
            print(f"   ℹ️  File records table not accessible: {e}")
        
        # 6. Multi-source specific tables (if they exist)
        print(f"6️⃣ Multi-Source Enhanced Records:")
        print("-" * 40)
        
        # Check for enhanced file records
        enhanced_query = """
        SELECT * FROM information_schema.tables 
        WHERE table_name LIKE '%multi%' OR table_name LIKE '%enhanced%'
        ORDER BY table_name;
        """
        
        try:
            enhanced_tables = await db.execute_query(enhanced_query)
            if enhanced_tables:
                for table in enhanced_tables:
                    table_name = table['table_name']
                    print(f"   📋 Found table: {table_name}")
                    
                    # Try to get some sample data
                    sample_query = f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 3;"
                    try:
                        sample_data = await db.execute_query(sample_query)
                        if sample_data:
                            print(f"      📊 {len(sample_data)} recent records")
                            for row in sample_data:
                                print(f"         ID: {row.get('id', 'N/A')}")
                        else:
                            print(f"      📊 No records")
                    except Exception as e:
                        print(f"      ⚠️  Cannot access: {e}")
                    print()
            else:
                print(f"   ✅ No multi-source specific tables found")
        except Exception as e:
            print(f"   ℹ️  Enhanced tables check failed: {e}")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    finally:
        if 'db' in locals():
            await db.disconnect()


if __name__ == "__main__":
    asyncio.run(view_postgres_sync_data())