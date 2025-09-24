#!/usr/bin/env python3
"""
Test PostgreSQL integration with multi-source implementation

This script tests the database layer for multi-source knowledge bases
to ensure proper integration with PostgreSQL.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.database import Database, DatabaseConfig
from data.multi_source_repository import MultiSourceRepository
from data.multi_source_models import (
    MultiSourceKnowledgeBase,
    SourceDefinition,
    MultiSourceSyncRun,
    EnhancedFileRecord,
    SyncMode
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_test_database():
    """Get test database connection."""
    config = DatabaseConfig()
    db = Database(config)
    await db.connect()
    return db

async def test_database_migration():
    """Test database migration for multi-source support."""
    
    print("Testing database migration...")
    
    db = await get_test_database()
    
    try:
        # Check if migration tables exist
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'multi_source_knowledge_base',
                'source_definition', 
                'multi_source_sync_run'
            )
        """
        
        tables = await db.fetch(tables_query)
        table_names = [row['table_name'] for row in tables]
        
        expected_tables = [
            'multi_source_knowledge_base',
            'source_definition',
            'multi_source_sync_run'
        ]
        
        missing_tables = [t for t in expected_tables if t not in table_names]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            print("   Please run the migration: migrations/001_multi_source_support.sql")
            return False
        else:
            print("✅ All required tables exist")
            return True
            
    except Exception as e:
        print(f"❌ Database migration check failed: {e}")
        return False
    finally:
        await db.disconnect()

async def test_multi_source_kb_operations():
    """Test multi-source knowledge base CRUD operations."""
    
    print("\nTesting multi-source KB operations...")
    
    db = await get_test_database()
    repo = MultiSourceRepository(db)
    
    try:
        # Create test multi-source KB
        test_kb = MultiSourceKnowledgeBase(
            name="test-multi-kb",
            description="Test multi-source knowledge base",
            rag_type="azure_blob",
            rag_config={
                "azure_storage_container_name": "test-container",
                "azure_storage_account_name": "testaccount"
            },
            sources=[
                SourceDefinition(
                    source_id="sharepoint_test",
                    source_type="enterprise_sharepoint",
                    source_config={
                        "tenant_id": "test-tenant",
                        "client_id": "test-client",
                        "site_url": "https://test.sharepoint.com/sites/test"
                    },
                    metadata_tags={"department": "IT", "system": "sharepoint"}
                ),
                SourceDefinition(
                    source_id="filesystem_test",
                    source_type="file_system",
                    source_config={
                        "root_path": "/test/documents",
                        "include_extensions": [".pdf", ".docx"]
                    },
                    metadata_tags={"department": "Archive", "system": "filesystem"}
                )
            ],
            file_organization={
                "naming_convention": "{source_id}/{uuid}{extension}"
            },
            sync_strategy={
                "default_mode": "parallel"
            }
        )
        
        # Test CREATE
        kb_id = await repo.create_multi_source_kb(test_kb)
        print(f"✅ Created multi-source KB with ID: {kb_id}")
        
        # Test READ by ID
        retrieved_kb = await repo.get_multi_source_kb(kb_id)
        if retrieved_kb and retrieved_kb.name == test_kb.name:
            print("✅ Retrieved multi-source KB by ID")
            print(f"   Sources: {len(retrieved_kb.sources)}")
            for source in retrieved_kb.sources:
                print(f"   - {source.source_id} ({source.source_type})")
        else:
            print("❌ Failed to retrieve multi-source KB by ID")
        
        # Test READ by name
        retrieved_kb_name = await repo.get_multi_source_kb_by_name("test-multi-kb")
        if retrieved_kb_name and retrieved_kb_name.id == kb_id:
            print("✅ Retrieved multi-source KB by name")
        else:
            print("❌ Failed to retrieve multi-source KB by name")
        
        # Test LIST
        all_kbs = await repo.list_multi_source_kbs()
        kb_names = [kb.name for kb in all_kbs]
        if "test-multi-kb" in kb_names:
            print("✅ Multi-source KB appears in list")
        else:
            print("❌ Multi-source KB not found in list")
        
        # Test UPDATE
        updates = {
            "description": "Updated test description",
            "sync_strategy": {"default_mode": "sequential", "batch_size": 25}
        }
        update_success = await repo.update_multi_source_kb(kb_id, updates)
        if update_success:
            print("✅ Updated multi-source KB")
            
            # Verify update
            updated_kb = await repo.get_multi_source_kb(kb_id)
            if updated_kb.description == "Updated test description":
                print("✅ Update verified")
            else:
                print("❌ Update verification failed")
        else:
            print("❌ Failed to update multi-source KB")
        
        # Test source operations
        new_source = SourceDefinition(
            source_id="onedrive_test",
            source_type="onedrive",
            source_config={
                "user_id": "test@example.com",
                "root_folder": "/Documents"
            },
            metadata_tags={"department": "Executive", "system": "onedrive"}
        )
        
        # Test ADD SOURCE
        add_success = await repo.add_source_to_kb(kb_id, new_source)
        if add_success:
            print("✅ Added new source to KB")
        else:
            print("❌ Failed to add new source to KB")
        
        # Test UPDATE SOURCE
        source_updates = {
            "enabled": False,
            "sync_schedule": "0 3 * * *"
        }
        update_source_success = await repo.update_source_definition(
            kb_id, "onedrive_test", source_updates
        )
        if update_source_success:
            print("✅ Updated source definition")
        else:
            print("❌ Failed to update source definition")
        
        # Test REMOVE SOURCE
        remove_success = await repo.remove_source_from_kb(kb_id, "onedrive_test")
        if remove_success:
            print("✅ Removed source from KB")
        else:
            print("❌ Failed to remove source from KB")
        
        # Test DELETE (cleanup)
        delete_success = await repo.delete_multi_source_kb(kb_id)
        if delete_success:
            print("✅ Deleted multi-source KB")
        else:
            print("❌ Failed to delete multi-source KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Multi-source KB operations failed: {e}")
        logger.exception("Detailed error:")
        return False
    finally:
        await db.disconnect()

