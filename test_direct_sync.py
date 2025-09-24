#!/usr/bin/env python3
"""
Test script to directly test the multi-source sync functionality.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and load dotenv like the CLI does
from dotenv import load_dotenv
load_dotenv()

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository
from src.data.multi_source_models import create_multi_source_kb_from_config, SyncMode
from src.utils.config_utils import load_config_with_env_expansion
from src.core.multi_source_batch_runner import MultiSourceBatchRunner


async def test_direct_sync():
    """Test the multi-source sync directly."""
    
    print("🚀 Direct Multi-Source Sync Test")
    print("=" * 50)
    
    config_file = "configs/internal-audit-kb-config.json"
    
    # Step 1: Load config with environment expansion
    print("\n1️⃣ Loading config with environment variable expansion...")
    try:
        config = load_config_with_env_expansion(config_file)
        multi_kb = create_multi_source_kb_from_config(config)
        print(f"   ✅ Config loaded: {multi_kb.name}")
        print(f"   🔍 Sources: {len(multi_kb.sources)}")
        
        # Check actual credentials
        source_config = multi_kb.sources[0].source_config
        print(f"   🔍 Tenant ID: {source_config.get('tenant_id')}")
        print(f"   🔍 Client ID: {source_config.get('client_id')}")
        print(f"   🔍 Client Secret: {'SET' if source_config.get('client_secret') else 'NOT SET'}")
        
    except Exception as e:
        print(f"   ❌ Config loading failed: {e}")
        return
    
    # Step 2: Connect to database and check KB
    print("\n2️⃣ Connecting to database...")
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        multi_repo = MultiSourceRepository(db)
        existing_kb = await multi_repo.get_multi_source_kb_by_name(multi_kb.name)
        
        if existing_kb:
            print(f"   ✅ KB found: {existing_kb.name} (ID: {existing_kb.id})")
        else:
            print(f"   ❌ KB not found in database")
            await db.disconnect()
            return
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return
    
    # Step 3: Test batch runner creation
    print("\n3️⃣ Creating batch runner...")
    try:
        batch_runner = MultiSourceBatchRunner(multi_repo)
        print(f"   ✅ Batch runner created")
    except Exception as e:
        print(f"   ❌ Batch runner creation failed: {e}")
        await db.disconnect()
        return
    
    # Step 4: Test sync execution
    print("\n4️⃣ Starting sync...")
    try:
        await batch_runner.sync_multi_source_knowledge_base(
            kb_name=multi_kb.name,
            sync_mode=SyncMode.SEQUENTIAL,
            source_ids=None
        )
        print(f"   ✅ Sync completed successfully!")
        
    except Exception as e:
        print(f"   ❌ Sync failed: {e}")
        import traceback
        print(f"   📜 Traceback:")
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(test_direct_sync())