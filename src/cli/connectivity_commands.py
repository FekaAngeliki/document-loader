"""
CLI commands for testing connectivity to different RAG systems.
"""
import asyncio
import logging
import sys
from typing import Dict, Any, List, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ..data.database import Database, DatabaseConfig

logger = logging.getLogger(__name__)
console = Console()

# Import RAG implementations with error handling
try:
    from ..implementations.mock_rag_system import MockRAGSystem
except ImportError as e:
    console.print(f"[red]Error importing MockRAGSystem: {e}[/red]")
    sys.exit(1)

try:
    from ..implementations.file_system_storage import FileSystemStorage
except ImportError as e:
    console.print(f"[red]Error importing FileSystemStorage: {e}[/red]")
    sys.exit(1)

# Try to import Azure implementation, handle gracefully if not available
try:
    from ..implementations.azure_blob_rag_system import AzureBlobRAGSystem
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    AzureBlobRAGSystem = None

# RAG system registry
RAG_SYSTEMS = {
    'mock': {
        'class': MockRAGSystem,
        'name': 'Mock RAG System',
        'description': 'In-memory mock system for testing',
        'required_config': []
    },
    'file_system_storage': {
        'class': FileSystemStorage,
        'name': 'File System Storage',
        'description': 'Local file system storage with metadata',
        'required_config': [
            'storage_path'
        ]
    }
}

# Add Azure support if available
if AZURE_AVAILABLE:
    RAG_SYSTEMS['azure_blob'] = {
        'class': AzureBlobRAGSystem,
        'name': 'Azure Blob Storage',
        'description': 'Azure Blob Storage with Azure Search integration',
        'required_config': [
            'azure_tenant_id',
            'azure_subscription_id', 
            'azure_client_id',
            'azure_client_secret',
            'azure_resource_group_name',
            'azure_storage_account_name',
            'azure_storage_container_name'
        ]
    }

@click.group()
def connectivity():
    """Test connectivity to RAG systems."""
    pass

@connectivity.command()
@click.option('--rag-type', type=click.Choice(list(RAG_SYSTEMS.keys())), 
              help='RAG system type to test')