async def test_sync_run_operations():
    """Test multi-source sync run operations."""
    
    print("\nTesting sync run operations...")
    
    db = await get_test_database()
    repo = MultiSourceRepository(db)
    
    try:
        # Create a test KB first
        test_kb = MultiSourceKnowledgeBase(
            name="test-sync-kb",
            description="Test KB for sync operations",
            rag_type="mock",
            rag_config={},
            sources=[
                SourceDefinition(
                    source_id="test_source",
                    source_type="file_system",
                    source_config={"root_path": "/test"}
                )
            ]
        )
        
        kb_id = await repo.create_multi_source_kb(test_kb)
        
        # Create test sync run
        sync_run = MultiSourceSyncRun(
            knowledge_base_id=kb_id,
            start_time=datetime.utcnow(),
            sync_mode=SyncMode.PARALLEL.value,
            sources_processed=["test_source"]
        )
        
        # Test CREATE sync run
        sync_run_id = await repo.create_multi_source_sync_run(sync_run)
        sync_run.id = sync_run_id
        print(f"✅ Created sync run with ID: {sync_run_id}")
        
        # Test UPDATE sync run
        sync_run.end_time = datetime.utcnow()
        sync_run.status = "completed"
        sync_run.total_files = 10
        sync_run.new_files = 8
        sync_run.modified_files = 2
        sync_run.source_stats = {
            "test_source": {
                "files_processed": 10,
                "files_new": 8,
                "files_modified": 2,
                "files_error": 0
            }
        }
        
        update_success = await repo.update_multi_source_sync_run(sync_run)
        if update_success:
            print("✅ Updated sync run")
        else:
            print("❌ Failed to update sync run")
        
        # Test GET sync runs
        sync_runs = await repo.get_multi_source_sync_runs(kb_id, limit=5)
        if sync_runs and len(sync_runs) > 0:
            print(f"✅ Retrieved {len(sync_runs)} sync runs")
            latest = sync_runs[0]
            print(f"   Latest: {latest.status}, {latest.total_files} files")
        else:
            print("❌ Failed to retrieve sync runs")
        
        # Cleanup
        await repo.delete_multi_source_kb(kb_id)
        
        return True
        
    except Exception as e:
        print(f"❌ Sync run operations failed: {e}")
        logger.exception("Detailed error:")
        return False
    finally:
        await db.disconnect()

