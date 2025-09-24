#!/usr/bin/env python3
"""
SharePoint Site Discovery Tool

Discovers SharePoint sites you have access to and shows their site IDs.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

load_dotenv()

console = Console()

async def discover_sharepoint_sites():
    """Discover SharePoint sites and their IDs."""
    
    console.print("\n[bold cyan]🔍 SharePoint Site Discovery[/bold cyan]")
    console.print("=" * 60)
    
    # Get credentials
    tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
    client_id = os.getenv('SHAREPOINT_CLIENT_ID')  
    client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
    
    if not all([tenant_id, client_id, client_secret]):
        console.print("[red]❌ Missing SharePoint credentials in .env file[/red]")
        return
    
    console.print(f"[dim]Using tenant: {tenant_id}[/dim]")
    console.print(f"[dim]Using client: {client_id}[/dim]")
    
    # Step 1: Get access token
    console.print("\n[yellow]🔑 Getting access token...[/yellow]")
    
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
                    console.print("[green]✅ Access token obtained[/green]")
                else:
                    error_text = await response.text()
                    console.print(f"[red]❌ Token request failed: {response.status} - {error_text}[/red]")
                    return
        except Exception as e:
            console.print(f"[red]❌ Token request error: {e}[/red]")
            return
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 2: Try different discovery methods
        sites_found = []
        
        # Method 1: List all sites (if you have broad permissions)
        console.print("\n[yellow]📋 Method 1: Listing all sites...[/yellow]")
        try:
            sites_url = "https://graph.microsoft.com/v1.0/sites?$top=50"
            async with session.get(sites_url, headers=headers) as response:
                if response.status == 200:
                    sites_data = await response.json()
                    sites = sites_data.get('value', [])
                    console.print(f"[green]✅ Found {len(sites)} sites via listing[/green]")
                    sites_found.extend(sites)
                else:
                    console.print(f"[yellow]⚠️  Site listing failed: {response.status} (might not have broad permissions)[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Site listing error: {e}[/yellow]")
        
        # Method 2: Search for sites with different terms
        console.print("\n[yellow]🔍 Method 2: Searching for sites...[/yellow]")
        search_terms = ["NBG", "audit", "premium", "banking", "finance", "hr", "legal", "*"]
        
        for term in search_terms:
            try:
                search_url = f"https://graph.microsoft.com/v1.0/sites?search={term}"
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        search_data = await response.json()
                        found_sites = search_data.get('value', [])
                        if found_sites:
                            console.print(f"[green]✅ Search '{term}': found {len(found_sites)} sites[/green]")
                            # Add only new sites (avoid duplicates)
                            for site in found_sites:
                                if not any(s.get('id') == site.get('id') for s in sites_found):
                                    sites_found.append(site)
                        else:
                            console.print(f"[dim]Search '{term}': no results[/dim]")
                    else:
                        console.print(f"[yellow]⚠️  Search '{term}' failed: {response.status}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Search '{term}' error: {e}[/yellow]")
        
        # Method 3: Try specific site URLs if you know them
        console.print("\n[yellow]🎯 Method 3: Testing known site patterns...[/yellow]")
        known_patterns = [
            "/sites/NBGInternalAuditDivision",
            "/sites/div991secb", 
            "/sites/premium",
            "/sites/audit",
            "/sites/finance",
            "/sites/hr"
        ]
        
        for pattern in known_patterns:
            try:
                site_url = f"https://graph.microsoft.com/v1.0/sites/groupnbg.sharepoint.com:{pattern}"
                async with session.get(site_url, headers=headers) as response:
                    if response.status == 200:
                        site_data = await response.json()
                        console.print(f"[green]✅ Found site at '{pattern}'[/green]")
                        # Add if not already found
                        if not any(s.get('id') == site_data.get('id') for s in sites_found):
                            sites_found.append(site_data)
                    else:
                        console.print(f"[dim]Pattern '{pattern}': not accessible[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Pattern '{pattern}' error: {e}[/yellow]")
        
        # Step 3: Display results
        console.print(f"\n[bold green]📊 Discovery Results: {len(sites_found)} sites found[/bold green]")
        
        if sites_found:
            # Create table
            table = Table(
                title="SharePoint Sites You Can Access", 
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            
            table.add_column("Site Name", style="cyan", width=30)
            table.add_column("Site ID", style="green", width=40)
            table.add_column("Web URL", style="blue", width=50)
            table.add_column("Description", style="dim", width=30)
            
            for site in sites_found:
                site_name = site.get('displayName', 'Unknown')
                site_id = site.get('id', 'Unknown')
                web_url = site.get('webUrl', 'Unknown')
                description = site.get('description', '')
                
                # Truncate long values
                if len(site_name) > 28:
                    site_name = site_name[:25] + "..."
                if len(description) > 28:
                    description = description[:25] + "..."
                if len(web_url) > 48:
                    web_url = web_url[:45] + "..."
                
                table.add_row(site_name, site_id, web_url, description)
            
            console.print(table)
            
            # Step 4: Show how to use the site IDs
            console.print(f"\n[bold yellow]💡 How to use these site IDs:[/bold yellow]")
            console.print("1. Copy a site_id from the table above")
            console.print("2. Update your config file:")
            console.print('[dim]   "site_id": "paste-site-id-here"[/dim]')
            console.print("3. You can also keep the site_url for reference")
            console.print("4. The site_id will bypass permission-restricted site discovery")
            
        else:
            console.print("[red]❌ No accessible SharePoint sites found[/red]")
            console.print("\n[yellow]💡 Possible reasons:[/yellow]")
            console.print("• Your app registration needs SharePoint permissions")
            console.print("• Sites.Read.All or Sites.Selected permission required")
            console.print("• Admin consent may be needed")
            console.print("• Your account may not have access to any sites")


if __name__ == "__main__":
    asyncio.run(discover_sharepoint_sites())