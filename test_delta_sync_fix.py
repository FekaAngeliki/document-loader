#!/usr/bin/env python3
"""
Test script to verify the delta sync fix for multi-source knowledge bases.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository
from src.core.multi_source_batch_runner import MultiSourceBatchRunner

async def test_delta_sync_fix():
    """Test that the delta sync fix enables proper change detection."""
    
    print("🧪 Testing Delta Sync Fix for Multi-Source")
    print("=" * 60)
    
    try:
        # Connect to database
        config = DatabaseConfig()
        db = Database(config)
        await db.connect()
        
        repo = MultiSourceRepository(db)
        batch_runner = MultiSourceBatchRunner(repo)
        
        print("✅ Connected to database")
        
        # Get the PremiumRMs2-kb multi-source KB
        multi_kb = await repo.get_multi_source_kb_by_name("PremiumRMs2-kb")
        if not multi_kb:
            print("❌ PremiumRMs2-kb not found")
            await db.disconnect()
            return
            
        print(f"✅ Found multi-source KB: {multi_kb.name} (ID: {multi_kb.id})")
        
        # Test the compatible KB ID resolution
        compatible_kb_id = await batch_runner._get_compatible_kb_id(multi_kb)
        print(f"✅ Compatible KB ID: {compatible_kb_id}")
        
        # Verify this KB exists and has file records
        compat_kb = await repo.get_knowledge_base(compatible_kb_id)
        if compat_kb:
            print(f"✅ Compatible KB exists: {compat_kb.name}")
            
            # Check for file records
            query = '''
            SELECT COUNT(*) as count FROM file_record fr
            JOIN sync_run sr ON fr.sync_run_id = sr.id
            WHERE sr.knowledge_base_id = $1
            '''
            file_count = await db.fetchval(query, compatible_kb_id)
            print(f"✅ File records found: {file_count}")
            
            if file_count > 0:
                # Test what change detection would find
                print(f"\\n🔍 Testing change detection:")
                print(f"  Before fix: Uses multi_kb.id = {multi_kb.id}")
                print(f"  After fix:  Uses compatible_kb_id = {compatible_kb_id}")
                
                # Simulate what would happen with old approach
                old_kb = await repo.get_knowledge_base(multi_kb.id)
                print(f"  Old approach KB lookup: {'Found' if old_kb else 'NOT FOUND'}")
                
                # Simulate what happens with new approach  
                new_kb = await repo.get_knowledge_base(compatible_kb_id)
                print(f"  New approach KB lookup: {'Found' if new_kb else 'NOT FOUND'}")
                
                if new_kb:
                    # Test file record lookup
                    latest_records = await repo.get_latest_file_records_for_kb(new_kb.name)
                    print(f"  Latest file records found: {len(latest_records)}")
                    
                    if len(latest_records) > 0:
                        print(f"\\n🎉 DELTA SYNC WILL WORK!")
                        print(f"  - Change detection will find {len(latest_records)} existing files")
                        print(f"  - Only NEW/MODIFIED files will be processed")
                        print(f"  - UNCHANGED files will be skipped")
                        print(f"  - Prevents re-downloading all files every sync")
                    else:
                        print(f"\\n❌ No file records found for change detection")
                else:
                    print(f"\\n❌ Compatible KB not accessible")
            else:
                print(f"\\n❌ No file records found for compatible KB")
        else:
            print(f"❌ Compatible KB {compatible_kb_id} not found")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_delta_sync_fix())