@click.option('--database-name', help='PostgreSQL database name (overrides default)')
@click.option('--interactive/--no-interactive', default=True, 
              help='Interactive mode for parameter input')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def check(rag_type: Optional[str], database_name: Optional[str], interactive: bool, verbose: bool):
    """Test connectivity to a selected RAG system."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    try:
        asyncio.run(_check_connectivity(rag_type, database_name, interactive, verbose))
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)

async def _check_connectivity(rag_type: Optional[str], database_name: Optional[str], 
                            interactive: bool, verbose: bool):
    """Main connectivity checking logic."""
    
    # Display header
    console.print(Panel.fit(
        "[bold blue]RAG System Connectivity Checker[/bold blue]\n"
        "Test connectivity to different RAG implementations",
        border_style="blue"
    ))
    
    # Select RAG type if not provided
    if not rag_type:
        rag_type = await _select_rag_type(interactive)
    
    rag_info = RAG_SYSTEMS[rag_type]
    console.print(f"\n[bold]Testing: {rag_info['name']}[/bold]")
    console.print(f"Description: {rag_info['description']}")
    
    # Test database connectivity first
    await _test_database_connectivity(database_name, verbose)
    
    # Get RAG configuration
    config = await _get_rag_configuration(rag_type, interactive, verbose)
    
    # Test RAG system connectivity
    await _test_rag_connectivity(rag_type, config, verbose)
    
    # Run comprehensive tests
    await _run_comprehensive_tests(rag_type, config, verbose)
    
    console.print("\n[bold green]✅ All connectivity tests completed![/bold green]")

async def _select_rag_type(interactive: bool) -> str:
    """Select RAG type interactively or show options."""
    if not interactive:
        console.print("[red]Error: --rag-type is required in non-interactive mode[/red]")
        sys.exit(1)
    
    console.print("\n[bold]Available RAG Systems:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description")
    
    for key, info in RAG_SYSTEMS.items():
        table.add_row(key, info['name'], info['description'])
    
    console.print(table)
    
    while True:
        rag_type = console.input("\n[bold]Select RAG type: [/bold]").strip()
        if rag_type in RAG_SYSTEMS:
            return rag_type
        console.print(f"[red]Invalid selection. Choose from: {', '.join(RAG_SYSTEMS.keys())}[/red]")

async def _test_database_connectivity(database_name: Optional[str], verbose: bool):
    """Test PostgreSQL database connectivity."""
    console.print("\n[bold]Testing Database Connectivity...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Connecting to PostgreSQL...", total=None)
        
        try:
            # Use custom database name if provided, otherwise use default
            config = DatabaseConfig(database_name) if database_name else DatabaseConfig()
            if verbose:
                console.print(f"[dim]Using database: {config.database}[/dim]")
            
            # Test connection
            db = Database(config)
            await db.connect()
            
            # Test a simple query
            result = await db.fetchval("SELECT 1")
            if result == 1:
                progress.update(task, description="✅ Database connection successful")
                await asyncio.sleep(0.5)  # Brief pause to show success
            else:
                raise Exception("Unexpected query result")
            
            # Clean up connection
            await db.disconnect()
                
        except Exception as e:
            progress.update(task, description="❌ Database connection failed")
            await asyncio.sleep(0.5)
            console.print(f"[red]Database Error: {e}[/red]")
            if verbose:
                console.print_exception()
            raise

async def _get_rag_configuration(rag_type: str, interactive: bool, verbose: bool) -> Dict[str, Any]:
    """Get configuration for the RAG system."""
    rag_info = RAG_SYSTEMS[rag_type]
    config = {}
    
    if not rag_info['required_config']:
        console.print("[dim]No configuration required for this RAG type[/dim]")
        return config
    
    console.print(f"\n[bold]Configuration for {rag_info['name']}:[/bold]")
    
    if rag_type == 'azure_blob':
        config = await _get_azure_blob_config(interactive, verbose)
    elif rag_type == 'file_system_storage':
        config = await _get_file_system_config(interactive, verbose)
    
    return config

async def _get_azure_blob_config(interactive: bool, verbose: bool) -> Dict[str, Any]:
    """Get Azure Blob Storage configuration."""
    if not AZURE_AVAILABLE:
        console.print("[red]Error: Azure Blob Storage is not available (missing dependencies)[/red]")
        console.print("[yellow]Install Azure dependencies to use this RAG type[/yellow]")
        sys.exit(1)
        
    console.print("\n[bold yellow]Azure Blob Storage Configuration[/bold yellow]")
    console.print("Required parameters:")
    
    config = {}
    required_params = RAG_SYSTEMS['azure_blob']['required_config']
    
    if interactive:
        for param in required_params:
            display_name = param.replace('_', ' ').title()
            value = console.input(f"Enter {display_name}: ").strip()
            if value:
                config[param] = value
            else:
                console.print(f"[yellow]Warning: {display_name} not provided[/yellow]")
    else:
        console.print("[red]Error: Interactive mode required for Azure configuration[/red]")
        sys.exit(1)
    
    return config

async def _get_file_system_config(interactive: bool, verbose: bool) -> Dict[str, Any]:
    """Get File System Storage configuration."""
    console.print("\n[bold yellow]File System Storage Configuration[/bold yellow]")
    
    config = {}
    
    if interactive:
        storage_path = console.input("Enter storage path [/tmp/rag_test]: ").strip()
        config['storage_path'] = storage_path or '/tmp/rag_test'
        config['kb_name'] = 'connectivity_test'
        config['create_dirs'] = True
        config['preserve_structure'] = False
        config['metadata_format'] = 'json'
    else:
        # Use defaults for non-interactive mode
        config = {
            'storage_path': '/tmp/rag_test',
            'kb_name': 'connectivity_test',
            'create_dirs': True,
            'preserve_structure': False,
            'metadata_format': 'json'
        }
    
    return config

async def _test_rag_connectivity(rag_type: str, config: Dict[str, Any], verbose: bool):
    """Test basic RAG system connectivity."""
    console.print(f"\n[bold]Testing {RAG_SYSTEMS[rag_type]['name']} Connectivity...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Initializing RAG system...", total=None)
        
        try:
            # Create RAG system instance
            rag_class = RAG_SYSTEMS[rag_type]['class']
            rag_system = rag_class(config)
            
            # Test initialization
            progress.update(task, description="Testing initialization...")
            await rag_system.initialize()
            
            progress.update(task, description="✅ RAG system connectivity successful")
            await asyncio.sleep(0.5)
            
        except Exception as e:
            progress.update(task, description="❌ RAG system connectivity failed")
            await asyncio.sleep(0.5)
            console.print(f"[red]RAG System Error: {e}[/red]")
            if verbose:
                console.print_exception()
            raise

async def _run_comprehensive_tests(rag_type: str, config: Dict[str, Any], verbose: bool):
    """Run comprehensive tests for all RAG system operations."""
    console.print(f"\n[bold]Running Comprehensive Tests...[/bold]")
    
    # Create RAG system instance
    rag_class = RAG_SYSTEMS[rag_type]['class']
    rag_system = rag_class(config)
    await rag_system.initialize()
    
    test_results = {}
    
    # Test 1: Upload Document
    test_results['upload'] = await _test_upload_document(rag_system, verbose)
    
    # Test 2: Get Document
    test_results['get'] = await _test_get_document(rag_system, verbose)
    
    # Test 3: List Documents
    test_results['list'] = await _test_list_documents(rag_system, verbose)
    
    # Test 4: Update Document
    test_results['update'] = await _test_update_document(rag_system, verbose)
    
    # Test 5: Delete Document
    test_results['delete'] = await _test_delete_document(rag_system, verbose)
    
    # Test 6: Cleanup
    test_results['cleanup'] = await _test_cleanup(rag_system, verbose)
    
    # Display results summary
    _display_test_results(test_results)

async def _test_upload_document(rag_system, verbose: bool) -> bool:
    """Test document upload."""
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Testing document upload...", total=None)
            
            test_content = b"Test document content for connectivity check"
            test_filename = "test_connectivity.txt"
            test_metadata = {
                'kb_name': 'connectivity_test',
                'original_uri': '/test/connectivity.txt',
                'test_purpose': 'connectivity_check'
            }
            
            uri = await rag_system.upload_document(test_content, test_filename, test_metadata)
            progress.update(task, description="✅ Document upload successful")
            
            if verbose:
                console.print(f"[dim]Uploaded to: {uri}[/dim]")
            
            # Store URI for other tests
            rag_system._test_uri = uri
            return True
            
    except Exception as e:
        console.print(f"[red]Upload test failed: {e}[/red]")
        return False

async def _test_get_document(rag_system, verbose: bool) -> bool:
    """Test document retrieval."""
    try:
        if not hasattr(rag_system, '_test_uri'):
            console.print("[yellow]Skipping get test - no uploaded document[/yellow]")
            return False
            
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Testing document retrieval...", total=None)
            
            doc_metadata = await rag_system.get_document(rag_system._test_uri)
            
            if doc_metadata:
                progress.update(task, description="✅ Document retrieval successful")
                if verbose:
                    console.print(f"[dim]Retrieved: {doc_metadata.name} ({doc_metadata.size} bytes)[/dim]")
                return True
            else:
                progress.update(task, description="❌ Document not found")
                return False
                
    except Exception as e:
        console.print(f"[red]Get test failed: {e}[/red]")
        return False

async def _test_list_documents(rag_system, verbose: bool) -> bool:
    """Test document listing."""
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Testing document listing...", total=None)
            
            documents = await rag_system.list_documents()
            progress.update(task, description="✅ Document listing successful")
            
            if verbose:
                console.print(f"[dim]Found {len(documents)} documents[/dim]")
            
            return True
            
    except Exception as e:
        console.print(f"[red]List test failed: {e}[/red]")
        return False

async def _test_update_document(rag_system, verbose: bool) -> bool:
    """Test document update."""
    try:
        if not hasattr(rag_system, '_test_uri'):
            console.print("[yellow]Skipping update test - no uploaded document[/yellow]")
            return False
            
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Testing document update...", total=None)
            
            updated_content = b"Updated test document content"
            updated_metadata = {
                'kb_name': 'connectivity_test',
                'original_uri': '/test/connectivity.txt',
                'test_purpose': 'connectivity_check_updated'
            }
            
            await rag_system.update_document(rag_system._test_uri, updated_content, updated_metadata)
            progress.update(task, description="✅ Document update successful")
            
            return True
            
    except Exception as e:
        console.print(f"[red]Update test failed: {e}[/red]")
        return False

async def _test_delete_document(rag_system, verbose: bool) -> bool:
    """Test document deletion."""
    try:
        if not hasattr(rag_system, '_test_uri'):
            console.print("[yellow]Skipping delete test - no uploaded document[/yellow]")
            return False
            
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Testing document deletion...", total=None)
            
            await rag_system.delete_document(rag_system._test_uri)
            progress.update(task, description="✅ Document deletion successful")
            
            return True
            
    except Exception as e:
        console.print(f"[red]Delete test failed: {e}[/red]")
        return False

async def _test_cleanup(rag_system, verbose: bool) -> bool:
    """Test system cleanup."""
    try:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Testing system cleanup...", total=None)
            
            await rag_system.cleanup()
            progress.update(task, description="✅ System cleanup successful")
            
            return True
            
    except Exception as e:
        console.print(f"[red]Cleanup test failed: {e}[/red]")
        return False

def _display_test_results(results: Dict[str, bool]):
    """Display a summary of test results."""
    console.print("\n[bold]Test Results Summary:[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Test", style="cyan")
    table.add_column("Status", justify="center")
    
    for test_name, success in results.items():
        status = "[green]✅ PASS[/green]" if success else "[red]❌ FAIL[/red]"
        table.add_row(test_name.title(), status)
    
    console.print(table)
    
    # Overall result
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    if passed_tests == total_tests:
        console.print(f"\n[bold green]All {total_tests} tests passed! 🎉[/bold green]")
    else:
        console.print(f"\n[bold yellow]{passed_tests}/{total_tests} tests passed[/bold yellow]")