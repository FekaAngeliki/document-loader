#!/usr/bin/env python3
"""Test script to verify consistent RAG URIs across multiple sync runs."""

import asyncio
import asyncpg
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    # Database connection
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Query to check if files maintain consistent RAG URIs across sync runs
    query = """
    WITH file_uris AS (
        SELECT 
            fr.original_uri,
            fr.rag_uri,
            fr.sync_run_id,
            sr.start_time,
            kb.name as kb_name,
            ROW_NUMBER() OVER (PARTITION BY fr.original_uri ORDER BY sr.start_time) as occurrence
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
        ORDER BY fr.original_uri, sr.start_time
    ),
    inconsistent_files AS (
        SELECT 
            f1.original_uri,
            f1.kb_name,
            f1.rag_uri as first_rag_uri,
            f2.rag_uri as second_rag_uri,
            f1.sync_run_id as first_sync_run,
            f2.sync_run_id as second_sync_run,
            f1.start_time as first_sync_time,
            f2.start_time as second_sync_time
        FROM file_uris f1
        JOIN file_uris f2 ON f1.original_uri = f2.original_uri 
                          AND f1.kb_name = f2.kb_name
                          AND f1.occurrence = 1 
                          AND f2.occurrence = 2
        WHERE f1.rag_uri != f2.rag_uri
    )
    SELECT * FROM inconsistent_files;
    """
    
    print("=== Testing Consistent RAG URIs Across Sync Runs ===\n")
    
    # First, show all sync runs
    sync_runs_query = """
    SELECT sr.id, sr.start_time, sr.status, kb.name as kb_name,
           sr.total_files, sr.new_files, sr.modified_files
    FROM sync_run sr
    JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
    ORDER BY sr.start_time DESC
    """
    
    runs = await conn.fetch(sync_runs_query)
    print(f"Found {len(runs)} sync runs:")
    for run in runs:
        print(f"  Run {run['id']}: {run['kb_name']} - {run['start_time']} - "
              f"Status: {run['status']} - Files: {run['total_files']} "
              f"(new: {run['new_files']}, modified: {run['modified_files']})")
    print()
    
    # Check for inconsistent URIs
    inconsistent = await conn.fetch(query)
    
    if inconsistent:
        print(f"❌ Found {len(inconsistent)} files with INCONSISTENT RAG URIs across runs:")
        for row in inconsistent:
            print(f"\n  File: {row['original_uri']}")
            print(f"  KB: {row['kb_name']}")
            print(f"  First sync (Run {row['first_sync_run']} @ {row['first_sync_time']}):")
            print(f"    RAG URI: {row['first_rag_uri']}")
            print(f"  Second sync (Run {row['second_sync_run']} @ {row['second_sync_time']}):")
            print(f"    RAG URI: {row['second_rag_uri']}")
    else:
        print("✅ Good news! All files maintain consistent RAG URIs across sync runs!")
    
    # Show sample of consistent files
    consistent_query = """
    WITH file_uris AS (
        SELECT 
            fr.original_uri,
            fr.rag_uri,
            COUNT(*) OVER (PARTITION BY fr.original_uri) as sync_count
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE fr.original_uri IN (
            SELECT DISTINCT original_uri 
            FROM file_record 
            GROUP BY original_uri 
            HAVING COUNT(DISTINCT sync_run_id) > 1
        )
        ORDER BY fr.original_uri
    )
    SELECT DISTINCT original_uri, rag_uri, sync_count
    FROM file_uris
    LIMIT 5;
    """
    
    consistent = await conn.fetch(consistent_query)
    if consistent:
        print(f"\n✨ Sample of files with consistent RAG URIs across {consistent[0]['sync_count']} sync runs:")
        for row in consistent:
            print(f"  {row['original_uri']}")
            print(f"    → {row['rag_uri']}")
            print(f"    (appears in {row['sync_count']} sync runs)")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())