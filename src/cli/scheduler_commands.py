"""
CLI Commands for Scheduler Management
"""

import click
import asyncio
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@click.group()
def scheduler():
    """Scheduler management commands."""
    pass

@scheduler.command()
def start():
    """Start the config-based scheduler service."""
    
    async def _start_scheduler():
        try:
            from ..scheduling.config_scheduler import start_scheduler_service
            
            console.print(Panel.fit(
                "[bold green]Starting Config-Based Scheduler[/bold green]",
                border_style="green"
            ))
            
            console.print("[yellow]🚀 Starting scheduler service...[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            
            # Start the scheduler service
            await start_scheduler_service()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⏹️  Scheduler stopped by user[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Scheduler failed: {e}[/red]")
            raise click.ClickException(str(e))
    
    asyncio.run(_start_scheduler())

@scheduler.command()
def stop():
    """Stop the scheduler service."""
    
    async def _stop_scheduler():
        try:
            from ..scheduling.config_scheduler import stop_scheduler_service
            
            console.print("[yellow]⏹️  Stopping scheduler service...[/yellow]")
            stop_scheduler_service()
            console.print("[green]✅ Scheduler stopped[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Failed to stop scheduler: {e}[/red]")
            raise click.ClickException(str(e))
    
    asyncio.run(_stop_scheduler())

@scheduler.command()
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), 
              help='Output format')
def status(output_format):
    """Show scheduler status and active schedules."""
    
    async def _show_status():
        try:
            from ..scheduling.config_scheduler import get_scheduler
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Getting scheduler status...", total=None)
                
                scheduler = await get_scheduler()
                status_info = scheduler.get_schedule_status()
                
                progress.update(task, description="Formatting status report...")
                
                if output_format == 'json':
                    # JSON output for API integration
                    status_dict = {
                        'scheduler_running': status_info['running'],
                        'active_schedules': status_info['active_schedules'],
                        'pending_executions': status_info['pending_executions'],
                        'running_executions': status_info['running_executions'],
                        'schedules': status_info['schedules'],
                        'generated_at': datetime.utcnow().isoformat()
                    }
                    
                    console.print(json.dumps(status_dict, indent=2, default=str))
                    
                else:
                    # Rich table output for human consumption
                    await _display_scheduler_status(status_info)
            
        except Exception as e:
            console.print(f"[red]❌ Failed to get scheduler status: {e}[/red]")
            raise click.ClickException(str(e))
    
    asyncio.run(_show_status())

@scheduler.command()
@click.option('--config-name', '-c', help='Filter by specific configuration name')
@click.option('--status-filter', type=click.Choice(['pending', 'running', 'completed', 'failed']),
              help='Filter by execution status')
@click.option('--limit', '-l', default=20, help='Maximum number of executions to show')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), 
              help='Output format')
def executions(config_name, status_filter, limit, output_format):
    """Show recent scheduled executions."""
    
    async def _show_executions():
        try:
            from ..scheduling.config_scheduler import get_scheduler
            
            scheduler = await get_scheduler()
            
            # Filter executions
            filtered_executions = []
            for exec_id, execution in scheduler.executions.items():
                if config_name and execution.config_name != config_name:
                    continue
                if status_filter and execution.status != status_filter:
                    continue
                filtered_executions.append(execution)
            
            # Sort by scheduled time (most recent first)
            filtered_executions.sort(key=lambda x: x.scheduled_time, reverse=True)
            filtered_executions = filtered_executions[:limit]
            
            if output_format == 'json':
                # JSON output
                executions_data = []
                for execution in filtered_executions:
                    exec_data = {
                        'execution_id': execution.execution_id,
                        'config_name': execution.config_name,
                        'scheduled_time': execution.scheduled_time.isoformat(),
                        'status': execution.status,
                        'started_at': execution.started_at.isoformat() if execution.started_at else None,
                        'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                        'error_message': execution.error_message
                    }
                    executions_data.append(exec_data)
                
                result = {
                    'executions': executions_data,
                    'total_count': len(filtered_executions),
                    'filters': {
                        'config_name': config_name,
                        'status': status_filter,
                        'limit': limit
                    },
                    'generated_at': datetime.utcnow().isoformat()
                }
                
                console.print(json.dumps(result, indent=2, default=str))
                
            else:
                # Rich table output
                await _display_executions(filtered_executions, config_name, status_filter)
            
        except Exception as e:
            console.print(f"[red]❌ Failed to get executions: {e}[/red]")
            raise click.ClickException(str(e))
    
    asyncio.run(_show_executions())

