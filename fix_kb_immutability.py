#!/usr/bin/env python3
"""
Script to fix knowledge base immutability issue.

This script helps delete a knowledge base with incorrect RAG type
so you can recreate it with the correct configuration.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.database import Database, DatabaseConfig
from src.data.repository import Repository
from src.data.multi_source_repository import MultiSourceRepository


async def fix_kb_immutability():
    """Fix the InternalAudit-kb knowledge base by removing incorrect RAG type."""
    
    print("🔧 Knowledge Base Immutability Fix")
    print("=" * 50)
    
    config = DatabaseConfig()
    db = Database(config)
    await db.connect()
    
    try:
        repository = Repository(db)
        multi_repo = MultiSourceRepository(db)
        
        # Check current KB state
        print("\n📊 Current Knowledge Base Status:")
        
        # Check multi-source KB
        multi_kb = await multi_repo.get_multi_source_kb_by_name("InternalAudit-kb")
        if multi_kb:
            print(f"Multi-source KB: {multi_kb.name}")
            print(f"  RAG Type: {multi_kb.rag_type}")
            print(f"  Sources: {len(multi_kb.sources)}")
            
            if multi_kb.rag_type == "Ask":
                print(f"  ❌ Invalid RAG type detected: '{multi_kb.rag_type}'")
                print(f"  ✅ Should be: 'mock'")
                
                print("\n🗑️  Deleting knowledge base with incorrect RAG type...")
                
                # Delete the multi-source KB
                await multi_repo.delete_multi_source_kb(multi_kb.id)
                print(f"  ✅ Deleted multi-source KB: {multi_kb.name}")
                
                # Also check for individual compatibility KBs
                compat_kb_name = f"{multi_kb.name}_Sharepoint_1"
                compat_kb = await repository.get_knowledge_base_by_name(compat_kb_name)
                if compat_kb:
                    # Delete individual KB too
                    await repository.delete_knowledge_base(compat_kb.id)
                    print(f"  ✅ Deleted compatibility KB: {compat_kb_name}")
                
                print("\n✨ Knowledge base cleaned up successfully!")
                print("\n📝 Next steps:")
                print("  1. Run: document-loader multi-source create-multi-kb --config-file configs/internal-audit-kb-config.json")
                print("  2. This will create the KB with correct RAG type: 'mock'")
                print("  3. Then you can sync: document-loader multi-source sync-multi-kb --config-file configs/internal-audit-kb-config.json")
                
            else:
                print(f"  ✅ RAG type is correct: '{multi_kb.rag_type}'")
                print("  No action needed.")
        else:
            print("Multi-source KB 'InternalAudit-kb' not found")
            
        # Check individual KB too
        individual_kb = await repository.get_knowledge_base_by_name("InternalAudit-kb_Sharepoint_1")
        if individual_kb:
            print(f"\nIndividual KB: {individual_kb.name}")
            print(f"  RAG Type: {individual_kb.rag_type}")
            
            if individual_kb.rag_type == "Ask":
                print(f"  ❌ Invalid RAG type detected: '{individual_kb.rag_type}'")
                await repository.delete_knowledge_base(individual_kb.id)
                print(f"  ✅ Deleted individual KB: {individual_kb.name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(fix_kb_immutability())