#!/usr/bin/env python
"""
Comprehensive test for file restore functionality.

This script simulates:
1. Creating a knowledge base
2. Adding files  
3. Running initial sync
4. Deleting files
5. Running sync to mark as deleted
6. Restoring files
7. Running sync to detect restored files
8. Verifying database state
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the components directly
from src.cli.knowledge_base_manager import KnowledgeBaseManager
from src.core.batch_runner import BatchRunner
from src.core.factory import Factory
from src.data.database import Database

async def setup_test_knowledge_base(temp_dir: Path):
    """Create a test knowledge base."""
    kb_name = "test-restore-kb"
    
    # Configuration for a simple file system source
    config = {
        "source": {
            "type": "file_system",
            "base_path": str(temp_dir),
            "include_patterns": ["**/*.txt", "**/*.md"],
            "exclude_patterns": ["**/.*", "**/__pycache__/**"],
            "recursive": True
        },
        "rag": {
            "type": "file_system_storage",
            "root_path": str(temp_dir / "storage"),
            "kb_name": kb_name
        }
    }
    
    # Create the knowledge base
    db = await Database.create()
    kb_manager = KnowledgeBaseManager(db)
    
    try:
        # Check if KB already exists and delete it
        existing_kb = await kb_manager.get_knowledge_base(kb_name)
        if existing_kb:
            logger.info(f"Deleting existing KB: {kb_name}")
            await kb_manager.delete_knowledge_base(kb_name)
        
        # Create new KB
        logger.info(f"Creating KB: {kb_name}")
        await kb_manager.create_knowledge_base(kb_name, config)
        
        return kb_name
    finally:
        await db.close()

async def run_sync(kb_name: str):
    """Run a sync operation."""
    db = await Database.create()
    factory = Factory(db)
    
    try:
        batch_runner = BatchRunner(db, factory)
        result = await batch_runner.sync(kb_name)
        logger.info(f"Sync result: {result}")
        return result
    finally:
        await db.close()

async def check_file_status(kb_name: str, file_name: str):
    """Check the status of a file in the database."""
    db = await Database.create()
    
    try:
        # Get the latest file record
        query = """
            SELECT fr.* 
            FROM file_record fr
            JOIN sync_run sr ON fr.sync_run_id = sr.sync_run_id
            JOIN knowledge_base kb ON sr.kb_id = kb.kb_id
            WHERE kb.kb_name = $1 
            AND fr.original_uri LIKE $2
            ORDER BY fr.created_at DESC
            LIMIT 1
        """
        
        search_pattern = f'%{file_name}'
        result = await db._execute(query, kb_name, search_pattern)
        
        if result:
            row = result[0]
            return {
                'file_record_id': row['file_record_id'],
                'original_uri': row['original_uri'],
                'rag_uri': row['rag_uri'],
                'status': row['status'],
                'created_at': row['created_at']
            }
        return None
    finally:
        await db.close()

async def main():
    """Run the comprehensive restore test."""
    logger.info("Starting comprehensive restore test")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Step 1: Setup KB and create initial files
        logger.info("Step 1: Setting up knowledge base")
        kb_name = await setup_test_knowledge_base(temp_path)
        
        # Create test files
        test_file = temp_path / "test_document.txt"
        test_file.write_text("This is a test document for restoration")
        
        test_file2 = temp_path / "another_document.md"
        test_file2.write_text("# Another Document\\n\\nThis will also be deleted and restored")
        
        # Step 2: Initial sync
        logger.info("Step 2: Running initial sync")
        await run_sync(kb_name)
        
        # Check initial status
        status1 = await check_file_status(kb_name, "test_document.txt")
        status2 = await check_file_status(kb_name, "another_document.md")
        
        logger.info(f"Initial status - test_document.txt: {status1}")
        logger.info(f"Initial status - another_document.md: {status2}")
        
        # Step 3: Delete files
        logger.info("Step 3: Deleting files")
        test_file.unlink()
        test_file2.unlink()
        
        # Step 4: Sync to mark as deleted
        logger.info("Step 4: Running sync to mark as deleted")
        await run_sync(kb_name)
        
        # Check deleted status
        status1_deleted = await check_file_status(kb_name, "test_document.txt")
        status2_deleted = await check_file_status(kb_name, "another_document.md")
        
        logger.info(f"Deleted status - test_document.txt: {status1_deleted}")
        logger.info(f"Deleted status - another_document.md: {status2_deleted}")
        
        # Step 5: Restore files
        logger.info("Step 5: Restoring files")
        test_file.write_text("This is a test document for restoration")
        test_file2.write_text("# Another Document\\n\\nThis will also be deleted and restored")
        
        # Step 6: Sync to detect restored files
        logger.info("Step 6: Running sync to detect restored files")
        await run_sync(kb_name)
        
        # Check restored status
        status1_restored = await check_file_status(kb_name, "test_document.txt")
        status2_restored = await check_file_status(kb_name, "another_document.md")
        
        logger.info(f"Restored status - test_document.txt: {status1_restored}")
        logger.info(f"Restored status - another_document.md: {status2_restored}")
        
        # Verify results
        logger.info("\\nVerifying results:")
        
        # Check if files are marked as NEW after restoration
        if status1_restored and status1_restored['status'] == 'new':
            logger.info("✓ test_document.txt correctly marked as NEW after restoration")
        else:
            logger.error("✗ test_document.txt not correctly marked as NEW")
            
        if status2_restored and status2_restored['status'] == 'new':
            logger.info("✓ another_document.md correctly marked as NEW after restoration")
        else:
            logger.error("✗ another_document.md not correctly marked as NEW")
            
        # Check if RAG URIs are maintained (for now they should be different)
        if status1_restored and status1_deleted:
            if status1_restored['rag_uri'] != status1_deleted['rag_uri']:
                logger.info("✓ New RAG URI generated for test_document.txt (expected behavior)")
            else:
                logger.warning("! Same RAG URI used for test_document.txt (unexpected)")
                
        # Step 7: Run sync again to check for duplicate deletions
        logger.info("\\nStep 7: Running sync again to check for duplicate handling")
        await run_sync(kb_name)
        
        # Check final status
        status1_final = await check_file_status(kb_name, "test_document.txt")
        status2_final = await check_file_status(kb_name, "another_document.md")
        
        logger.info(f"Final status - test_document.txt: {status1_final}")
        logger.info(f"Final status - another_document.md: {status2_final}")
        
        logger.info("\\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())