#!/usr/bin/env python3
"""
Test script to verify the sync run creation fix.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.data.multi_source_models import MultiSourceSyncRun, MultiSourceKnowledgeBase, SyncMode

async def test_sync_run_creation():
    """Test that MultiSourceSyncRun can be created without initialization errors."""
    
    print("🧪 Testing Sync Run Creation Fix")
    print("=" * 50)
    
    try:
        # Test basic MultiSourceSyncRun creation
        sync_run = MultiSourceSyncRun(
            id=1,
            knowledge_base_id=22,
            sync_mode="sequential",
            sources_processed=["test_source"],
            status="running",
            source_stats={}
        )
        
        print("✅ Basic MultiSourceSyncRun creation: SUCCESS")
        
        # Test adding compatible KB ID as attribute (like the fix)
        sync_run._compatible_kb_id = 31
        
        print("✅ Adding _compatible_kb_id attribute: SUCCESS")
        print(f"   Original KB ID: {sync_run.knowledge_base_id}")
        print(f"   Compatible KB ID: {sync_run._compatible_kb_id}")
        
        # Test accessing the attribute with getattr (like in finalize method)
        compatible_id = getattr(sync_run, '_compatible_kb_id', sync_run.knowledge_base_id)
        print(f"✅ Accessing compatible KB ID with getattr: {compatible_id}")
        
        # Test that we can still access all normal attributes
        print(f"✅ Sync run ID: {sync_run.id}")
        print(f"✅ Sync mode: {sync_run.sync_mode}")
        print(f"✅ Status: {sync_run.status}")
        
        print("\n🎉 All tests passed!")
        print("The sync run creation should now work without '__init__() got an unexpected keyword argument' error.")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sync_run_creation())
    if success:
        print("\n✅ Ready to test actual multi-source sync!")
    else:
        print("\n❌ Fix needs more work.")