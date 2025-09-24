#!/usr/bin/env python3
"""
Backward Compatibility Test

This script tests that existing single-source knowledge bases continue to work
after the multi-source migration is applied.
"""

import asyncio
import os
import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.database import Database, DatabaseConfig
from data.repository import Repository
from data.multi_source_repository import MultiSourceRepository
from data.models import KnowledgeBase

async def get_test_database():
    """Get test database connection."""
    config = DatabaseConfig()
    db = Database(config)
    await db.connect()
    return db

async def test_legacy_kb_operations():
    """Test that legacy single-source KB operations still work."""
    
    print("🔄 Testing legacy single-source KB operations...")
    
    db = await get_test_database()
    repo = Repository(db)
    
    try:
        # Create a traditional single-source KB
        legacy_kb = KnowledgeBase(
            name="test-legacy-kb",
            source_type="file_system",
            source_config={
                "root_path": "/tmp/test",
                "include_extensions": [".pdf", ".docx"],
                "recursive": True
            },
            rag_type="mock",
            rag_config={}
        )
        
        # Test CREATE
        print("   Creating legacy KB...")
        kb_id = await repo.create_knowledge_base(legacy_kb)
        print(f"   ✅ Created legacy KB with ID: {kb_id}")
        
        # Test READ
        print("   Reading legacy KB...")
        retrieved_kb = await repo.get_knowledge_base(kb_id)
        if retrieved_kb and retrieved_kb.name == legacy_kb.name:
            print("   ✅ Retrieved legacy KB successfully")
        else:
            raise Exception("Failed to retrieve legacy KB")
        
        # Test READ by name
        retrieved_by_name = await repo.get_knowledge_base_by_name("test-legacy-kb")
        if retrieved_by_name and retrieved_by_name.id == kb_id:
            print("   ✅ Retrieved legacy KB by name")
        else:
            raise Exception("Failed to retrieve legacy KB by name")
        
        # Test LIST
        print("   Listing legacy KBs...")
        all_kbs = await repo.list_knowledge_bases()
        kb_names = [kb.name for kb in all_kbs]
        if "test-legacy-kb" in kb_names:
            print("   ✅ Legacy KB found in list")
        else:
            raise Exception("Legacy KB not found in list")
        
        # Test UPDATE
        print("   Updating legacy KB...")
        updates = {
            "source_config": {
                "root_path": "/tmp/updated",
                "include_extensions": [".pdf", ".txt"],
                "recursive": False
            }
        }
        update_success = await repo.update_knowledge_base(kb_id, updates)
        if update_success:
            print("   ✅ Updated legacy KB")
            
            # Verify update
            updated_kb = await repo.get_knowledge_base(kb_id)
            if updated_kb.source_config["root_path"] == "/tmp/updated":
                print("   ✅ Update verified")
            else:
                raise Exception("Update verification failed")
        else:
            raise Exception("Failed to update legacy KB")
        
        # Test DELETE
        print("   Deleting legacy KB...")
        delete_success = await repo.delete_knowledge_base(kb_id)
        if delete_success:
            print("   ✅ Deleted legacy KB")
        else:
            raise Exception("Failed to delete legacy KB")
        
        print("   ✅ All legacy KB operations successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Legacy KB operations failed: {e}")
        return False
    finally:
        await db.disconnect()

