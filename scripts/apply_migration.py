#!/usr/bin/env python3
"""
Apply Database Migration for Multi-Source Support

This script applies the multi-source migration to the PostgreSQL database.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.database import Database, DatabaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def apply_migration():
    """Apply the multi-source migration."""
    
    print("Applying Multi-Source Database Migration")
    print("=" * 50)
    
    # Read migration file
    migration_file = Path(__file__).parent.parent / "migrations" / "001_multi_source_support.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📂 Reading migration file: {migration_file}")
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
    except Exception as e:
        print(f"❌ Failed to read migration file: {e}")
        return False
    
    # Connect to database
    config = DatabaseConfig()
    print(f"🔌 Connecting to database: {config.host}:{config.port}/{config.database}")
    
    db = Database(config)
    
    try:
        await db.connect()
        print("✅ Connected to database")
        
        # Check if migration already applied
        check_query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'multi_source_knowledge_base'
            )
        """
        
        already_applied = await db.fetchval(check_query)
        
        if already_applied:
            print("⚠️  Migration appears to already be applied")
            print("   multi_source_knowledge_base table exists")
            
            # Ask for confirmation
            response = input("Do you want to continue anyway? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("❌ Migration cancelled by user")
                return False
        
        # Split migration into individual statements
        statements = []
        current_statement = ""
        
        for line in migration_sql.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('--'):
                continue
            
            current_statement += line + "\n"
            
            # End of statement
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        print(f"📝 Found {len(statements)} SQL statements to execute")
        
        # Execute migration statements
        successful = 0
        failed = 0
        
        for i, statement in enumerate(statements, 1):
            try:
                print(f"⚙️  Executing statement {i}/{len(statements)}...")
                logger.debug(f"SQL: {statement[:100]}...")
                
                await db.execute(statement)
                successful += 1
                
            except Exception as e:
                print(f"❌ Statement {i} failed: {e}")
                logger.error(f"Failed statement: {statement[:200]}...")
                failed += 1
                
                # For some errors, we might want to continue
                if "already exists" in str(e).lower():
                    print(f"   ⚠️  Object already exists, continuing...")
                    successful += 1
                    failed -= 1
                else:
                    print(f"   ❌ Critical error, stopping migration")
                    break
        
        print(f"\n📊 Migration Results:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📝 Total: {len(statements)}")
        
        if failed == 0:
            print("\n🎉 Migration completed successfully!")
            
            # Verify migration
            await verify_migration(db)
            return True
        else:
            print(f"\n⚠️  Migration completed with {failed} errors")
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.exception("Detailed error:")
        return False
    finally:
        await db.disconnect()
        print("🔌 Database connection closed")

async def verify_migration(db: Database):
    """Verify that the migration was applied correctly."""
    
    print("\n🔍 Verifying migration...")
    
    # Check for new tables
    tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN (
            'multi_source_knowledge_base',
            'source_definition', 
            'multi_source_sync_run'
        )
        ORDER BY table_name
    """
    
    tables = await db.fetch(tables_query)
    table_names = [row['table_name'] for row in tables]
    
    expected_tables = [
        'multi_source_knowledge_base',
        'source_definition',
        'multi_source_sync_run'
    ]
    
    print("📋 Checking new tables:")
    for table in expected_tables:
        if table in table_names:
            print(f"   ✅ {table}")
        else:
            print(f"   ❌ {table} - NOT FOUND")
    
    # Check for new columns in file_record
    columns_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'file_record'
        AND column_name IN (
            'source_id', 'source_type', 'source_path', 'content_type',
            'source_metadata', 'rag_metadata', 'tags'
        )
        ORDER BY column_name
    """
    
    columns = await db.fetch(columns_query)
    column_names = [row['column_name'] for row in columns]
    
    expected_columns = [
        'source_id', 'source_type', 'source_path', 'content_type',
        'source_metadata', 'rag_metadata', 'tags'
    ]
    
    print("\n📋 Checking enhanced file_record columns:")
    for column in expected_columns:
        if column in column_names:
            print(f"   ✅ {column}")
        else:
            print(f"   ❌ {column} - NOT FOUND")
    
    # Check for views
    views_query = """
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'public' 
        AND table_name = 'legacy_knowledge_base_view'
    """
    
    views = await db.fetch(views_query)
    if views:
        print("\n📋 Checking views:")
        print("   ✅ legacy_knowledge_base_view")
    else:
        print("\n📋 Checking views:")
        print("   ❌ legacy_knowledge_base_view - NOT FOUND")
    
    # Check for functions
    functions_query = """
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name IN ('get_sources_for_multi_kb', 'get_file_stats_by_source')
    """
    
    functions = await db.fetch(functions_query)
    function_names = [row['routine_name'] for row in functions]
    
    print("\n📋 Checking functions:")
    for func in ['get_sources_for_multi_kb', 'get_file_stats_by_source']:
        if func in function_names:
            print(f"   ✅ {func}")
        else:
            print(f"   ❌ {func} - NOT FOUND")
    
    # Check source types
    source_types_query = """
        SELECT name FROM source_type 
        WHERE name IN ('enterprise_sharepoint', 'onedrive')
    """
    
    source_types = await db.fetch(source_types_query)
    source_type_names = [row['name'] for row in source_types]
    
    print("\n📋 Checking new source types:")
    for source_type in ['enterprise_sharepoint', 'onedrive']:
        if source_type in source_type_names:
            print(f"   ✅ {source_type}")
        else:
            print(f"   ❌ {source_type} - NOT FOUND")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = asyncio.run(apply_migration())
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Run tests: python test_scripts/test_postgres_multi_source.py")
        print("2. Test CLI: document-loader multi-source create-template test-kb")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check the logs and fix any issues.")
        sys.exit(1)