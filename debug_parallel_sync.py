#!/usr/bin/env python3
"""
Debug script for parallel sync issues
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository
from src.core.multi_source_batch_runner import MultiSourceBatchRunner
from src.data.multi_source_models import SyncMode

async def debug_parallel_sync():
    """Debug parallel sync functionality."""
    
    print("🔧 Debugging Parallel Sync Issues")
    print("=" * 50)
    
    try:
        # Connect to database
        config = DatabaseConfig()
        db = Database(config)
        await db.connect()
        
        repo = MultiSourceRepository(db)
        batch_runner = MultiSourceBatchRunner(repo)
        
        print("✅ Connected to database")
        
        # Get multi-source KB
        multi_kb = await repo.get_multi_source_kb_by_name("PremiumRMs2-kb")
        if not multi_kb:
            print("❌ PremiumRMs2-kb not found")
            await db.disconnect()
            return
            
        print(f"✅ Found multi-source KB: {multi_kb.name}")
        print(f"📁 Sources: {len(multi_kb.sources)}")
        
        for i, source in enumerate(multi_kb.sources, 1):
            print(f"  {i}. {source.source_id} ({source.source_type})")
        
        # Test parallel mode specifically
        print(f"\n🧪 Testing Parallel Sync Components...")
        
        # Test 1: Check if asyncio works
        print("1. Testing asyncio.create_task...")
        try:
            async def dummy_task(n):
                await asyncio.sleep(0.1)
                return f"Task {n} completed"
            
            tasks = [asyncio.create_task(dummy_task(i)) for i in range(3)]
            results = await asyncio.gather(*tasks)
            print("   ✅ asyncio.create_task works")
            print(f"   Results: {results}")
        except Exception as e:
            print(f"   ❌ asyncio.create_task failed: {e}")
            
        # Test 2: Check if Rich Progress works
        print("2. Testing Rich Progress...")
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn
            from rich.console import Console
            
            console = Console()
            with Progress(SpinnerColumn(), TextColumn("Test"), console=console) as progress:
                task = progress.add_task("Testing...", total=10)
                for i in range(10):
                    await asyncio.sleep(0.01)
                    progress.update(task, advance=1)
            print("   ✅ Rich Progress works")
        except Exception as e:
            print(f"   ❌ Rich Progress failed: {e}")
        
        # Test 3: Check if we can create sources
        print("3. Testing source creation...")
        try:
            from src.core.factory import Factory
            factory = Factory(repo)
            
            # Test with first source
            if multi_kb.sources:
                source_def = multi_kb.sources[0]
                source = await factory.create_source(source_def.source_type, source_def.source_config)
                print(f"   ✅ Created source: {source_def.source_id}")
                
                # Test if source has delta sync
                if hasattr(source, '_delta_sync_manager'):
                    print(f"   ✅ Source has delta sync manager")
                else:
                    print(f"   ⚠️  Source missing delta sync manager")
                    
                await source.cleanup()
            else:
                print("   ⚠️  No sources found to test")
                
        except Exception as e:
            print(f"   ❌ Source creation failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Check if we can create RAG system
        print("4. Testing RAG system creation...")
        try:
            rag = await factory.create_rag(multi_kb.rag_type, multi_kb.rag_config)
            await rag.initialize()
            print(f"   ✅ Created RAG system: {multi_kb.rag_type}")
            await rag.cleanup()
        except Exception as e:
            print(f"   ❌ RAG system creation failed: {e}")
        
        # Test 5: Simulate parallel sync (dry run)
        print("5. Testing parallel sync simulation...")
        try:
            print(f"   📊 Sync mode: {SyncMode.PARALLEL}")
            print(f"   📁 Sources to sync: {len(multi_kb.sources)}")
            
            # Check if enum values work
            if SyncMode.PARALLEL == SyncMode.PARALLEL:
                print("   ✅ SyncMode enum works")
            else:
                print("   ❌ SyncMode enum issue")
                
        except Exception as e:
            print(f"   ❌ Parallel sync simulation failed: {e}")
        
        print(f"\n🔍 Common Parallel Sync Issues:")
        print(f"❓ **Event loop issues**: Check if running in Jupyter/IDE with existing loop")
        print(f"❓ **Resource limits**: Check file descriptors, memory limits")  
        print(f"❓ **Network timeouts**: SharePoint may throttle parallel requests")
        print(f"❓ **Database connections**: Check if connection pool is sufficient")
        print(f"❓ **Rich console conflicts**: Check if terminal supports Rich formatting")
        
        print(f"\n🛠️ Troubleshooting Steps:")
        print(f"1. Try sequential mode first: --sync-mode sequential")
        print(f"2. Check system resources: memory, file descriptors")
        print(f"3. Test with fewer sources: --sources 'Sharepoint_1'")
        print(f"4. Run with maximum logging: --verbose")
        print(f"5. Check for existing async event loops")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_parallel_sync())