#!/usr/bin/env python3
"""
Debug script to check multi-source sync KB lookup issue.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository
from src.data.multi_source_models import create_multi_source_kb_from_config


async def debug_sync_lookup():
    """Debug why multi-source sync can't find the KB."""
    
    print("🔍 Debug Multi-Source Sync KB Lookup")
    print("=" * 50)
    
    # Load config file (same as sync command does)
    config_file = "configs/internal-audit-kb-config.json"
    config_path = Path(config_file)
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_file}")
        return
    
    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return
    
    print(f"📄 Config file loaded: {config_file}")
    
    # Parse config (same as sync command does)
    try:
        multi_kb = create_multi_source_kb_from_config(config)
        print(f"📋 Parsed KB name: '{multi_kb.name}'")
        print(f"📋 KB description: '{multi_kb.description}'")
        print(f"📋 RAG type: '{multi_kb.rag_type}'")
        print(f"📋 Sources: {len(multi_kb.sources)}")
        for source in multi_kb.sources:
            print(f"   - {source.source_id} ({source.source_type})")
    except Exception as e:
        print(f"❌ Failed to parse config: {e}")
        return
    
    # Connect to database (same as sync command does)
    config_db = DatabaseConfig()
    db = Database(config_db)
    await db.connect()
    
    try:
        multi_repo = MultiSourceRepository(db)
        
        # Check lookup (same as sync command does)
        print(f"\n🔍 Looking up KB: '{multi_kb.name}'")
        existing_kb = await multi_repo.get_multi_source_kb_by_name(multi_kb.name)
        
        if existing_kb:
            print(f"✅ Found KB: {existing_kb.name} (ID: {existing_kb.id})")
            print(f"   RAG type: {existing_kb.rag_type}")
            print(f"   Sources: {len(existing_kb.sources)}")
        else:
            print(f"❌ KB not found in multi_source_knowledge_base table")
            
            # Check what's actually in the table
            print(f"\n📊 All multi-source KBs in database:")
            all_kbs = await multi_repo.list_multi_source_kbs()
            for kb in all_kbs:
                print(f"   - '{kb.name}' (ID: {kb.id})")
                
            # Check for exact match issues
            print(f"\n🔍 Checking for potential name mismatches:")
            for kb in all_kbs:
                if multi_kb.name in kb.name or kb.name in multi_kb.name:
                    print(f"   Similar: '{kb.name}' vs '{multi_kb.name}'")
                    print(f"   Length: {len(kb.name)} vs {len(multi_kb.name)}")
                    print(f"   Bytes: {repr(kb.name)} vs {repr(multi_kb.name)}")
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(debug_sync_lookup())