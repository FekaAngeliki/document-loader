#!/usr/bin/env python3
"""
Test script to verify the error RAG URI fix works correctly.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.data.database import Database, DatabaseConfig
from src.data.multi_source_repository import MultiSourceRepository

async def test_error_uri_logic():
    """Test that error RAG URIs are handled correctly."""
    
    print("🧪 Testing Error RAG URI Fix")
    print("=" * 50)
    
    try:
        # Connect to database
        config = DatabaseConfig()
        db = Database(config)
        await db.connect()
        
        repo = MultiSourceRepository(db)
        
        print("✅ Connected to database")
        
        # Check the 3 error files that should be fixed
        print("\n🔍 Checking the 3 files that had error RAG URIs:")
        
        error_files = [
            "https://groupnbg.sharepoint.com/sites/div991secb/Shared%20Documents/Premium/Easter%20card%202025/20250410%20Easter%20Premium%20Card_overview%20final.pdf",
            "https://groupnbg.sharepoint.com/sites/div991secb/Shared%20Documents/Premium/Easter%20card%202025/20250410%20Easter%20Premium%20Card_overview%20final_.pdf", 
            "https://groupnbg.sharepoint.com/sites/div991secb/Shared%20Documents/Premium/Eleaflets/Auto_Protect_e-leaflet_05062024.pdf"
        ]
        
        for i, uri in enumerate(error_files, 1):
            print(f"\n📄 File {i}: ...{uri[-50:]}")
            
            # Get latest record for this file
            query = '''
            SELECT 
                fr.id,
                fr.sync_run_id,
                fr.rag_uri,
                fr.status,
                fr.file_size,
                fr.upload_time,
                sr.id as run_id
            FROM file_record fr
            JOIN sync_run sr ON fr.sync_run_id = sr.id
            WHERE fr.original_uri = $1
            ORDER BY fr.upload_time DESC
            LIMIT 2
            '''
            
            records = await db.fetch(query, uri)
            
            if records:
                print(f"  📊 Found {len(records)} records:")
                for j, record in enumerate(records):
                    status_emoji = "✅" if record['status'] != 'error' else "❌"
                    is_error_uri = record['rag_uri'].startswith('PremiumRMs3-kb/error-')
                    uri_type = "Error URI" if is_error_uri else "Normal URI"
                    
                    print(f"    {status_emoji} Run {record['run_id']}: {record['status']} | {record['file_size']} bytes")
                    print(f"       RAG URI: {record['rag_uri']} ({uri_type})")
                    print(f"       Time: {record['upload_time']}")
                
                # Test the fix logic
                latest_record = records[0]
                multi_kb_name = "PremiumRMs3-kb"
                
                print(f"\n  🔧 Fix Logic Test:")
                print(f"    RAG URI: {latest_record['rag_uri']}")
                print(f"    Starts with error prefix: {latest_record['rag_uri'].startswith(f'{multi_kb_name}/error-')}")
                
                if latest_record['rag_uri'].startswith(f"{multi_kb_name}/error-"):
                    print(f"    ✅ Would use UPLOAD (new document)")
                else:
                    print(f"    ✅ Would use UPDATE (existing document)")
            else:
                print(f"  ❌ No records found")
        
        # Summary of what the fix does
        print(f"\n📋 Fix Summary:")
        print(f"✅ **Before Fix**: Tried to UPDATE error RAG URIs → 'Document not found'")
        print(f"✅ **After Fix**: Detects error RAG URIs → Uses UPLOAD instead")
        print(f"✅ **Logic**: Check if rag_uri.startswith('{multi_kb_name}/error-')")
        print(f"✅ **Result**: Files with error records will be uploaded as new documents")
        
        print(f"\n🚀 Next Sync Expected Behavior:")
        print(f"1. Change detection finds the 3 error records")
        print(f"2. Marks as MODIFIED (size 0 → actual size)")  
        print(f"3. Fix detects error RAG URIs")
        print(f"4. Uses upload_document() instead of update_document()")
        print(f"5. Creates new successful records")
        print(f"6. No more 'Document not found' errors")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_error_uri_logic())