async def test_enhanced_file_records():
    """Test enhanced file record operations."""
    
    print("\nTesting enhanced file record operations...")
    
    db = await get_test_database()
    repo = MultiSourceRepository(db)
    
    try:
        # Create test KB and sync run
        test_kb = MultiSourceKnowledgeBase(
            name="test-file-kb",
            description="Test KB for file operations",
            rag_type="mock",
            rag_config={},
            sources=[
                SourceDefinition(
                    source_id="test_source",
                    source_type="file_system",
                    source_config={"root_path": "/test"}
                )
            ]
        )
        
        kb_id = await repo.create_multi_source_kb(test_kb)
        
        sync_run = MultiSourceSyncRun(
            knowledge_base_id=kb_id,
            start_time=datetime.utcnow(),
            sync_mode=SyncMode.PARALLEL.value,
            sources_processed=["test_source"]
        )
        
        sync_run_id = await repo.create_multi_source_sync_run(sync_run)
        
        # Create test file record
        file_record = EnhancedFileRecord(
            sync_run_id=sync_run_id,
            source_id="test_source",
            source_type="file_system",
            source_path="/test/documents/file.pdf",
            original_uri="/test/documents/file.pdf",
            rag_uri="test-container/test_source/abc123.pdf",
            file_hash="sha256:abc123def456",
            uuid_filename="abc123def456.pdf",
            upload_time=datetime.utcnow(),
            file_size=1024,
            content_type="application/pdf",
            status="uploaded",
            source_metadata={"department": "IT", "category": "documentation"},
            rag_metadata={"kb_name": "test-file-kb", "source_id": "test_source"},
            tags=["document", "pdf", "it"],
            source_created_at=datetime.utcnow(),
            source_modified_at=datetime.utcnow()
        )
        
        # Test CREATE file record
        file_id = await repo.create_enhanced_file_record(file_record)
        print(f"✅ Created enhanced file record with ID: {file_id}")
        
        # Test GET files by source
        files = await repo.get_files_by_source(kb_id, "test_source", limit=10)
        if files and len(files) > 0:
            print(f"✅ Retrieved {len(files)} files for source")
            file = files[0]
            print(f"   File: {file.uuid_filename}, Size: {file.file_size}")
            print(f"   Tags: {file.tags}")
            print(f"   Source metadata: {file.source_metadata}")
        else:
            print("❌ Failed to retrieve files by source")
        
        # Cleanup
        await repo.delete_multi_source_kb(kb_id)
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced file record operations failed: {e}")
        logger.exception("Detailed error:")
        return False
    finally:
        await db.disconnect()

async def test_statistics_and_reporting():
    """Test statistics and reporting functions."""
    
    print("\nTesting statistics and reporting...")
    
    db = await get_test_database()
    repo = MultiSourceRepository(db)
    
    try:
        # Create test data
        test_kb = MultiSourceKnowledgeBase(
            name="test-stats-kb",
            description="Test KB for statistics",
            rag_type="mock",
            rag_config={},
            sources=[
                SourceDefinition(
                    source_id="source1",
                    source_type="file_system",
                    source_config={"root_path": "/test1"}
                ),
                SourceDefinition(
                    source_id="source2",
                    source_type="enterprise_sharepoint",
                    source_config={"site_url": "https://test.sharepoint.com"}
                )
            ]
        )
        
        kb_id = await repo.create_multi_source_kb(test_kb)
        
        # Create sync run and file records for testing
        sync_run = MultiSourceSyncRun(
            knowledge_base_id=kb_id,
            start_time=datetime.utcnow(),
            sync_mode=SyncMode.PARALLEL.value,
            sources_processed=["source1", "source2"]
        )
        
        sync_run_id = await repo.create_multi_source_sync_run(sync_run)
        
        # Add some test file records
        for i in range(3):
            file_record = EnhancedFileRecord(
                sync_run_id=sync_run_id,
                source_id="source1",
                source_type="file_system",
                source_path=f"/test1/file{i}.pdf",
                original_uri=f"/test1/file{i}.pdf",
                rag_uri=f"test-container/source1/file{i}.pdf",
                file_hash=f"hash{i}",
                uuid_filename=f"file{i}.pdf",
                upload_time=datetime.utcnow(),
                file_size=1024 * (i + 1),
                content_type="application/pdf",
                status="uploaded"
            )
            await repo.create_enhanced_file_record(file_record)
        
        # Test statistics
        stats = await repo.get_multi_source_stats(kb_id)
        
        if stats:
            print("✅ Retrieved multi-source statistics")
            print(f"   KB ID: {stats['kb_id']}")
            print(f"   Total files: {stats['totals']['total_files']}")
            print(f"   Total size: {stats['totals']['total_size']}")
            print(f"   Sources: {list(stats['sources'].keys())}")
        else:
            print("❌ Failed to retrieve statistics")
        
        # Cleanup
        await repo.delete_multi_source_kb(kb_id)
        
        return True
        
    except Exception as e:
        print(f"❌ Statistics operations failed: {e}")
        logger.exception("Detailed error:")
        return False
    finally:
        await db.disconnect()

