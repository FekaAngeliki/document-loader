#!/usr/bin/env python3
"""
Test script for SharePoint discovery functionality.

This script tests the SharePoint discovery utilities without requiring
a real SharePoint connection.
"""

import sys
import os
import json
from datetime import datetime

# Add parent directory to path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.sharepoint_discovery import SharePointSiteInfo, SharePointDiscovery
from src.utils.sharepoint_config_helper import SharePointConfigHelper, ConfigurationTemplate

def create_mock_site_info():
    """Create mock SharePoint site info for testing."""
    libraries = [
        {
            'id': 'lib-001',
            'title': 'Documents',
            'description': 'Main document library',
            'base_template': 101,
            'item_count': 150,
            'server_relative_url': '/sites/marketing/Documents',
            'hidden': False,
            'list_type': 'DocumentLibrary'
        },
        {
            'id': 'lib-002',
            'title': 'Presentations',
            'description': 'Marketing presentations',
            'base_template': 101,
            'item_count': 45,
            'server_relative_url': '/sites/marketing/Presentations',
            'hidden': False,
            'list_type': 'DocumentLibrary'
        },
        {
            'id': 'lib-003',
            'title': 'Templates',
            'description': 'Document templates',
            'base_template': 101,
            'item_count': 25,
            'server_relative_url': '/sites/marketing/Templates',
            'hidden': False,
            'list_type': 'DocumentLibrary'
        }
    ]
    
    lists = [
        {
            'id': 'list-001',
            'title': 'Marketing Calendar',
            'description': 'Marketing events and campaigns',
            'base_template': 106,
            'item_count': 75,
            'server_relative_url': '/sites/marketing/Lists/MarketingCalendar',
            'hidden': False,
            'list_type': 'GenericList'
        },
        {
            'id': 'list-002',
            'title': 'Contact List',
            'description': 'Marketing contacts',
            'base_template': 105,
            'item_count': 200,
            'server_relative_url': '/sites/marketing/Lists/Contacts',
            'hidden': False,
            'list_type': 'GenericList'
        }
    ]
    
    pages = [
        {
            'id': 1,
            'title': 'Home',
            'file_name': 'Home.aspx',
            'server_relative_url': '/sites/marketing/SitePages/Home.aspx',
            'created': '2024-01-15T10:00:00Z',
            'modified': '2024-01-20T14:30:00Z'
        },
        {
            'id': 2,
            'title': 'Team Information',
            'file_name': 'Team.aspx',
            'server_relative_url': '/sites/marketing/SitePages/Team.aspx',
            'created': '2024-01-16T09:15:00Z',
            'modified': '2024-01-18T11:45:00Z'
        }
    ]
    
    return SharePointSiteInfo(
        site_url="https://contoso.sharepoint.com/sites/marketing",
        site_id="12345678-1234-1234-1234-123456789012",
        site_name="Marketing Team",
        web_id="87654321-4321-4321-4321-210987654321",
        tenant_name="contoso",
        lists=lists,
        libraries=libraries,
        pages=pages
    )

def test_url_parsing():
    """Test SharePoint URL parsing functionality."""
    print("Testing SharePoint URL parsing...")
    
    # Create auth config (mock)
    auth_config = {
        'tenant_id': 'test-tenant',
        'client_id': 'test-client',
        'client_secret': 'test-secret'
    }
    
    discovery = SharePointDiscovery(auth_config)
    
    # Test various URL formats
    test_urls = [
        "https://contoso.sharepoint.com/sites/marketing",
        "https://contoso.sharepoint.com/teams/development", 
        "https://fabrikam.sharepoint.com/sites/hr/subsite",
        "https://company.sharepoint.com/"
    ]
    
    for url in test_urls:
        try:
            parsed = discovery.parse_sharepoint_url(url)
            print(f"  ✓ {url}")
            print(f"    Tenant: {parsed['tenant_name']}")
            print(f"    Site: {parsed.get('site_name', 'N/A')}")
            print(f"    Collection: {parsed.get('site_collection', 'N/A')}")
        except Exception as e:
            print(f"  ✗ {url}: {e}")
    
    print()

