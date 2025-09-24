#!/usr/bin/env python3
"""
Check all knowledge bases in the database to see which ones have placeholder values.
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


async def check_all_kbs():
    """Check all knowledge bases in the database."""
    
    print("🔍 Checking All Knowledge Bases in Database")
    print("=" * 60)
    
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
        # Get all multi-source KBs
        print("📋 Multi-Source Knowledge Bases:")
        print("-" * 40)
        
        # This would need a method to get all KBs, let's try to get by name first
        kb_names = ["InternalAudit-kb"]  # Add more if you know them
        
        for kb_name in kb_names:
            print(f"\n🔍 Checking KB: {kb_name}")
            
            try:
                kb = await multi_repo.get_multi_source_kb_by_name(kb_name)
                
                if kb:
                    print(f"   ✅ Found KB: {kb.name} (ID: {kb.id})")
                    
                    # Check each source for placeholder values
                    for i, source in enumerate(kb.sources):
                        print(f"   📁 Source {i+1}: {source.source_id}")
                        print(f"      Type: {source.source_type}")
                        
                        config = source.source_config
                        
                        # Check for placeholder values
                        has_placeholders = False
                        placeholder_keys = []
                        
                        for key, value in config.items():
                            if isinstance(value, str) and '${' in value:
                                has_placeholders = True
                                placeholder_keys.append(f"{key}: {value}")
                        
                        if has_placeholders:
                            print(f"      ❌ Has placeholders:")
                            for placeholder in placeholder_keys:
                                print(f"         {placeholder}")
                        else:
                            print(f"      ✅ No placeholders found")
                            # Show actual values (masked for secrets)
                            for key, value in config.items():
                                if key in ['tenant_id', 'client_id']:
                                    print(f"         {key}: {value}")
                                elif key in ['client_secret']:
                                    print(f"         {key}: {'SET' if value else 'NOT SET'}")
                
                else:
                    print(f"   ❌ KB not found: {kb_name}")
                    
            except Exception as e:
                print(f"   ❌ Error checking KB {kb_name}: {e}")
        
        # Also check regular knowledge bases if they exist
        print(f"\n📋 Regular Knowledge Bases:")
        print("-" * 30)
        
        try:
            # Check if there are regular KBs with the same name
            regular_kb = await multi_repo.repository.get_knowledge_base_by_name("InternalAudit-kb")
            if regular_kb:
                print(f"   ⚠️  Found regular KB with same name: {regular_kb.name} (ID: {regular_kb.id})")
                print(f"      This might be causing conflicts!")
            else:
                print(f"   ✅ No regular KB with same name found")
        except Exception as e:
            print(f"   ℹ️  Could not check regular KBs: {e}")
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(check_all_kbs())