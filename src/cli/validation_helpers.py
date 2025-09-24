"""
CLI validation helpers for knowledge base and database operations.

Provides utility functions to validate user input before executing
create-kb and create-db operations.
"""

import json
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from ..data.validators import (
    validate_kb_creation, 
    validate_db_creation, 
    ValidationResult,
    ValidationError
)
from ..data.repository import Repository
from ..utils.config_utils import load_config_with_env_expansion
from ..data.database import DatabaseConfig


console = Console()


def display_validation_results(result: ValidationResult, operation: str) -> bool:
    """
    Display validation results to the user.
    
    Args:
        result: ValidationResult object with errors and warnings
        operation: Name of the operation being validated
        
    Returns:
        bool: True if validation passed (no errors), False otherwise
    """
    if result.errors:
        console.print(f"\n[red]❌ {operation} validation failed:[/red]")
        
        error_table = Table(show_header=True, header_style="bold red")
        error_table.add_column("Field", style="cyan", no_wrap=True)
        error_table.add_column("Error", style="red")
        
        for error in result.errors:
            error_table.add_row(error.field, error.message)
        
        console.print(error_table)
        console.print(f"\n[red]Please fix the above errors before proceeding.[/red]")
        return False
    
    if result.warnings:
        console.print(f"\n[yellow]⚠️  {operation} validation warnings:[/yellow]")
        
        warning_table = Table(show_header=True, header_style="bold yellow")
        warning_table.add_column("Field", style="cyan", no_wrap=True)
        warning_table.add_column("Warning", style="yellow")
        
        for warning in result.warnings:
            warning_table.add_row(warning.field, warning.message)
        
        console.print(warning_table)
    
    if not result.errors and not result.warnings:
        console.print(f"[green]✅ {operation} validation passed successfully.[/green]")
    elif not result.errors:
        console.print(f"[green]✅ {operation} validation passed with warnings.[/green]")
    
    return True


async def validate_and_confirm_kb_creation(
    name: str, 
    source_type: str, 
    source_config: str, 
    rag_type: str, 
    rag_config: str,
    repository: Repository,
    force: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Validate knowledge base creation parameters and get user confirmation.
    
    Args:
        name: Knowledge base name
        source_type: Source type identifier
        source_config: JSON string with source configuration
        rag_type: RAG type identifier
        rag_config: JSON string with RAG configuration
        repository: Repository instance for validation
        force: Skip validation if True
        
    Returns:
        Dict with parsed configuration if validation passes, None otherwise
    """
    # Parse configurations
    try:
        source_config_dict = json.loads(source_config)
        rag_config_dict = json.loads(rag_config)
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Error parsing JSON configuration: {e}[/red]")
        return None
    
    # Build knowledge base configuration
    kb_config = {
        "name": name,
        "description": f"Knowledge Base: {name}",
        "rag_type": rag_type,
        "rag_config": rag_config_dict,
        "sources": [{
            "source_id": f"{source_type}_1",
            "source_type": source_type,
            "source_config": source_config_dict,
            "metadata_tags": {
                "source_system": source_type,
                "created_via": "cli"
            }
        }]
    }
    
    # Skip validation if forced
    if force:
        console.print("[yellow]⚠️  Validation skipped (--force flag used)[/yellow]")
        return kb_config
    
    # Validate configuration
    console.print("\n[cyan]🔍 Validating knowledge base configuration...[/cyan]")
    
    try:
        validation_result = await validate_kb_creation(kb_config, repository)
        
        if not display_validation_results(validation_result, "Knowledge base creation"):
            return None
        
        # Display configuration summary
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            f"[bold]Knowledge Base Configuration Summary[/bold]\n\n"
            f"Name: [green]{name}[/green]\n"
            f"Source Type: [blue]{source_type}[/blue]\n"
            f"RAG Type: [blue]{rag_type}[/blue]\n"
            f"Source Config: [dim]{json.dumps(source_config_dict, indent=2)}[/dim]\n"
            f"RAG Config: [dim]{json.dumps(rag_config_dict, indent=2)}[/dim]",
            title="Configuration Review"
        ))
        
        return kb_config
        
    except Exception as e:
        console.print(f"[red]❌ Validation error: {e}[/red]")
        return None


async def validate_and_confirm_db_creation(
    database_name: str,
    config: DatabaseConfig,
    force: bool = False
) -> bool:
    """
    Validate database creation parameters and get user confirmation.
    
    Args:
        database_name: Name of the database to create
        config: Database configuration
        force: Skip validation if True
        
    Returns:
        bool: True if validation passes and user confirms, False otherwise
    """
    # Skip validation if forced
    if force:
        console.print("[yellow]⚠️  Validation skipped (--force flag used)[/yellow]")
        return True
    
    # Validate database creation
    console.print("\n[cyan]🔍 Validating database creation...[/cyan]")
    
    try:
        validation_result = await validate_db_creation(database_name, config)
        
        if not display_validation_results(validation_result, "Database creation"):
            return False
        
        # Display configuration summary
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            f"[bold]Database Configuration Summary[/bold]\n\n"
            f"Database Name: [green]{database_name}[/green]\n"
            f"Host: [blue]{config.host}[/blue]\n"
            f"Port: [blue]{config.port}[/blue]\n"
            f"User: [blue]{config.user}[/blue]",
            title="Configuration Review"
        ))
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Validation error: {e}[/red]")
        return False


def get_user_confirmation(operation: str, details: str = "") -> bool:
    """
    Get user confirmation for a potentially destructive operation.
    
    Args:
        operation: Description of the operation
        details: Additional details to display
        
    Returns:
        bool: True if user confirms, False otherwise
    """
    console.print(f"\n[yellow]⚠️  You are about to {operation}[/yellow]")
    
    if details:
        console.print(f"[dim]{details}[/dim]")
    
    try:
        confirm = console.input("\n[bold]Do you want to proceed? (y/N): [/bold]")
        return confirm.lower() in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        console.print("\n[red]Operation cancelled.[/red]")
        return False


async def validate_multi_source_kb_config(config_file: str, repository: Repository) -> Optional[Dict[str, Any]]:
    """
    Validate multi-source knowledge base configuration from file.
    
    Args:
        config_file: Path to configuration file
        repository: Repository instance for validation
        
    Returns:
        Dict with configuration if validation passes, None otherwise
    """
    try:
        config = load_config_with_env_expansion(config_file)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        console.print(f"[red]❌ Error reading configuration file: {e}[/red]")
        return None
    
    console.print("\n[cyan]🔍 Validating multi-source knowledge base configuration...[/cyan]")
    
    try:
        validation_result = await validate_kb_creation(config, repository)
        
        if not display_validation_results(validation_result, "Multi-source knowledge base creation"):
            return None
        
        return config
        
    except Exception as e:
        console.print(f"[red]❌ Validation error: {e}[/red]")
        return None