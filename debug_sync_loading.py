#!/usr/bin/env python3
"""
Debug what the sync process is actually loading.
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
from src.core.multi_source_batch_runner import MultiSourceBatchRunner


async def debug_sync_loading():
    """Debug what the sync process loads."""
    
    print("🔍 Debug Sync Loading Process")
    print("=" * 50)
    
    # Step 1: Check database connection
    print("1️⃣ Connecting to database...")
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        multi_repo = MultiSourceRepository(db)
        print("   ✅ Database connected")
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return
    
    # Step 2: Create batch runner (like the CLI does)
    print("\n2️⃣ Creating batch runner...")
    try:
        batch_runner = MultiSourceBatchRunner(multi_repo)
        print("   ✅ Batch runner created")
    except Exception as e:
        print(f"   ❌ Batch runner creation failed: {e}")
        await db.disconnect()
        return
    
    # Step 3: Test the _load_multi_source_kb method directly
    print("\n3️⃣ Testing KB loading...")
    try:
        kb_name = "InternalAudit-kb"
        multi_kb = await batch_runner._load_multi_source_kb(kb_name)
        
        if multi_kb:
            print(f"   ✅ KB loaded: {multi_kb.name} (ID: {multi_kb.id})")
            
            # Check the source config values
            source = multi_kb.sources[0]
            print(f"   📁 Source: {source.source_id}")
            print(f"   📋 Source config:")
            
            config = source.source_config
            for key, value in config.items():
                if key in ['tenant_id', 'client_id']:
                    print(f"      {key}: {value}")
                elif key in ['client_secret']:
                    print(f"      {key}: {'SET' if value else 'NOT SET'}")
                elif key == 'site_id':
                    print(f"      {key}: {value}")
            
            # Check for any placeholder values
            config_str = str(config)
            if '${' in config_str:
                print(f"   ❌ Placeholders found in loaded config!")
                for key, value in config.items():
                    if isinstance(value, str) and '${' in value:
                        print(f"      {key}: {value}")
            else:
                print(f"   ✅ No placeholders in loaded config")
                
        else:
            print(f"   ❌ KB not found: {kb_name}")
    
    except Exception as e:
        print(f"   ❌ KB loading failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Test source creation directly
    print("\n4️⃣ Testing source creation...")
    try:
        if 'multi_kb' in locals() and multi_kb:
            source_def = multi_kb.sources[0]
            
            print(f"   📋 Creating source with config:")
            for key, value in source_def.source_config.items():
                if key in ['tenant_id', 'client_id', 'site_id']:
                    print(f"      {key}: {value}")
                elif key in ['client_secret']:
                    print(f"      {key}: {'SET' if value else 'NOT SET'}")
            
            # Import the factory here to avoid circular imports
            from src.core.factory import Factory
            
            factory = Factory(multi_repo)
            source = await factory.create_source(source_def.source_type, source_def.source_config)
            
            print(f"   ✅ Source created: {type(source).__name__}")
            
            # Check the source's internal config
            if hasattr(source, 'sp_config'):
                sp_config = source.sp_config
                print(f"   🔍 Source internal config:")
                print(f"      tenant_id: {getattr(sp_config, 'tenant_id', 'NOT SET')}")
                print(f"      client_id: {getattr(sp_config, 'client_id', 'NOT SET')}")
                print(f"      client_secret: {'SET' if getattr(sp_config, 'client_secret', None) else 'NOT SET'}")
                print(f"      site_id: {getattr(sp_config, 'site_id', 'NOT SET')}")
                
    except Exception as e:
        print(f"   ❌ Source creation failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(debug_sync_loading())