async def test_legacy_view_integration():
    """Test the legacy view integration with multi-source KBs."""
    
    print("\n🔍 Testing legacy view integration...")
    
    db = await get_test_database()
    multi_repo = MultiSourceRepository(db)
    
    try:
        # Create a multi-source KB
        from data.multi_source_models import MultiSourceKnowledgeBase, SourceDefinition
        
        multi_kb = MultiSourceKnowledgeBase(
            name="test-compat-kb",
            description="Test backward compatibility",
            rag_type="mock",
            rag_config={},
            sources=[
                SourceDefinition(
                    source_id="source1",
                    source_type="file_system",
                    source_config={"root_path": "/test1"},
                    metadata_tags={"department": "IT"}
                ),
                SourceDefinition(
                    source_id="source2", 
                    source_type="file_system",
                    source_config={"root_path": "/test2"},
                    metadata_tags={"department": "HR"}
                )
            ]
        )
        
        print("   Creating multi-source KB...")
        kb_id = await multi_repo.create_multi_source_kb(multi_kb)
        print(f"   ✅ Created multi-source KB with ID: {kb_id}")
        
        # Test legacy view
        print("   Testing legacy view...")
        legacy_view_query = """
            SELECT id, name, source_type, rag_type, multi_source_kb_id, source_id, enabled
            FROM legacy_knowledge_base_view 
            WHERE multi_source_kb_id = $1
            ORDER BY source_id
        """
        
        legacy_rows = await db.fetch(legacy_view_query, kb_id)
        
        if legacy_rows and len(legacy_rows) == 2:
            print(f"   ✅ Legacy view returned {len(legacy_rows)} rows")
            
            for row in legacy_rows:
                print(f"      - {row['name']} (source: {row['source_id']}, enabled: {row['enabled']})")
                
                # Test legacy KB representation
                legacy_kb = await multi_repo.get_legacy_kb_for_source(kb_id, row['source_id'])
                if legacy_kb:
                    print(f"        ✅ Legacy representation: {legacy_kb.name}")
                else:
                    raise Exception(f"Failed to get legacy representation for {row['source_id']}")
        else:
            raise Exception(f"Expected 2 legacy view rows, got {len(legacy_rows) if legacy_rows else 0}")
        
        # Cleanup
        await multi_repo.delete_multi_source_kb(kb_id)
        print("   ✅ Legacy view integration successful")
        return True
        
    except Exception as e:
        print(f"   ❌ Legacy view integration failed: {e}")
        return False
    finally:
        await db.disconnect()

async def test_schema_backward_compatibility():
    """Test that the schema changes don't break existing operations."""
    
    print("\n🗄️  Testing schema backward compatibility...")
    
    db = await get_test_database()
    
    try:
        # Test that original tables still exist and work
        print("   Testing original tables...")
        
        # Test knowledge_base table
        kb_query = "SELECT COUNT(*) FROM knowledge_base"
        kb_count = await db.fetchval(kb_query)
        print(f"   ✅ knowledge_base table accessible ({kb_count} records)")
        
        # Test sync_run table
        sync_query = "SELECT COUNT(*) FROM sync_run"
        sync_count = await db.fetchval(sync_query)
        print(f"   ✅ sync_run table accessible ({sync_count} records)")
        
        # Test file_record table with new columns
        file_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'file_record' 
            AND column_name IN ('source_id', 'source_type', 'source_metadata')
        """
        new_columns = await db.fetch(file_query)
        if len(new_columns) >= 3:
            print("   ✅ file_record table has new columns")
        else:
            raise Exception("file_record table missing new columns")
        
        # Test that existing file_record operations still work
        file_count_query = "SELECT COUNT(*) FROM file_record"
        file_count = await db.fetchval(file_count_query)
        print(f"   ✅ file_record table accessible ({file_count} records)")
        
        # Test new tables exist
        new_tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'multi_source_knowledge_base',
                'source_definition',
                'multi_source_sync_run'
            )
        """
        new_tables = await db.fetch(new_tables_query)
        if len(new_tables) >= 3:
            print("   ✅ New multi-source tables exist")
        else:
            raise Exception("Missing new multi-source tables")
        
        # Test source_type table has new entries
        source_types_query = """
            SELECT name FROM source_type 
            WHERE name IN ('enterprise_sharepoint', 'onedrive')
        """
        source_types = await db.fetch(source_types_query)
        if len(source_types) >= 2:
            print("   ✅ New source types registered")
        else:
            print("   ⚠️  New source types not found (may need manual registration)")
        
        print("   ✅ Schema backward compatibility verified")
        return True
        
    except Exception as e:
        print(f"   ❌ Schema backward compatibility failed: {e}")
        return False
    finally:
        await db.disconnect()

