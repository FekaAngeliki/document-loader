#!/usr/bin/env python3
"""
Test script for Enterprise SharePoint source

This script tests the Enterprise SharePoint integration with your clientID, 
clientSecret, and tenantID across multiple department sites.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from implementations.enterprise_sharepoint_source import EnterpriseSharePointSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_authentication():
    """Test SharePoint authentication with your credentials."""
    
    config = {
        "tenant_id": os.getenv("SHAREPOINT_TENANT_ID", "your-tenant-id-here"),
        "client_id": os.getenv("SHAREPOINT_CLIENT_ID", "your-client-id-here"),
        "client_secret": os.getenv("SHAREPOINT_CLIENT_SECRET", "your-client-secret-here"),
        "site_url": "https://yourorg.sharepoint.com/sites/hr",  # Update with your site
        "include_libraries": True,
        "include_lists": True,
        "include_site_pages": False,
        "include_extensions": [".pdf", ".docx", ".xlsx"],
        "recursive": True
    }
    
    source = EnterpriseSharePointSource(config)
    
    try:
        print("Testing SharePoint authentication...")
        await source.initialize()
        print("✅ Authentication successful!")
        return True
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    finally:
        await source.cleanup()

async def test_multi_site_access():
    """Test access to multiple SharePoint sites."""
    
    sites_to_test = [
        "https://yourorg.sharepoint.com/sites/hr",
        "https://yourorg.sharepoint.com/sites/finance", 
        "https://yourorg.sharepoint.com/sites/marketing",
        "https://yourorg.sharepoint.com/sites/it"
    ]
    
    config = {
        "tenant_id": os.getenv("SHAREPOINT_TENANT_ID"),
        "client_id": os.getenv("SHAREPOINT_CLIENT_ID"),
        "client_secret": os.getenv("SHAREPOINT_CLIENT_SECRET"),
        "include_libraries": True,
        "include_lists": True,
        "recursive": False  # Don't recurse for testing
    }
    
    results = {}
    
    for site_url in sites_to_test:
        print(f"\nTesting access to: {site_url}")
        
        site_config = config.copy()
        site_config["site_url"] = site_url
        
        source = EnterpriseSharePointSource(site_config)
        
        try:
            await source.initialize()
            site_id = await source._get_site_id(site_url)
            
            if site_id:
                print(f"✅ Site accessible: {site_id}")
                
                # Test getting document libraries
                libraries = await source._get_document_libraries(site_id)
                print(f"   📁 Found {len(libraries)} document libraries")
                for lib in libraries[:3]:  # Show first 3
                    print(f"      - {lib.get('name', 'Unknown')}")
                
                # Test getting SharePoint lists
                lists = await source._get_sharepoint_lists(site_id)
                print(f"   📋 Found {len(lists)} SharePoint lists")
                for sp_list in lists[:3]:  # Show first 3
                    print(f"      - {sp_list.get('displayName', 'Unknown')}")
                
                results[site_url] = "accessible"
            else:
                print(f"❌ Site not accessible or not found")
                results[site_url] = "not accessible"
                
        except Exception as e:
            print(f"❌ Error accessing site: {e}")
            results[site_url] = f"error: {e}"
        finally:
            await source.cleanup()
    
    return results

async def test_file_listing():
    """Test listing files from a SharePoint site."""
    
    config = {
        "tenant_id": os.getenv("SHAREPOINT_TENANT_ID"),
        "client_id": os.getenv("SHAREPOINT_CLIENT_ID"),
        "client_secret": os.getenv("SHAREPOINT_CLIENT_SECRET"),
        "site_url": "https://yourorg.sharepoint.com/sites/hr",  # Update with your site
        "include_libraries": True,
        "include_lists": True,
        "include_site_pages": False,
        "include_extensions": [".pdf", ".docx", ".xlsx", ".txt"],
        "recursive": True
    }
    
    source = EnterpriseSharePointSource(config)
    
    try:
        print("\nTesting file listing...")
        await source.initialize()
        
        files = await source.list_files()
        
        print(f"✅ Found {len(files)} files")
        
        # Show file type breakdown
        file_types = {}
        for file in files:
            ext = Path(file.uri).suffix.lower()
            file_types[ext] = file_types.get(ext, 0) + 1
        
        print("📊 File type breakdown:")
        for ext, count in sorted(file_types.items()):
            print(f"   {ext or 'no extension'}: {count} files")
        
        # Show first few files
        print("\n📄 Sample files:")
        for file in files[:5]:
            print(f"   - {Path(file.uri).name} ({file.size} bytes)")
        
        return True
        
    except Exception as e:
        print(f"❌ File listing failed: {e}")
        return False
    finally:
        await source.cleanup()

async def test_department_specific_config():
    """Test configuration for specific departments."""
    
    dept_configs = {
        "HR": {
            "site_url": "https://yourorg.sharepoint.com/sites/hr",
            "library_filters": ["Shared Documents", "Policies", "Employee Handbook"],
            "list_filters": ["Employee Directory", "Training Records"]
        },
        "Finance": {
            "site_url": "https://yourorg.sharepoint.com/sites/finance",
            "library_filters": ["Financial Reports", "Budgets"], 
            "list_filters": ["Expense Reports", "Budget Approvals"]
        },
        "Marketing": {
            "site_url": "https://yourorg.sharepoint.com/sites/marketing",
            "library_filters": ["Campaign Assets", "Brand Guidelines"],
            "include_site_pages": True
        }
    }
    
    base_config = {
        "tenant_id": os.getenv("SHAREPOINT_TENANT_ID"),
        "client_id": os.getenv("SHAREPOINT_CLIENT_ID"),
        "client_secret": os.getenv("SHAREPOINT_CLIENT_SECRET"),
        "include_libraries": True,
        "include_lists": True,
        "include_site_pages": False,
        "recursive": False
    }
    
    for dept, dept_config in dept_configs.items():
        print(f"\nTesting {dept} department configuration...")
        
        config = base_config.copy()
        config.update(dept_config)
        
        source = EnterpriseSharePointSource(config)
        
        try:
            await source.initialize()
            site_id = await source._get_site_id(config["site_url"])
            
            if site_id:
                print(f"✅ {dept} site accessible")
                
                # Test specific library filters
                if "library_filters" in dept_config:
                    libraries = await source._get_document_libraries(site_id)
                    filtered_libs = [lib for lib in libraries 
                                   if lib.get('name', '') in dept_config["library_filters"]]
                    print(f"   📁 Found {len(filtered_libs)} filtered libraries out of {len(libraries)} total")
                
            else:
                print(f"❌ {dept} site not accessible")
                
        except Exception as e:
            print(f"❌ {dept} test failed: {e}")
        finally:
            await source.cleanup()

async def run_all_tests():
    """Run all tests."""
    
    print("Enterprise SharePoint Source Tests")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ["SHAREPOINT_TENANT_ID", "SHAREPOINT_CLIENT_ID", "SHAREPOINT_CLIENT_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment")
        return
    
    # Run tests
    tests = [
        ("Authentication", test_authentication),
        ("Multi-site Access", test_multi_site_access),
        ("File Listing", test_file_listing),
        ("Department Configs", test_department_specific_config)
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
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('.env.enterprise')
    
    asyncio.run(run_all_tests())