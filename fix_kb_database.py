#!/usr/bin/env python3
"""
Fix the InternalAudit-kb in database with proper environment variable expansion.
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
from src.data.multi_source_models import create_multi_source_kb_from_config
from src.utils.config_utils import load_config_with_env_expansion


async def fix_kb_database():
    """Fix the KB in database with correct environment variables."""
    
    print("🔧 Fixing InternalAudit-kb in Database")
    print("=" * 50)
    
    config_file = "configs/internal-audit-kb-config.json"
    kb_name = "InternalAudit-kb"
    
    # Step 1: Load config with environment expansion
    print("\n1️⃣ Loading config with environment variable expansion...")
    try:
        config = load_config_with_env_expansion(config_file)
        multi_kb = create_multi_source_kb_from_config(config)
        
        # Verify credentials are expanded
        source_config = multi_kb.sources[0].source_config
        tenant_id = source_config.get('tenant_id')
        client_id = source_config.get('client_id')
        client_secret = source_config.get('client_secret')
        
        print(f"   ✅ Config loaded with expanded variables:")
        print(f"   📋 Tenant ID: {tenant_id}")
        print(f"   📋 Client ID: {client_id}")
        print(f"   📋 Client Secret: {'SET' if client_secret else 'NOT SET'}")
        
        if '${' in str(source_config):
            print(f"   ❌ Still contains placeholders!")
            return
        
    except Exception as e:
        print(f"   ❌ Config loading failed: {e}")
        return
    
    # Step 2: Connect to database
    print("\n2️⃣ Connecting to database...")
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        multi_repo = MultiSourceRepository(db)
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return
    
    # Step 3: Check existing KB
    print("\n3️⃣ Checking existing KB...")
    try:
        existing_kb = await multi_repo.get_multi_source_kb_by_name(kb_name)
        
        if existing_kb:
            print(f"   ✅ Found existing KB: {existing_kb.name} (ID: {existing_kb.id})")
            
            # Check if it has placeholder values
            old_source_config = existing_kb.sources[0].source_config
            if '${' in str(old_source_config):
                print(f"   ❌ KB has placeholder values - needs fixing")
            else:
                print(f"   ✅ KB already has expanded values")
                await db.disconnect()
                return
        else:
            print(f"   ❌ KB not found")
            await db.disconnect()
            return
            
    except Exception as e:
        print(f"   ❌ KB check failed: {e}")
        await db.disconnect()
        return
    
    # Step 4: Delete old KB and create new one
    print("\n4️⃣ Recreating KB with correct values...")
    try:
        # Delete old KB
        print(f"   🗑️  Deleting old KB...")
        await multi_repo.delete_multi_source_kb(existing_kb.id)
        print(f"   ✅ Old KB deleted")
        
        # Create new KB with expanded values
        print(f"   📝 Creating new KB with expanded values...")
        new_kb_id = await multi_repo.create_multi_source_kb(multi_kb)
        print(f"   ✅ New KB created with ID: {new_kb_id}")
        
        # Verify the new KB
        print(f"   🔍 Verifying new KB...")
        new_kb = await multi_repo.get_multi_source_kb_by_name(kb_name)
        if new_kb:
            new_source_config = new_kb.sources[0].source_config
            print(f"   📋 New tenant_id: {new_source_config.get('tenant_id')}")
            print(f"   📋 New client_id: {new_source_config.get('client_id')}")
            print(f"   ✅ KB successfully recreated with proper values!")
        
    except Exception as e:
        print(f"   ❌ KB recreation failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(fix_kb_database())