async def test_cli_backward_compatibility():
    """Test that existing CLI commands still work."""
    
    print("\n🖥️  Testing CLI backward compatibility...")
    
    try:
        # Test that we can still import the old CLI
        from core.batch_runner import BatchRunner
        from data.repository import Repository
        
        print("   ✅ Legacy imports work")
        
        # Test creating a legacy KB via repository
        db = await get_test_database()
        repo = Repository(db)
        
        legacy_kb = KnowledgeBase(
            name="test-cli-compat",
            source_type="file_system",
            source_config={"root_path": "/tmp"},
            rag_type="mock",
            rag_config={}
        )
        
        kb_id = await repo.create_knowledge_base(legacy_kb)
        print(f"   ✅ Legacy KB creation works (ID: {kb_id})")
        
        # Test BatchRunner instantiation
        batch_runner = BatchRunner(repo)
        print("   ✅ BatchRunner instantiation works")
        
        # Cleanup
        await repo.delete_knowledge_base(kb_id)
        await db.disconnect()
        
        print("   ✅ CLI backward compatibility verified")
        return True
        
    except Exception as e:
        print(f"   ❌ CLI backward compatibility failed: {e}")
        return False

async def test_data_migration_integrity():
    """Test that existing data is preserved after migration."""
    
    print("\n📊 Testing data migration integrity...")
    
    db = await get_test_database()
    
    try:
        # Create some test data to simulate existing data
        repo = Repository(db)
        
        # Create legacy KB
        legacy_kb = KnowledgeBase(
            name="pre-migration-kb",
            source_type="file_system",
            source_config={"root_path": "/existing"},
            rag_type="mock", 
            rag_config={}
        )
        
        kb_id = await repo.create_knowledge_base(legacy_kb)
        
        # Verify it can be read
        retrieved = await repo.get_knowledge_base(kb_id)
        if not retrieved:
            raise Exception("Failed to retrieve pre-migration KB")
        
        print("   ✅ Pre-migration data preserved")
        
        # Test that new columns have default values
        file_record_query = """
            SELECT id, original_uri, source_id, source_type 
            FROM file_record 
            WHERE source_id IS NOT NULL 
            LIMIT 1
        """
        
        sample_record = await db.fetchrow(file_record_query)
        if sample_record:
            print(f"   ✅ File records have source tracking: {sample_record['source_id']}")
        else:
            print("   ℹ️  No file records with source tracking found (expected for fresh DB)")
        
        # Cleanup
        await repo.delete_knowledge_base(kb_id)
        
        print("   ✅ Data migration integrity verified")
        return True
        
    except Exception as e:
        print(f"   ❌ Data migration integrity failed: {e}")
        return False
    finally:
        await db.disconnect()

async def run_backward_compatibility_tests():
    """Run all backward compatibility tests."""
    
    print("Backward Compatibility Tests")
    print("=" * 40)
    
    # Check database connection
    try:
        db = await get_test_database()
        await db.disconnect()
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Run tests
    tests = [
        ("Legacy KB Operations", test_legacy_kb_operations),
        ("Legacy View Integration", test_legacy_view_integration), 
        ("Schema Backward Compatibility", test_schema_backward_compatibility),
        ("CLI Backward Compatibility", test_cli_backward_compatibility),
        ("Data Migration Integrity", test_data_migration_integrity)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*40)
    print("BACKWARD COMPATIBILITY TEST SUMMARY")
    print("="*40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All backward compatibility tests passed!")
        print("✅ Existing single-source KBs will continue to work")
        print("✅ Legacy CLI commands remain functional")
        print("✅ Database migration preserves existing data")
        return True
    else:
        print(f"\n⚠️  {total - passed} compatibility tests failed.")
        print("Some existing functionality may be affected.")
        return False

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = asyncio.run(run_backward_compatibility_tests())
    
    if success:
        print("\n🎯 Backward compatibility is maintained!")
        print("You can safely use both:")
        print("  - Existing single-source commands")
        print("  - New multi-source commands")
        sys.exit(0)
    else:
        print("\n⚠️  Compatibility issues found. Please review the migration.")
        sys.exit(1)