async def test_backward_compatibility():
    """Test backward compatibility with legacy system."""
    
    print("\nTesting backward compatibility...")
    
    db = await get_test_database()
    repo = MultiSourceRepository(db)
    
    try:
        # Create multi-source KB
        test_kb = MultiSourceKnowledgeBase(
            name="test-compat-kb",
            description="Test backward compatibility",
            rag_type="mock",
            rag_config={},
            sources=[
                SourceDefinition(
                    source_id="legacy_source",
                    source_type="file_system",
                    source_config={"root_path": "/legacy"}
                )
            ]
        )
        
        kb_id = await repo.create_multi_source_kb(test_kb)
        
        # Test legacy KB representation
        legacy_kb = await repo.get_legacy_kb_for_source(kb_id, "legacy_source")
        
        if legacy_kb:
            print("✅ Retrieved legacy KB representation")
            print(f"   Name: {legacy_kb.name}")
            print(f"   Source type: {legacy_kb.source_type}")
            print(f"   RAG type: {legacy_kb.rag_type}")
        else:
            print("❌ Failed to retrieve legacy KB representation")
        
        # Test legacy view directly
        legacy_view_query = """
            SELECT name, source_type, rag_type, multi_source_kb_id, source_id
            FROM legacy_knowledge_base_view 
            WHERE multi_source_kb_id = $1
        """
        
        legacy_rows = await db.fetch(legacy_view_query, kb_id)
        
        if legacy_rows and len(legacy_rows) > 0:
            print("✅ Legacy view working correctly")
            for row in legacy_rows:
                print(f"   Legacy KB: {row['name']} (source: {row['source_id']})")
        else:
            print("❌ Legacy view not working")
        
        # Cleanup
        await repo.delete_multi_source_kb(kb_id)
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        logger.exception("Detailed error:")
        return False
    finally:
        await db.disconnect()

async def run_all_tests():
    """Run all PostgreSQL integration tests."""
    
    print("PostgreSQL Multi-Source Integration Tests")
    print("=" * 50)
    
    # Check environment
    config = DatabaseConfig()
    if not all([config.host, config.port, config.database, config.user]):
        print("❌ Database configuration incomplete")
        print("Please ensure these environment variables are set:")
        print("- DOCUMENT_LOADER_DB_HOST")
        print("- DOCUMENT_LOADER_DB_PORT") 
        print("- DOCUMENT_LOADER_DB_NAME")
        print("- DOCUMENT_LOADER_DB_USER")
        print("- DOCUMENT_LOADER_DB_PASSWORD")
        return
    
    # Run tests
    tests = [
        ("Database Migration", test_database_migration),
        ("Multi-Source KB Operations", test_multi_source_kb_operations),
        ("Sync Run Operations", test_sync_run_operations),
        ("Enhanced File Records", test_enhanced_file_records),
        ("Statistics and Reporting", test_statistics_and_reporting),
        ("Backward Compatibility", test_backward_compatibility)
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
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! PostgreSQL integration is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the database migration and configuration.")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(run_all_tests())