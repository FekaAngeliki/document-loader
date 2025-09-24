#!/usr/bin/env python3
"""
Get the correct site_id for the NBG Internal Audit Division SharePoint site.
"""

import asyncio
import aiohttp
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

async def get_site_id():
    """Get site_id for the NBG Internal Audit SharePoint site."""
    
    print("🔍 Getting Site ID for NBG Internal Audit Division")
    print("=" * 60)
    
    # Extract site information from the provided URL
    full_url = "https://groupnbg.sharepoint.com/sites/NBGInternalAuditDivision/Shared%20Documents/Forms/AllItems.aspx"
    site_url = "https://groupnbg.sharepoint.com/sites/NBGInternalAuditDivision"
    
    print(f"📄 Full URL: {full_url}")
    print(f"🏠 Site URL: {site_url}")
    
    # Parse URL for Graph API call
    parsed = urlparse(site_url)
    hostname = parsed.hostname
    site_path = parsed.path
    
    print(f"🌐 Hostname: {hostname}")
    print(f"📂 Site Path: {site_path}")
    
    # Get credentials
    tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
    client_id = os.getenv('SHAREPOINT_CLIENT_ID')  
    client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
    
    print(f"\n🔑 Using credentials:")
    print(f"   Tenant ID: {tenant_id}")
    print(f"   Client ID: {client_id}")
    print(f"   Client Secret: {'SET' if client_secret else 'NOT SET'}")
    
    # Step 1: Get access token
    print(f"\n1️⃣ Getting access token...")
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    access_token = token_data["access_token"]
                    print(f"   ✅ Access token obtained")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Token request failed: {response.status} - {error_text}")
                    return
        except Exception as e:
            print(f"   ❌ Token request error: {e}")
            return
        
        # Step 2: Try to get site_id using Graph API
        print(f"\n2️⃣ Getting site_id...")
        
        graph_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        print(f"   🔗 Graph URL: {graph_url}")
        
        try:
            async with session.get(graph_url, headers=headers) as response:
                if response.status == 200:
                    site_data = await response.json()
                    site_id = site_data.get("id")
                    print(f"   ✅ Site access successful!")
                    print(f"   📋 Site name: {site_data.get('displayName', 'Unknown')}")
                    print(f"   📋 Site URL: {site_data.get('webUrl', 'Unknown')}")
                    print(f"   📋 Site ID: {site_id}")
                    
                    # Test access to this site_id
                    print(f"\n3️⃣ Testing access to site_id...")
                    test_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}"
                    
                    async with session.get(test_url, headers=headers) as test_response:
                        if test_response.status == 200:
                            print(f"   ✅ Site_id access confirmed!")
                            return site_id
                        else:
                            print(f"   ❌ Site_id access failed: {test_response.status}")
                            
                elif response.status == 403:
                    error_text = await response.text()
                    print(f"   ❌ 403 Forbidden - Insufficient permissions")
                    print(f"   📜 Error details: {error_text}")
                    
                    # Try alternative approaches
                    print(f"\n🔄 Trying alternative approaches...")
                    
                    # Try with just the hostname
                    alt_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}"
                    print(f"   🔗 Trying root site: {alt_url}")
                    
                    async with session.get(alt_url, headers=headers) as alt_response:
                        if alt_response.status == 200:
                            root_data = await alt_response.json()
                            print(f"   ✅ Root site accessible: {root_data.get('displayName')}")
                            print(f"   📋 Root site ID: {root_data.get('id')}")
                        else:
                            print(f"   ❌ Root site access failed: {alt_response.status}")
                    
                elif response.status == 404:
                    print(f"   ❌ 404 Not Found - Site path may be incorrect")
                    print(f"   💡 Try checking if the site URL is correct")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Site access failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"   ❌ Site access error: {e}")
        
        # Step 3: Try searching for the site
        print(f"\n4️⃣ Searching for NBG Internal Audit sites...")
        
        search_terms = ["NBG", "Internal", "Audit", "NBGInternalAudit"]
        
        for term in search_terms:
            search_url = f"https://graph.microsoft.com/v1.0/sites?search={term}"
            
            try:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        sites_data = await response.json()
                        sites = sites_data.get('value', [])
                        if sites:
                            print(f"   🔍 Search '{term}' found {len(sites)} sites:")
                            for site in sites:
                                print(f"      • {site.get('displayName', 'Unknown')}")
                                print(f"        ID: {site.get('id', 'Unknown')}")
                                print(f"        URL: {site.get('webUrl', 'Unknown')}")
                                print()
                        else:
                            print(f"   ⚪ Search '{term}' found no sites")
                    elif response.status == 403:
                        print(f"   ❌ Search '{term}' - insufficient permissions")
                        break
                    else:
                        print(f"   ❌ Search '{term}' failed: {response.status}")
            except Exception as e:
                print(f"   ❌ Search '{term}' error: {e}")

if __name__ == "__main__":
    asyncio.run(get_site_id())