@scheduler.command()
@click.argument('config_name')
@click.option('--force', is_flag=True, help='Force execution even if one is already running')
def trigger(config_name, force):
    """Manually trigger a scheduled sync for a configuration."""
    
    async def _trigger_sync():
        try:
            from ..scheduling.config_scheduler import get_scheduler
            from datetime import datetime
            import uuid
            
            scheduler = await get_scheduler()
            
            # Check if config exists in scheduler
            if config_name not in scheduler.schedules:
                # Try to reload schedules first
                await scheduler.load_schedules_from_configs()
                
                if config_name not in scheduler.schedules:
                    console.print(f"[red]❌ Configuration '{config_name}' not found in active schedules[/red]")
                    console.print("[yellow]💡 Available configurations:[/yellow]")
                    for name in scheduler.schedules.keys():
                        console.print(f"  - {name}")
                    return
            
            # Check if already running (unless forced)
            if not force:
                for execution in scheduler.executions.values():
                    if execution.config_name == config_name and execution.status == "running":
                        console.print(f"[yellow]⚠️  Sync already running for '{config_name}'[/yellow]")
                        console.print(f"   Execution ID: {execution.execution_id}")
                        console.print(f"   Started: {execution.started_at}")
                        console.print("[dim]Use --force to override[/dim]")
                        return
            
            console.print(f"[yellow]🚀 Triggering manual sync for '{config_name}'...[/yellow]")
            
            # Create manual execution
            schedule = scheduler.schedules[config_name]
            current_time = datetime.now()
            
            await scheduler._schedule_execution(config_name, schedule, current_time)
            
            console.print(f"[green]✅ Manual sync triggered for '{config_name}'[/green]")
            console.print("[dim]Use 'scheduler executions' to monitor progress[/dim]")
            
        except Exception as e:
            console.print(f"[red]❌ Failed to trigger sync: {e}[/red]")
            raise click.ClickException(str(e))
    
    asyncio.run(_trigger_sync())

@scheduler.command()
def reload():
    """Reload scheduler configurations from the database."""
    
    async def _reload_configs():
        try:
            from ..scheduling.config_scheduler import get_scheduler
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Reloading configurations...", total=None)
                
                scheduler = await get_scheduler()
                old_count = len(scheduler.schedules)
                
                await scheduler.load_schedules_from_configs()
                new_count = len(scheduler.schedules)
                
                progress.update(task, description="Configuration reload complete")
            
            console.print(f"[green]✅ Configurations reloaded[/green]")
            console.print(f"   Previous count: {old_count}")
            console.print(f"   Current count: {new_count}")
            
            if new_count != old_count:
                console.print(f"   [yellow]Change: {new_count - old_count:+d} configurations[/yellow]")
            
        except Exception as e:
            console.print(f"[red]❌ Failed to reload configurations: {e}[/red]")
            raise click.ClickException(str(e))
    
    asyncio.run(_reload_configs())

@scheduler.command()
@click.argument('config_name')
def schedule_info(config_name):
    """Show detailed schedule information for a configuration."""
    
    async def _show_schedule_info():
        try:
            from ..scheduling.config_scheduler import get_scheduler
            
            scheduler = await get_scheduler()
            
            if config_name not in scheduler.schedules:
                await scheduler.load_schedules_from_configs()
                
                if config_name not in scheduler.schedules:
                    console.print(f"[red]❌ Configuration '{config_name}' not found in schedules[/red]")
                    return
            
            schedule = scheduler.schedules[config_name]
            
            # Create info panel
            info_text = f"""[bold green]{schedule.config_name}[/bold green]

[bold]Schedule Configuration:[/bold]
Enabled: [{'green' if schedule.enabled else 'red'}]{'✅ Yes' if schedule.enabled else '❌ No'}[/{'green' if schedule.enabled else 'red'}]
Frequency: [blue]{schedule.frequency}[/blue]
Time: [yellow]{schedule.time or 'N/A'}[/yellow]
Timezone: [cyan]{schedule.timezone}[/cyan]
Max Duration: [yellow]{schedule.max_duration_hours} hours[/yellow]
Retry Attempts: [yellow]{schedule.retry_attempts}[/yellow]

[bold]Next Execution:[/bold]
{scheduler._calculate_next_execution(schedule) or '[dim]Not scheduled[/dim]'}

[bold]Notifications:[/bold]
{', '.join(schedule.notification_emails) if schedule.notification_emails else '[dim]None configured[/dim]'}"""

            if schedule.cron_expression:
                info_text += f"\n\n[bold]Cron Expression:[/bold]\n[yellow]{schedule.cron_expression}[/yellow]"
            
            console.print(Panel(info_text, title="Schedule Information", expand=False))
            
            # Show recent executions for this config
            recent_executions = [
                exec for exec in scheduler.executions.values() 
                if exec.config_name == config_name
            ]
            recent_executions.sort(key=lambda x: x.scheduled_time, reverse=True)
            recent_executions = recent_executions[:5]
            
            if recent_executions:
                console.print(f"\n[bold]Recent Executions (last 5):[/bold]")
                exec_table = Table()
                exec_table.add_column("Time", style="yellow")
                exec_table.add_column("Status", style="white", justify="center")
                exec_table.add_column("Duration", style="blue")
                exec_table.add_column("Error", style="red")
                
                for execution in recent_executions:
                    time_str = execution.scheduled_time.strftime("%Y-%m-%d %H:%M")
                    status = _get_status_icon(execution.status)
                    
                    duration = "N/A"
                    if execution.started_at and execution.completed_at:
                        delta = execution.completed_at - execution.started_at
                        duration = f"{delta.total_seconds():.1f}s"
                    elif execution.started_at:
                        delta = datetime.now() - execution.started_at
                        duration = f"{delta.total_seconds():.1f}s (running)"
                    
                    error = execution.error_message[:50] + "..." if execution.error_message and len(execution.error_message) > 50 else execution.error_message or ""
                    
                    exec_table.add_row(time_str, status, duration, error)
                
                console.print(exec_table)
            else:
                console.print(f"\n[dim]No recent executions found for '{config_name}'[/dim]")
            
        except Exception as e:
            console.print(f"[red]❌ Failed to get schedule info: {e}[/red]")
            raise click.ClickException(str(e))
    
    asyncio.run(_show_schedule_info())

