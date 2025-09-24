#!/usr/bin/env python3
"""
Detailed SharePoint Discovery Tool

Discovers SharePoint sites, their document libraries, and sample files.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich import box

load_dotenv()

console = Console()

async def detailed_sharepoint_discovery():
    """Detailed discovery of SharePoint sites, libraries, and files."""
    
    console.print("\n[bold cyan]🔍 Detailed SharePoint Discovery[/bold cyan]")
    console.print("=" * 70)
    
    # Get credentials
    tenant_id = os.getenv('SHAREPOINT_TENANT_ID')
    client_id = os.getenv('SHAREPOINT_CLIENT_ID')  
    client_secret = os.getenv('SHAREPOINT_CLIENT_SECRET')
    
    if not all([tenant_id, client_id, client_secret]):
        console.print("[red]❌ Missing SharePoint credentials in .env file[/red]")
        return
    
    # Get access token
    console.print("[yellow]🔑 Getting access token...[/yellow]")
    
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
        
        # Discover sites using multiple methods
        console.print("\n[yellow]🌐 Discovering accessible sites...[/yellow]")
        sites_found = await discover_sites(session, headers)
        
        if not sites_found:
            console.print("[red]❌ No accessible SharePoint sites found[/red]")
            return
        
        console.print(f"[green]✅ Found {len(sites_found)} accessible sites[/green]")
        
        # For each site, get detailed information
        for i, site in enumerate(sites_found, 1):
            await analyze_site_details(session, headers, site, i, len(sites_found))


async def discover_sites(session, headers):
    """Discover accessible SharePoint sites."""
    sites_found = []
    
    # Method 1: Try known site patterns
    known_patterns = [
        "/sites/NBGInternalAuditDivision",
        "/sites/div991secb", 
        "/sites/premium",
        "/sites/audit",
        "/sites/finance",
        "/sites/hr",
        "/sites/legal",
        "/sites/compliance"
    ]
    
    for pattern in known_patterns:
        try:
            site_url = f"https://graph.microsoft.com/v1.0/sites/groupnbg.sharepoint.com:{pattern}"
            async with session.get(site_url, headers=headers) as response:
                if response.status == 200:
                    site_data = await response.json()
                    # Add if not already found
                    if not any(s.get('id') == site_data.get('id') for s in sites_found):
                        sites_found.append(site_data)
        except Exception:
            pass
    
    # Method 2: Try to list sites (if you have broad permissions)
    try:
        sites_url = "https://graph.microsoft.com/v1.0/sites?$top=20"
        async with session.get(sites_url, headers=headers) as response:
            if response.status == 200:
                sites_data = await response.json()
                sites = sites_data.get('value', [])
                for site in sites:
                    if not any(s.get('id') == site.get('id') for s in sites_found):
                        sites_found.append(site)
    except Exception:
        pass
    
    return sites_found


async def analyze_site_details(session, headers, site, site_num, total_sites):
    """Analyze detailed information for a specific site."""
    
    site_name = site.get('displayName', 'Unknown')
    site_id = site.get('id', 'Unknown')
    web_url = site.get('webUrl', 'Unknown')
    
    console.print(f"\n[bold blue]📊 Site {site_num}/{total_sites}: {site_name}[/bold blue]")
    console.print(f"[dim]Site ID: {site_id}[/dim]")
    console.print(f"[dim]Web URL: {web_url}[/dim]")
    
    # Create a tree structure for this site
    site_tree = Tree(f"[bold cyan]{site_name}[/bold cyan]")
    
    try:
        # Get document libraries (drives)
        console.print("[yellow]  📁 Getting document libraries...[/yellow]")
        drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        
        async with session.get(drives_url, headers=headers) as response:
            if response.status == 200:
                drives_data = await response.json()
                drives = drives_data.get('value', [])
                
                console.print(f"[green]  ✅ Found {len(drives)} document libraries[/green]")
                
                for drive in drives[:3]:  # Limit to first 3 drives
                    drive_name = drive.get('name', 'Unknown')
                    drive_id = drive.get('id', 'Unknown')
                    
                    drive_branch = site_tree.add(f"[green]📁 {drive_name}[/green] [dim](ID: {drive_id[:20]}...)[/dim]")
                    
                    # Get sample files from this drive
                    await get_sample_files(session, headers, site_id, drive_id, drive_branch)
                
            else:
                site_tree.add("[red]❌ Cannot access document libraries[/red]")
                console.print(f"[red]  ❌ Failed to get document libraries: {response.status}[/red]")
    
    except Exception as e:
        site_tree.add(f"[red]❌ Error: {str(e)[:50]}...[/red]")
        console.print(f"[red]  ❌ Error analyzing site: {e}[/red]")
    
    # Display the tree
    console.print(site_tree)
    
    # Create a summary table for this site
    table = Table(title=f"Configuration for {site_name}", box=box.SIMPLE)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("site_id", site_id)
    table.add_row("site_url", web_url)
    table.add_row("site_name", site_name)
    
    console.print(table)


async def get_sample_files(session, headers, site_id, drive_id, drive_branch):
    """Get sample files from a document library."""
    
    try:
        # Get root files
        files_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$top=10"
        
        async with session.get(files_url, headers=headers) as response:
            if response.status == 200:
                files_data = await response.json()
                items = files_data.get('value', [])
                
                file_count = 0
                folder_count = 0
                
                for item in items[:8]:  # Limit to first 8 items
                    item_name = item.get('name', 'Unknown')
                    item_size = item.get('size', 0)
                    
                    if 'file' in item:
                        file_count += 1
                        # Check if it has a download URL
                        download_url = item.get('@microsoft.graph.downloadUrl')
                        download_status = "✅ Downloadable" if download_url else "❌ No download URL"
                        
                        size_str = f"{item_size:,} bytes" if item_size > 0 else "0 bytes"
                        file_type = item.get('file', {}).get('mimeType', 'unknown')
                        
                        drive_branch.add(f"[blue]📄 {item_name}[/blue] [dim]({size_str}) {download_status}[/dim]")
                        
                    elif 'folder' in item:
                        folder_count += 1
                        child_count = item.get('folder', {}).get('childCount', 0)
                        drive_branch.add(f"[yellow]📁 {item_name}/[/yellow] [dim]({child_count} items)[/dim]")
                
                # Add summary
                if file_count > 0 or folder_count > 0:
                    drive_branch.add(f"[dim]Summary: {file_count} files, {folder_count} folders[/dim]")
                else:
                    drive_branch.add("[dim]No items found[/dim]")
                    
            else:
                drive_branch.add(f"[red]❌ Cannot access files ({response.status})[/red]")
                
    except Exception as e:
        drive_branch.add(f"[red]❌ Error: {str(e)[:30]}...[/red]")


if __name__ == "__main__":
    asyncio.run(detailed_sharepoint_discovery())