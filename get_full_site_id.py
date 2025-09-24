#!/usr/bin/env python3
"""
Get the full site ID for the accessible SharePoint site.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def get_full_site_id():
    """Get the full site ID for div991secb."""
    
    print("🔍 Getting Full Site ID")
    print("=" * 40)
    
    # Get credentials
    tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
    client_id = os.getenv('SHAREPOINT_CLIENT_ID')  
    client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
    
    # Get access token
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=data) as response:
            token_data = await response.json()
            access_token = token_data["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get the site info
        site_url = "https://graph.microsoft.com/v1.0/sites/groupnbg.sharepoint.com:/sites/div991secb"
        
        async with session.get(site_url, headers=headers) as response:
            if response.status == 200:
                site_data = await response.json()
                
                print(f"✅ Site Found:")
                print(f"   Name: {site_data.get('displayName')}")
                print(f"   Description: {site_data.get('description', 'No description')}")
                print(f"   Web URL: {site_data.get('webUrl')}")
                print(f"   Full Site ID: {site_data.get('id')}")
                
                print(f"\n📋 For your config file:")
                print(f'   "site_id": "{site_data.get("id")}"')
                
            else:
                print(f"❌ Failed to get site info: {response.status}")

if __name__ == "__main__":
    asyncio.run(get_full_site_id())