async def _display_scheduler_status(status_info):
    """Display scheduler status in rich format."""
    
    # Header
    running_status = "🟢 Running" if status_info['running'] else "🔴 Stopped"
    header = Panel.fit(
        f"[bold cyan]Scheduler Status: {running_status}[/bold cyan]",
        style="bold cyan"
    )
    console.print(header)
    
    # Overview metrics
    overview_table = Table(title="Overview")
    overview_table.add_column("Metric", style="bold")
    overview_table.add_column("Value", justify="right")
    
    overview_table.add_row("Scheduler Status", running_status)
    overview_table.add_row("Active Schedules", str(status_info['active_schedules']))
    overview_table.add_row("Pending Executions", str(status_info['pending_executions']))
    overview_table.add_row("Running Executions", str(status_info['running_executions']))
    
    console.print(overview_table)
    
    # Active schedules
    if status_info['schedules']:
        schedules_table = Table(title="Active Schedules")
        schedules_table.add_column("Configuration", style="green")
        schedules_table.add_column("Frequency", style="blue")
        schedules_table.add_column("Time", style="yellow")
        schedules_table.add_column("Next Execution", style="cyan")
        schedules_table.add_column("Status", style="white", justify="center")
        
        for name, schedule in status_info['schedules'].items():
            status_icon = "✅" if schedule['enabled'] else "⏸️ "
            time_str = schedule['time'] or "N/A"
            next_exec = schedule['next_execution']
            if next_exec:
                try:
                    next_dt = datetime.fromisoformat(next_exec.replace('Z', '+00:00'))
                    next_exec = next_dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            
            schedules_table.add_row(
                name,
                schedule['frequency'],
                time_str,
                next_exec or "N/A",
                status_icon
            )
        
        console.print(schedules_table)
    else:
        console.print("[yellow]No active schedules configured[/yellow]")

async def _display_executions(executions, config_name=None, status_filter=None):
    """Display executions in rich format."""
    
    title = "Scheduled Executions"
    if config_name:
        title += f" for {config_name}"
    if status_filter:
        title += f" ({status_filter})"
    
    if not executions:
        console.print(f"[yellow]No executions found[/yellow]")
        return
    
    # Executions table
    exec_table = Table(title=title)
    exec_table.add_column("Config", style="green")
    exec_table.add_column("Scheduled", style="yellow")
    exec_table.add_column("Status", style="white", justify="center")
    exec_table.add_column("Duration", style="blue")
    exec_table.add_column("Error", style="red")
    
    for execution in executions:
        scheduled_str = execution.scheduled_time.strftime("%Y-%m-%d %H:%M")
        status = _get_status_icon(execution.status)
        
        duration = "N/A"
        if execution.started_at and execution.completed_at:
            delta = execution.completed_at - execution.started_at
            duration = f"{delta.total_seconds():.1f}s"
        elif execution.started_at:
            delta = datetime.now() - execution.started_at
            duration = f"{delta.total_seconds():.1f}s (running)"
        
        error = ""
        if execution.error_message:
            error = execution.error_message[:60] + "..." if len(execution.error_message) > 60 else execution.error_message
        
        exec_table.add_row(
            execution.config_name,
            scheduled_str,
            status,
            duration,
            error
        )
    
    console.print(exec_table)

def _get_status_icon(status: str) -> str:
    """Get a status icon for execution status."""
    icons = {
        "pending": "⏳ Pending",
        "running": "🔄 Running", 
        "completed": "✅ Completed",
        "failed": "❌ Failed"
    }
    return icons.get(status, f"❓ {status}")