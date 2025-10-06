#!/usr/bin/env python3
"""
Quick script to check SharePoint libraries in Premium RMS site
"""
import asyncio
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.factory import Factory
from src.data.database import Database, DatabaseConfig
from src.data.repository import Repository

async def check_sharepoint_libraries():
    """Check what SharePoint libraries and folders exist in Premium RMS"""
    
    # Load the multi-source config to get SharePoint source details
    config_path = 'configs/premium-rms-kb-config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Find SharePoint source in the config
    sharepoint_source = None
    for source in config['sources']:
        if source['source_type'] == 'sharepoint_online':
            sharepoint_source = source
            break
    
    if not sharepoint_source:
        print('❌ No SharePoint source found in config')
        return
    
    print(f"📁 SharePoint source found: {sharepoint_source['source_id']}")
    print(f"🌐 Site URL: {sharepoint_source['source_config'].get('site_url', 'Not specified')}")
    
    # Connect to database
    db = Database(DatabaseConfig())
    await db.connect()
    repository = Repository(db)
    factory = Factory(repository)
    
    try:
        # Create SharePoint source
        print("\n🔐 Initializing SharePoint connection...")
        source = await factory.create_source(
            sharepoint_source['source_type'], 
            sharepoint_source['source_config']
        )
        await source.initialize()
        
        print('✅ Connected to SharePoint successfully!')
        print('📋 Listing libraries and folders...')
        
        # List files to see what libraries/folders are available
        files = await source.list_files()
        
        # Extract library names from file URIs
        libraries = set()
        folders = set()
        file_types = {}
        
        for i, file_metadata in enumerate(files):
            uri = file_metadata.uri
            
            # Show first few URI examples
            if i < 3:
                print(f"📄 Sample URI {i+1}: {uri}")
            
            # Count file types
            if hasattr(file_metadata, 'content_type') and file_metadata.content_type:
                file_types[file_metadata.content_type] = file_types.get(file_metadata.content_type, 0) + 1
            
            # Extract library and folder info from SharePoint URL structure
            if 'sharepoint.com' in uri:
                parts = uri.split('/')
                if 'sites' in parts:
                    sites_idx = parts.index('sites')
                    if sites_idx + 3 < len(parts):
                        library = parts[sites_idx + 3]
                        libraries.add(library)
                        
                        # Get folder path
                        if sites_idx + 4 < len(parts):
                            folder_parts = parts[sites_idx + 4:-1]  # Exclude filename
                            if folder_parts:
                                folder_path = '/'.join(folder_parts)
                                folders.add(f'{library}/{folder_path}')
        
        print(f'\n📊 STATISTICS')
        print(f'📁 Total files found: {len(files)}')
        print(f'📚 Total libraries: {len(libraries)}')
        print(f'📂 Total folders: {len(folders)}')
        
        print(f'\n📚 SHAREPOINT LIBRARIES:')
        for lib in sorted(libraries):
            # Count files in each library
            lib_files = [f for f in files if f'/{lib}/' in f.uri]
            print(f'  📚 {lib} ({len(lib_files)} files)')
        
        print(f'\n📂 FOLDER STRUCTURE (first 20):')
        for folder in sorted(list(folders)[:20]):
            # Count files in each folder
            folder_files = [f for f in files if f'/{folder}/' in f.uri]
            print(f'  📂 {folder} ({len(folder_files)} files)')
        
        if len(folders) > 20:
            print(f'  📂 ... and {len(folders) - 20} more folders')
        
        print(f'\n📄 FILE TYPES:')
        for file_type, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f'  📄 {file_type}: {count}')
        
        await source.cleanup()
        
    except Exception as e:
        print(f'❌ Error connecting to SharePoint: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_sharepoint_libraries())