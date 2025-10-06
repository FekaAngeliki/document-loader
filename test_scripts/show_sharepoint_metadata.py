#!/usr/bin/env python3
"""
Test script to show available metadata for SharePoint documents
This is an adhoc test - not part of the solution implementation
"""
import json
import os

def show_sharepoint_metadata_info():
    """Show information about SharePoint document metadata"""
    
    print("📋 SharePoint Document Metadata Information")
    print("=" * 70)
    
    print("🏢 ENTERPRISE SHAREPOINT METADATA CATEGORIES:")
    print()
    
    print("📄 1. CORE DOCUMENT PROPERTIES:")
    print("   • ID - Unique item identifier")
    print("   • Name - File name")
    print("   • Title - Document title (if set)")
    print("   • Created - Creation date/time")
    print("   • Modified - Last modification date/time")
    print("   • File_x0020_Size - File size in bytes")
    print("   • File_x0020_Type - File extension")
    print("   • ServerRedirectedEmbedUrl - SharePoint viewing URL")
    print("   • ServerRelativeUrl - Relative path within site")
    print("   • UniqueId - GUID identifier")
    print("   • VersionLabel - Version number (1.0, 2.0, etc.)")
    
    print("\n👤 2. AUTHOR/EDITOR INFORMATION:")
    print("   • Author - User who created the document")
    print("   • Editor - User who last modified the document")
    print("   • AuthorId - ID of creating user")
    print("   • EditorId - ID of modifying user")
    print("   • CreatedBy - Full author details")
    print("   • ModifiedBy - Full editor details")
    
    print("\n🏷️  3. CONTENT TYPE & CLASSIFICATION:")
    print("   • ContentType - SharePoint content type")
    print("   • ContentTypeId - Content type identifier")
    print("   • DocIcon - Icon associated with file type")
    print("   • ProgId - Program identifier")
    
    print("\n📁 4. LOCATION & ORGANIZATION:")
    print("   • FileLeafRef - File name only")
    print("   • FileDirRef - Directory path")
    print("   • FileRef - Full path reference")
    print("   • BaseName - File name without extension")
    print("   • FSObjType - File system object type (0=file, 1=folder)")
    
    print("\n🔒 5. PERMISSIONS & WORKFLOW:")
    print("   • PermMask - Permission mask")
    print("   • CheckoutUser - User who has checked out the file")
    print("   • CheckedOutUserId - ID of checkout user")
    print("   • IsCheckedoutToLocal - Local checkout status")
    print("   • WorkflowVersion - Workflow version number")
    
    print("\n📊 6. CUSTOM COLUMNS (Site-Specific):")
    print("   • Department - Custom department field")
    print("   • Project - Custom project field") 
    print("   • Category - Custom category field")
    print("   • Status - Custom status field")
    print("   • Keywords - Custom keywords/tags")
    print("   • Comments - Custom comments field")
    print("   • Any other custom columns defined in the library")
    
    print("\n🔍 7. SEARCH & DISCOVERY:")
    print("   • ListItemAllFields - All available fields")
    print("   • ParentList - Parent library information")
    print("   • WebId - Web/site identifier")
    print("   • SiteId - Site collection identifier")
    
    print("\n📈 8. USAGE & ANALYTICS:")
    print("   • ViewsLifetime - Total views")
    print("   • ViewsRecent - Recent views")
    print("   • Last_x0020_Modified - Last modification timestamp")
    
    print("\n" + "=" * 70)
    
    # Show current configuration
    config_file = "configs/premium-rms-kb-config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        sharepoint_source = None
        for source in config.get('sources', []):
            if source.get('source_type') == 'enterprise_sharepoint':
                sharepoint_source = source
                break
        
        if sharepoint_source:
            print("🔧 YOUR CURRENT METADATA CONFIGURATION:")
            metadata_tags = sharepoint_source.get('metadata_tags', {})
            print(f"   Currently capturing these metadata tags:")
            for key, value in metadata_tags.items():
                print(f"   • {key}: {value}")
            
            print(f"\n💡 TO CAPTURE MORE METADATA:")
            print(f"   Add more fields to 'metadata_tags' in your config:")
            print(f"   Example additions:")
            print(f'   "Author": "{{Author}}"')
            print(f'   "Modified": "{{Modified}}"')
            print(f'   "ContentType": "{{ContentType}}"')
            print(f'   "Department": "{{Department}}"')
            print(f'   "FileSize": "{{File_x0020_Size}}"')
    
    print(f"\n📝 IMPORTANT NOTES:")
    print(f"   • Metadata availability depends on:")
    print(f"     - Library configuration")
    print(f"     - Content types enabled")
    print(f"     - Custom columns defined")
    print(f"     - User permissions")
    print(f"   • Some metadata may be empty if not populated")
    print(f"   • Custom fields vary by organization/library setup")
    
    print(f"\n🔍 TO DISCOVER ACTUAL METADATA:")
    print(f"   1. Access your SharePoint library directly")
    print(f"   2. View library settings → Columns")
    print(f"   3. Check content types and their fields")
    print(f"   4. Test with a sample document sync to see what's captured")

if __name__ == "__main__":
    show_sharepoint_metadata_info()