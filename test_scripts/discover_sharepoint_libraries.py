#!/usr/bin/env python3
"""
Test script to discover SharePoint libraries in Premium RMS site using existing SharePoint client
This is an adhoc test - not part of the solution implementation
"""
import os
import sys
import asyncio
import json

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.implementations.enterprise_sharepoint_source import EnterpriseSharePointSource

async def discover_sharepoint_libraries():
    """Discover all SharePoint libraries using the existing SharePoint client"""
    
    print("🔍 Discovering SharePoint libraries in Premium RMS site")
    print("📋 Using existing enterprise SharePoint client...")
    
    # Configuration from the premium-rms config
    config = {
        "tenant_id": os.getenv('SHAREPOINT_TENANT_ID'),
        "client_id": os.getenv('SHAREPOINT_CLIENT_ID'),
        "client_secret": os.getenv('SHAREPOINT_CLIENT_SECRET'),
        "site_url": "https://groupnbg.sharepoint.com/sites/div991secb",
        "site_id": "6f63c8f0-aa51-4681-8da5-5d48f6255f69",
        "include_libraries": True,
        "library_names": ["Έγγραφα"],  # Current config
        "include_lists": False,
        "include_site_pages": False,
        "include_extensions": [".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"],
        "recursive": True,
        "timeout": 60,
        "max_retries": 3,
        "batch_size": 100
    }
    
    if not all([config["tenant_id"], config["client_id"], config["client_secret"]]):
        print("❌ Missing SharePoint credentials in environment variables")
        print("Required: SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET")
        return
    
    try:
        print("🔐 Initializing SharePoint connection...")
        
        # Create SharePoint source instance
        sharepoint_source = EnterpriseSharePointSource(config)
        await sharepoint_source.initialize()
        
        print("✅ Connected to SharePoint successfully!")
        
        # Access the SharePoint client to discover libraries
        site_client = sharepoint_source.site_client
        
        print("📚 Discovering document libraries...")
        
        # Get drives (document libraries) from the site
        drives = await site_client.get_drives()
        
        print(f"\n📊 Found {len(drives)} document libraries:")
        print("=" * 60)
        
        current_library = "Έγγραφα"
        found_current = False
        
        for i, drive in enumerate(drives, 1):
            name = drive.get("name", "Unknown")
            description = drive.get("description", "No description")
            web_url = drive.get("webUrl", "No URL")
            drive_type = drive.get("driveType", "Unknown")
            drive_id = drive.get("id", "Unknown")
            
            if name == current_library:
                found_current = True
                
            print(f"\n📚 Library {i}: {name}")
            print(f"   Type: {drive_type}")
            print(f"   Description: {description}")
            print(f"   Drive ID: {drive_id}")
            print(f"   URL: {web_url}")
            
            # Try to get some basic statistics
            try:
                items = await site_client.get_drive_items(drive_id, limit=1)
                print(f"   Status: ✅ Accessible")
            except Exception as e:
                print(f"   Status: ⚠️  Access limited ({str(e)[:50]}...)")
        
        print("\n" + "=" * 60)
        print(f"📋 SUMMARY:")
        print(f"   Total libraries found: {len(drives)}")
        print(f"   Currently configured library: '{current_library}'")
        print(f"   Current library exists: {'✅ Yes' if found_current else '❌ No'}")
        
        if not found_current:
            print(f"⚠️  WARNING: Current library '{current_library}' not found!")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   • To scan all libraries: remove 'library_names' from config")
        print(f"   • To scan specific libraries: update 'library_names' array")
        print(f"   • Current config only scans: {config['library_names']}")
        
        # Show what files are currently accessible
        print(f"\n📄 TESTING FILE ACCESS (current config):")
        try:
            files = await sharepoint_source.list_files()
            print(f"   Files accessible with current config: {len(files)}")
            
            if files:
                print(f"   Sample files:")
                for i, file_meta in enumerate(files[:3]):
                    print(f"   📄 {file_meta.uri}")
                if len(files) > 3:
                    print(f"   📄 ... and {len(files) - 3} more files")
        except Exception as e:
            print(f"   ❌ Error accessing files: {e}")
        
        await sharepoint_source.cleanup()
        
    except Exception as e:
        print(f"❌ Error discovering libraries: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(discover_sharepoint_libraries())