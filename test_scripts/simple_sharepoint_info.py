#!/usr/bin/env python3
"""
Simple script to show SharePoint configuration information
This is an adhoc test - not part of the solution implementation
"""
import json
import os

def show_sharepoint_info():
    """Show current SharePoint configuration and suggest library discovery methods"""
    
    print("🔍 SharePoint Library Discovery for Premium RMS")
    print("=" * 60)
    
    # Read current configuration
    config_file = "configs/premium-rms-kb-config.json"
    
    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        return
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Find SharePoint source
    sharepoint_source = None
    for source in config.get('sources', []):
        if source.get('source_type') == 'enterprise_sharepoint':
            sharepoint_source = source
            break
    
    if not sharepoint_source:
        print("❌ No SharePoint source found in configuration")
        return
    
    print("📋 CURRENT SHAREPOINT CONFIGURATION:")
    print(f"   Site URL: {sharepoint_source['source_config']['site_url']}")
    print(f"   Site ID: {sharepoint_source['source_config']['site_id']}")
    print(f"   Include Libraries: {sharepoint_source['source_config']['include_libraries']}")
    print(f"   Current Library: {sharepoint_source['source_config']['library_names']}")
    print(f"   Include Lists: {sharepoint_source['source_config']['include_lists']}")
    print(f"   Include Site Pages: {sharepoint_source['source_config']['include_site_pages']}")
    print(f"   Recursive Scan: {sharepoint_source['source_config']['recursive']}")
    
    print(f"\n📄 FILE TYPES CONFIGURED:")
    extensions = sharepoint_source['source_config']['include_extensions']
    print(f"   Extensions: {', '.join(extensions)}")
    
    print(f"\n🏷️  METADATA TAGS:")
    for key, value in sharepoint_source['metadata_tags'].items():
        print(f"   {key}: {value}")
    
    print(f"\n📊 CURRENT STATUS:")
    print(f"   Currently scanning only: {sharepoint_source['source_config']['library_names'][0]}")
    print(f"   To discover all libraries, you have these options:")
    
    print(f"\n💡 DISCOVERY OPTIONS:")
    print(f"   1. Manual Check:")
    print(f"      Visit: {sharepoint_source['source_config']['site_url']}")
    print(f"      Browse the site to see all available libraries")
    
    print(f"\n   2. Modify Config Temporarily:")
    print(f"      - Remove 'library_names' array from config")
    print(f"      - Run a test sync to see what libraries are discovered")
    print(f"      - Check the logs for library names found")
    
    print(f"\n   3. Check Existing Database:")
    print(f"      - Run: document-loader db files --kb-name 'PremiumRMs-kb_placeholder'")
    print(f"      - Look at file URIs to see library structure")
    
    print(f"\n   4. Use Multi-Source Analyze:")
    print(f"      - Run: document-loader multi-source analyze-sources --config-name 'PremiumRMs-kb'")
    print(f"      - This might show more details about source structure")
    
    # Check environment variables
    print(f"\n🔐 AUTHENTICATION STATUS:")
    required_vars = ['SHAREPOINT_TENANT_ID', 'SHAREPOINT_CLIENT_ID', 'SHAREPOINT_CLIENT_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"   ✅ {var}: Set")
        else:
            print(f"   ❌ {var}: Missing")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  WARNING: Missing environment variables: {', '.join(missing_vars)}")
        print(f"   Set these variables to enable SharePoint access")
    
    print(f"\n📚 SHAREPOINT LIBRARY NAMING:")
    print(f"   Current library 'Έγγραφα' means 'Documents' in Greek")
    print(f"   This is likely the default document library")
    print(f"   Other common library names in SharePoint:")
    print(f"   - Shared Documents")
    print(f"   - Site Assets") 
    print(f"   - Style Library")
    print(f"   - Form Templates")
    print(f"   - Custom libraries created by users")
    
    print(f"\n🎯 RECOMMENDATION:")
    print(f"   Visit the SharePoint site directly to see all available libraries:")
    print(f"   {sharepoint_source['source_config']['site_url']}")
    print(f"   Then update the 'library_names' array in the config file")

if __name__ == "__main__":
    show_sharepoint_info()