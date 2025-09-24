#!/usr/bin/env python3
"""
Debug script to check what happens during sync execution.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and load dotenv like the CLI does
from dotenv import load_dotenv
load_dotenv()

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository
from src.data.multi_source_models import create_multi_source_kb_from_config
from src.utils.config_utils import load_config_with_env_expansion


async def debug_sync_environment():
    """Debug the sync environment step by step."""
    
    print("🔍 Comprehensive Sync Environment Debug")
    print("=" * 60)
    
    # Step 1: Check environment variables after dotenv loading
    print("\n1️⃣ Environment Variables (after dotenv loading):")
    env_vars = ['SHAREPOINT_TENANT_ID', 'SHAREPOINT_CLIENT_ID', 'SHAREPOINT_CLIENT_SECRET']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            display_value = f"{value[:10]}..." if 'SECRET' in var else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: NOT SET")
    
    # Step 2: Load and parse config file 
    print("\n2️⃣ Config File Processing:")
    config_file = "configs/internal-audit-kb-config.json"
    
    try:
        with open(config_file) as f:
            raw_config = f.read()
        
        print(f"   📄 Raw config (first 200 chars): {raw_config[:200]}...")
        
        # Parse JSON with environment expansion
        config = load_config_with_env_expansion(config_file)
        print(f"   ✅ JSON parsing successful")
        
        # Check source config values
        source_config = config['sources'][0]['source_config']
        print(f"\n   🔍 Source config values:")
        print(f"      tenant_id: {source_config.get('tenant_id')}")
        print(f"      client_id: {source_config.get('client_id')}")
        print(f"      client_secret: {source_config.get('client_secret')[:10]}..." if source_config.get('client_secret') else None)
        
        # Check if placeholders are still there
        if '${' in str(source_config):
            print(f"   ❌ Environment variable placeholders still present!")
            for key, value in source_config.items():
                if isinstance(value, str) and '${' in value:
                    print(f"      {key}: {value}")
        else:
            print(f"   ✅ No placeholders found - values should be resolved")
            
    except Exception as e:
        print(f"   ❌ Config file error: {e}")
        return
    
    # Step 3: Test multi-source KB creation
    print("\n3️⃣ Multi-source KB Creation:")
    try:
        multi_kb = create_multi_source_kb_from_config(config)
        print(f"   ✅ Multi-KB created: {multi_kb.name}")
        
        # Check the actual source config values in the created object
        source_def = multi_kb.sources[0]
        print(f"   🔍 Created source config:")
        sc = source_def.source_config
        print(f"      tenant_id: {sc.get('tenant_id')}")
        print(f"      client_id: {sc.get('client_id')}")
        print(f"      client_secret: {sc.get('client_secret')[:10]}..." if sc.get('client_secret') else None)
        
    except Exception as e:
        print(f"   ❌ Multi-KB creation failed: {e}")
        return
    
    # Step 4: Test database connection and lookup
    print("\n4️⃣ Database Connection and Lookup:")
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        multi_repo = MultiSourceRepository(db)
        existing_kb = await multi_repo.get_multi_source_kb_by_name(multi_kb.name)
        
        if existing_kb:
            print(f"   ✅ KB found in database: {existing_kb.name} (ID: {existing_kb.id})")
        else:
            print(f"   ❌ KB not found in database")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
    
    # Step 5: Test source creation with actual config
    print("\n5️⃣ Source Creation Test:")
    try:
        from src.core.factory import SourceFactory
        
        factory = SourceFactory()
        source_def = multi_kb.sources[0]
        
        print(f"   📋 Creating source: {source_def.source_type}")
        print(f"   📋 With config keys: {list(source_def.source_config.keys())}")
        
        # Create source
        source = await factory.create_source(source_def.source_type, source_def.source_config)
        print(f"   ✅ Source created: {type(source).__name__}")
        
        # Check if source has the config values
        if hasattr(source, 'sp_config'):
            sp_config = source.sp_config
            print(f"   🔍 Source SP config:")
            print(f"      tenant_id: {getattr(sp_config, 'tenant_id', 'NOT SET')}")
            print(f"      client_id: {getattr(sp_config, 'client_id', 'NOT SET')}")
            print(f"      client_secret: {'SET' if getattr(sp_config, 'client_secret', None) else 'NOT SET'}")
        
        # Test initialization
        print(f"   🚀 Testing source initialization...")
        await source.initialize()
        print(f"   ✅ Source initialization successful!")
        
        # Check session
        if hasattr(source, '_session'):
            session_status = "SET" if source._session else "NOT SET"
            print(f"   🔍 Session status: {session_status}")
        
        # Cleanup
        if hasattr(source, 'cleanup'):
            await source.cleanup()
        
    except Exception as e:
        print(f"   ❌ Source creation/initialization failed: {e}")
        import traceback
        print(f"   📜 Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_sync_environment())