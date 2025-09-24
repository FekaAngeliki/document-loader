#!/usr/bin/env python3
"""
Check KB credentials in the database.
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


async def check_kb_credentials():
    """Check KB credentials."""
    
    print("🔍 Checking KB Credentials")
    print("=" * 40)
    
    # Connect to database
    try:
        config_db = DatabaseConfig()
        db = Database(config_db)
        await db.connect()
        
        multi_repo = MultiSourceRepository(db)
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    try:
        # Check PremiumRMs-kb
        print("📚 PremiumRMs-kb:")
        premium_kb = await multi_repo.get_multi_source_kb_by_name("PremiumRMs-kb")
        
        if premium_kb:
            print(f"   ✅ Found KB: {premium_kb.name} (ID: {premium_kb.id})")
            
            source = premium_kb.sources[0]
            config = source.source_config
            
            print(f"   📋 Source credentials:")
            print(f"      tenant_id: {config.get('tenant_id')}")
            print(f"      client_id: {config.get('client_id')}")
            print(f"      client_secret: {'SET' if config.get('client_secret') else 'NOT SET'}")
            print(f"      site_id: {config.get('site_id')}")
            
            # Check for placeholders
            config_str = str(config)
            if '${' in config_str:
                print(f"   ❌ PLACEHOLDERS FOUND:")
                for key, value in config.items():
                    if isinstance(value, str) and '${' in value:
                        print(f"      {key}: {value}")
            else:
                print(f"   ✅ No placeholders - credentials are expanded")
        
        else:
            print(f"   ❌ PremiumRMs-kb not found")
        
    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(check_kb_credentials())