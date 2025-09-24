#!/usr/bin/env python3
"""
Simple test for SharePoint discovery commands without full CLI setup.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_sharepoint_imports():
    """Test that SharePoint modules can be imported."""
    print("Testing SharePoint discovery imports...")
    
    try:
        from src.utils.sharepoint_discovery import SharePointDiscovery, SharePointSiteInfo
        print("  ✓ SharePoint discovery module imported")
    except ImportError as e:
        print(f"  ✗ Failed to import SharePoint discovery: {e}")
        return False
    
    try:
        from src.utils.sharepoint_config_helper import SharePointConfigHelper
        print("  ✓ SharePoint config helper imported")
    except ImportError as e:
        print(f"  ✗ Failed to import config helper: {e}")
        return False
    
    return True

def test_url_parsing():
    """Test URL parsing without requiring Office365 package."""
    print("\nTesting URL parsing functionality...")
    
    try:
        from src.utils.sharepoint_discovery import SharePointDiscovery
        
        # Create discovery instance (won't actually connect)
        auth_config = {'tenant_id': 'test', 'client_id': 'test', 'client_secret': 'test'}
        discovery = SharePointDiscovery(auth_config)
        
        # Test URL parsing
        test_urls = [
            "https://contoso.sharepoint.com/sites/marketing",
            "https://company.sharepoint.com/teams/development"
        ]
        
        for url in test_urls:
            parsed = discovery.parse_sharepoint_url(url)
            print(f"  ✓ Parsed {url}")
            print(f"    Tenant: {parsed['tenant_name']}, Site: {parsed.get('site_name', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ URL parsing failed: {e}")
        return False

def main():
    """Run tests."""
    print("SharePoint Discovery Quick Test")
    print("=" * 35)
    
    all_passed = True
    
    # Test imports
    if not test_sharepoint_imports():
        all_passed = False
    
    # Test URL parsing  
    if not test_url_parsing():
        all_passed = False
    
    print(f"\n{'✓ All tests passed!' if all_passed else '✗ Some tests failed'}")
    
    if all_passed:
        print("\nNext steps to test with real SharePoint:")
        print("1. Install Office365-REST-Python-Client: uv add Office365-REST-Python-Client")
        print("2. Set up authentication (service principal or user credentials)")
        print("3. Run: python3 test_scripts/test_sharepoint_discovery.py")
        print("4. Try CLI commands:")
        print("   python3 -c \"from document_loader.cli import cli; cli(['discover-sharepoint', '--help'])\"")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())