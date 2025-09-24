#!/usr/bin/env python3
"""
Test access to the Premium RMs SharePoint site.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_premium_site():
    """Test the Premium RMs SharePoint site access."""
    
    print("🔍 Testing Premium RMs SharePoint Site")
    print("=" * 50)
    
    # Get credentials
    tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
    client_id = os.getenv('SHAREPOINT_CLIENT_ID')  
    client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
    site_id = "6f63c8f0-aa51-4681-8da5-5d48f6255f69"
    
    print(f"🔑 Testing site: {site_id}")
    
    # Get access token
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
        
        # Test site access
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
                else:
                    error_text = await response.text()
                    print(f"   ❌ Site access failed: {response.status} - {error_text}")
                    return
        except Exception as e:
            print(f"   ❌ Site access error: {e}")
            return
        
        # Test document libraries
        print(f"\n3️⃣ Testing document libraries...")
        
        drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        
        try:
            async with session.get(drives_url, headers=headers) as response:
                if response.status == 200:
                    drives_data = await response.json()
                    drives = drives_data.get('value', [])
                    print(f"   ✅ Found {len(drives)} document libraries:")
                    for drive in drives:
                        print(f"      • {drive.get('name', 'Unknown')} (ID: {drive.get('id', 'Unknown')})")
                else:
                    error_text = await response.text() 
                    print(f"   ❌ Drives access failed: {response.status} - {error_text}")
        except Exception as e:
            print(f"   ❌ Drives access error: {e}")

if __name__ == "__main__":
    asyncio.run(test_premium_site())