def test_config_helper():
    """Test configuration helper functionality."""
    print("Testing configuration helper...")
    
    # Create mock site info and auth config
    site_info = create_mock_site_info()
    auth_config = {
        'tenant_id': 'test-tenant-id',
        'client_id': 'test-client-id',
        'client_secret': 'test-client-secret'
    }
    
    helper = SharePointConfigHelper(site_info, auth_config)
    
    # Test listing available sources
    sources = helper.list_available_sources()
    print(f"  Available libraries: {len(sources['libraries'])}")
    print(f"  Available lists: {len(sources['lists'])}")
    print(f"  Available pages: {len(sources['pages'])}")
    
    # Test template-based configuration
    templates = helper.templates
    print(f"  Available templates: {len(templates)}")
    
    for template in templates:
        print(f"    - {template.name}: {template.description}")
    
    # Test creating configuration from template
    template = templates[0]  # "all_documents"
    config = helper.create_configuration_from_template(template, "test-kb")
    
    print(f"  Generated config for template '{template.name}':")
    print(f"    KB name: {config['name']}")
    print(f"    Sources: {len(config['source_config']['sources'])}")
    
    # Test validation
    is_valid, issues = helper.validate_configuration(config)
    print(f"    Validation: {'✓ Valid' if is_valid else f'✗ {len(issues)} issues'}")
    if issues:
        for issue in issues:
            print(f"      - {issue}")
    
    # Test custom configuration
    custom_config = helper.create_custom_configuration(
        kb_name="custom-test-kb",
        selected_libraries=["Documents", "Presentations"],
        include_pages=True,
        rag_type="azure_blob"
    )
    
    print(f"  Custom config:")
    print(f"    KB name: {custom_config['name']}")
    print(f"    Sources: {len(custom_config['source_config']['sources'])}")
    print(f"    RAG type: {custom_config['rag_type']}")
    
    # Test CLI command generation
    commands = helper.generate_cli_commands(config)
    print(f"  Generated {len(commands)} CLI commands")
    
    print()

def test_configuration_export():
    """Test configuration export functionality."""
    print("Testing configuration export...")
    
    # Create mock configuration
    site_info = create_mock_site_info()
    auth_config = {'tenant_id': 'test', 'client_id': 'test', 'client_secret': 'test'}
    helper = SharePointConfigHelper(site_info, auth_config)
    
    config = helper.create_configuration_from_template(helper.templates[0], "export-test-kb")
    
    # Test JSON export
    json_file = "/tmp/test-config.json"
    success = helper.export_configuration(config, json_file, "json")
    print(f"  JSON export: {'✓ Success' if success else '✗ Failed'}")
    
    if success and os.path.exists(json_file):
        with open(json_file, 'r') as f:
            exported = json.load(f)
        print(f"    Exported config has {len(exported)} top-level keys")
        os.remove(json_file)
    
    print()

def test_configuration_summary():
    """Test configuration summary generation."""
    print("Testing configuration summary...")
    
    site_info = create_mock_site_info()
    auth_config = {'tenant_id': 'test', 'client_id': 'test', 'client_secret': 'test'}
    helper = SharePointConfigHelper(site_info, auth_config)
    
    config = helper.create_configuration_from_template(helper.templates[2], "summary-test-kb")  # "everything" template
    
    summary = helper.print_configuration_summary(config)
    print("  Generated configuration summary:")
    print("  " + "─" * 50)
    
    # Print first few lines of summary
    lines = summary.split('\n')
    for line in lines[:15]:  # Show first 15 lines
        print(f"  {line}")
    
    if len(lines) > 15:
        print(f"  ... ({len(lines) - 15} more lines)")
    
    print()

def main():
    """Run all tests."""
    print("SharePoint Discovery Test Suite")
    print("=" * 40)
    print()
    
    try:
        test_url_parsing()
        test_config_helper()
        test_configuration_export()
        test_configuration_summary()
        
        print("All tests completed successfully! ✓")
        print()
        print("Note: These tests use mock data. To test with real SharePoint:")
        print("1. Set up proper authentication credentials")
        print("2. Use the CLI commands:")
        print("   document-loader discover-sharepoint <site-url> [auth-options]")
        print("   document-loader generate-sharepoint-config <site-url> [options]")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())