#!/usr/bin/env python3
"""
Test script to verify site_id access with current credentials.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_site_access():
    """Test direct access to the SharePoint site using provided credentials."""
    
    print("🔍 Testing SharePoint Site Access")
    print("=" * 50)
    
    # Get credentials from environment
    tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
    client_id = os.getenv('SHAREPOINT_CLIENT_ID')  
    client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
    site_id = "ba00c686-567e-41e8-b320-2d54f35bfe54"
    
    print(f"🔑 Using credentials:")
    print(f"   Tenant ID: {tenant_id}")
    print(f"   Client ID: {client_id}")
    print(f"   Client Secret: {'SET' if client_secret else 'NOT SET'}")
    print(f"   Site ID: {site_id}")
    
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
        
        # Step 2: Test site access
        print(f"\n2️⃣ Testing site access...")
        
        graph_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with session.get(graph_url, headers=headers) as response:
                if response.status == 200:
                    site_data = await response.json()
                    print(f"   ✅ Site access successful!")
                    print(f"   📋 Site name: {site_data.get('displayName', 'Unknown')}")
                    print(f"   📋 Site URL: {site_data.get('webUrl', 'Unknown')}")
                elif response.status == 403:
                    error_text = await response.text()
                    print(f"   ❌ 403 Forbidden - Insufficient permissions")
                    print(f"   📜 Error details: {error_text}")
                    print(f"\n💡 Possible solutions:")
                    print(f"   1. Ask your admin to grant 'Sites.Selected' permission")
                    print(f"   2. Grant specific site permissions for this site_id")
                    print(f"   3. Use a different site_id you have access to")
                elif response.status == 404:
                    print(f"   ❌ 404 Not Found - Site ID may be incorrect")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Site access failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"   ❌ Site access error: {e}")
        
        # Step 3: Test alternative - list all accessible sites
        print(f"\n3️⃣ Testing accessible sites...")
        
        sites_url = "https://graph.microsoft.com/v1.0/sites?search=*"
        
        try:
            async with session.get(sites_url, headers=headers) as response:
                if response.status == 200:
                    sites_data = await response.json()
                    sites = sites_data.get('value', [])
                    print(f"   ✅ Found {len(sites)} accessible sites:")
                    for site in sites[:5]:  # Show first 5 sites
                        print(f"      • {site.get('displayName', 'Unknown')} (ID: {site.get('id', 'Unknown')})")
                        if site.get('webUrl'):
                            print(f"        URL: {site.get('webUrl')}")
                elif response.status == 403:
                    print(f"   ❌ Cannot list sites - insufficient permissions")
                else:
                    error_text = await response.text()
                    print(f"   ❌ Sites listing failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"   ❌ Sites listing error: {e}")

if __name__ == "__main__":
    asyncio.run(test_site_access())