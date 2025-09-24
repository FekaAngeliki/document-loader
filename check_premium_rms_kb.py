#!/usr/bin/env python3
"""
Check and create PremiumRMs-kb if needed.
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


async def check_premium_rms_kb():
    """Check and create PremiumRMs-kb if needed."""
    
    print("🔍 Checking PremiumRMs-kb")
    print("=" * 40)
    
    config_file = "configs/premium-rms-kb-config.json"
    kb_name = "PremiumRMs-kb"
    
    # Step 1: Load config with environment expansion
    print("1️⃣ Loading config with environment variable expansion...")
    try:
        config = load_config_with_env_expansion(config_file)
        multi_kb = create_multi_source_kb_from_config(config)
        
        # Verify credentials are expanded
        source_config = multi_kb.sources[0].source_config
        tenant_id = source_config.get('tenant_id')
        client_id = source_config.get('client_id')
        client_secret = source_config.get('client_secret')
        site_id = source_config.get('site_id')
        
        print(f"   ✅ Config loaded with expanded variables:")
        print(f"   📋 Tenant ID: {tenant_id}")
        print(f"   📋 Client ID: {client_id}")
        print(f"   📋 Client Secret: {'SET' if client_secret else 'NOT SET'}")
        print(f"   📋 Site ID: {site_id}")
        
        if '${' in str(source_config):
            print(f"   ❌ Still contains placeholders!")
            for key, value in source_config.items():
                if isinstance(value, str) and '${' in value:
                    print(f"      {key}: {value}")
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
    
    # Step 3: Check if KB exists
    print("\n3️⃣ Checking if KB exists...")
    try:
        existing_kb = await multi_repo.get_multi_source_kb_by_name(kb_name)
        
        if existing_kb:
            print(f"   ✅ Found existing KB: {existing_kb.name} (ID: {existing_kb.id})")
            
            # Check if it has placeholder values
            old_source_config = existing_kb.sources[0].source_config
            if '${' in str(old_source_config):
                print(f"   ❌ KB has placeholder values - needs fixing")
                
                # Delete and recreate
                print(f"   🗑️  Deleting old KB...")
                await multi_repo.delete_multi_source_kb(existing_kb.id)
                print(f"   ✅ Old KB deleted")
                
                # Create new one
                print(f"   📝 Creating new KB with expanded values...")
                new_kb_id = await multi_repo.create_multi_source_kb(multi_kb)
                print(f"   ✅ New KB created with ID: {new_kb_id}")
                
            else:
                print(f"   ✅ KB already has expanded values")
                # Show current values
                print(f"   📋 Current values:")
                sc = old_source_config
                print(f"      tenant_id: {sc.get('tenant_id')}")
                print(f"      client_id: {sc.get('client_id')}")
                print(f"      site_id: {sc.get('site_id')}")
        else:
            print(f"   ❌ KB not found - creating new one")
            
            # Create new KB
            print(f"   📝 Creating new KB...")
            new_kb_id = await multi_repo.create_multi_source_kb(multi_kb)
            print(f"   ✅ New KB created with ID: {new_kb_id}")
            
    except Exception as e:
        print(f"   ❌ KB check/creation failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(check_premium_rms_kb())