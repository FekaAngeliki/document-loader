"""
CLI Commands for Analytics and Business Metrics
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
# Note: rich.chart is not available in standard rich package
# from rich.chart import Chart

console = Console()

@click.group()
def analytics():
    """Analytics and business metrics commands."""
    pass

@analytics.command()
@click.option('--config-name', '-c', required=True, help='Configuration name')
@click.option('--days', '-d', default=30, help='Analysis period in days')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), 
              help='Output format')
def knowledge_base(config_name, days, output_format):
    """Generate comprehensive analytics for a specific knowledge base."""
    
    async def _generate_analytics():
        try:
            from ..analytics.metrics_engine import create_metrics_engine
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Calculating analytics...", total=None)
                
                # Create metrics engine
                metrics_engine = await create_metrics_engine()
                
                progress.update(task, description="Gathering knowledge base metrics...")
                
                # Calculate metrics
                metrics = await metrics_engine.calculate_kb_metrics(config_name, days)
                
                progress.update(task, description="Generating report...")
                
                if output_format == 'json':
                    # JSON output for API integration
                    metrics_dict = {
                        'config_name': metrics.config_name,
                        'kb_name': metrics.kb_name,
                        'reporting_period_days': days,
                        'generated_at': datetime.utcnow().isoformat(),
                        'document_metrics': {
                            'total_documents': metrics.total_documents,
                            'new_documents_30d': metrics.new_documents_30d,
                            'updated_documents_30d': metrics.updated_documents_30d,
                            'deleted_documents_30d': metrics.deleted_documents_30d
                        },
                        'performance_metrics': {
                            'total_syncs': metrics.total_syncs,
                            'successful_syncs': metrics.successful_syncs,
                            'failed_syncs': metrics.failed_syncs,
                            'success_rate_percentage': metrics.success_rate_percentage,
                            'avg_sync_duration_minutes': metrics.avg_sync_duration_minutes,
                            'last_sync_time': metrics.last_sync_time.isoformat() if metrics.last_sync_time else None
                        },
                        'storage_metrics': {
                            'total_size_gb': metrics.total_size_gb,
                            'avg_document_size_kb': metrics.avg_document_size_kb,
                            'cost_estimate_usd': metrics.cost_estimate_usd
                        },
                        'source_breakdown': {
                            'document_counts': metrics.source_document_counts,
                            'success_rates': metrics.source_success_rates
                        },
                        'trends': {
                            'documents_trend_7d': metrics.documents_trend_7d,
                            'sync_performance_trend_7d': metrics.sync_performance_trend_7d
                        },
                        'error_analysis': {
                            'common_errors': metrics.common_errors,
                            'error_rate_trend': metrics.error_rate_trend
                        }
                    }
                    
                    console.print(json.dumps(metrics_dict, indent=2, default=str))
                    
                else:
                    # Rich table output for human consumption
                    await _display_kb_analytics(metrics, days)
                
                await metrics_engine.db.disconnect()
                
        except Exception as e:
            console.print(f"❌ Analytics generation failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_generate_analytics())

@analytics.command()
@click.option('--days', '-d', default=30, help='Analysis period in days')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), 
              help='Output format')
def business_summary(days, output_format):
    """Generate business-level analytics across all knowledge bases."""
    
    async def _generate_business_analytics():
        try:
            from ..analytics.metrics_engine import create_metrics_engine
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Calculating business analytics...", total=None)
                
                # Create metrics engine
                metrics_engine = await create_metrics_engine()
                
                progress.update(task, description="Gathering global metrics...")
                
                # Calculate business analytics
                analytics = await metrics_engine.calculate_business_analytics(days)
                
                progress.update(task, description="Generating business report...")
                
                if output_format == 'json':
                    # JSON output
                    analytics_dict = {
                        'reporting_period_days': analytics.reporting_period_days,
                        'generated_at': analytics.generated_at.isoformat(),
                        'global_metrics': {
                            'total_knowledge_bases': analytics.total_knowledge_bases,
                            'active_knowledge_bases': analytics.active_knowledge_bases,
                            'total_documents': analytics.total_documents,
                            'total_storage_gb': analytics.total_storage_gb
                        },
                        'performance_summary': {
                            'overall_success_rate': analytics.overall_success_rate,
                            'avg_sync_duration_minutes': analytics.avg_sync_duration_minutes,
                            'total_sync_operations': analytics.total_sync_operations
                        },
                        'cost_analysis': {
                            'total_estimated_cost_usd': analytics.total_estimated_cost_usd,
                            'cost_per_knowledge_base': analytics.cost_per_knowledge_base,
                            'cost_per_document': analytics.cost_per_document
                        },
                        'growth_metrics': {
                            'document_growth_rate': analytics.document_growth_rate,
                            'new_knowledge_bases_30d': analytics.new_knowledge_bases_30d
                        },
                        'top_performers': {
                            'most_active_kb': analytics.most_active_kb,
                            'largest_kb_by_docs': analytics.largest_kb_by_docs,
                            'fastest_sync_kb': analytics.fastest_sync_kb
                        },
                        'issues_summary': {
                            'knowledge_bases_with_issues': analytics.knowledge_bases_with_issues,
                            'total_errors_30d': analytics.total_errors_30d,
                            'top_error_types': analytics.top_error_types
                        }
                    }
                    
                    console.print(json.dumps(analytics_dict, indent=2, default=str))
                    
                else:
                    # Rich display
                    await _display_business_analytics(analytics)
                
                await metrics_engine.db.disconnect()
                
        except Exception as e:
            console.print(f"❌ Business analytics generation failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_generate_business_analytics())

@analytics.command()
@click.option('--config-name', '-c', help='Specific knowledge base (optional)')
@click.option('--days', '-d', default=7, help='Trend period in days')
def trends(config_name, days):
    """Show performance trends and patterns."""
    
    async def _show_trends():
        try:
            from ..analytics.metrics_engine import create_metrics_engine
            
            metrics_engine = await create_metrics_engine()
            
            if config_name:
                # Show trends for specific KB
                metrics = await metrics_engine.calculate_kb_metrics(config_name, days)
                _display_kb_trends(metrics, days)
            else:
                # Show global trends
                analytics = await metrics_engine.calculate_business_analytics(days)
                _display_global_trends(analytics, days)
            
            await metrics_engine.db.disconnect()
            
        except Exception as e:
            console.print(f"❌ Trend analysis failed: {e}")
            raise click.ClickException(str(e))
    
    asyncio.run(_show_trends())

async def _display_kb_analytics(metrics, days):
    """Display knowledge base analytics in rich format."""
    
    # Header
    header = Panel.fit(
        f"📊 Knowledge Base Analytics: {metrics.config_name}",
        style="bold cyan"
    )
    console.print(header)
    
    # Overview metrics
    overview_table = Table(title=f"Overview (Last {days} days)")
    overview_table.add_column("Metric", style="bold")
    overview_table.add_column("Value", justify="right")
    
    overview_table.add_row("Knowledge Base", metrics.kb_name)
    overview_table.add_row("Total Documents", f"{metrics.total_documents:,}")
    overview_table.add_row("New Documents", f"{metrics.new_documents_30d:,}")
    overview_table.add_row("Success Rate", f"{metrics.success_rate_percentage:.1f}%")
    overview_table.add_row("Avg Sync Duration", f"{metrics.avg_sync_duration_minutes:.1f} min")
    overview_table.add_row("Storage Size", f"{metrics.total_size_gb:.2f} GB")
    overview_table.add_row("Estimated Cost", f"${metrics.cost_estimate_usd:.2f}")
    
    # Performance metrics
    perf_table = Table(title="Sync Performance")
    perf_table.add_column("Metric", style="bold")
    perf_table.add_column("Value", justify="right")
    
    perf_table.add_row("Total Syncs", str(metrics.total_syncs))
    perf_table.add_row("Successful", str(metrics.successful_syncs))
    perf_table.add_row("Failed", str(metrics.failed_syncs))
    perf_table.add_row("Uptime", f"{metrics.uptime_percentage:.1f}%")
    if metrics.last_sync_time:
        perf_table.add_row("Last Sync", metrics.last_sync_time.strftime("%Y-%m-%d %H:%M"))
    
    # Source breakdown
    source_table = Table(title="Source Breakdown")
    source_table.add_column("Source", style="bold")
    source_table.add_column("Documents", justify="right")
    source_table.add_column("Success Rate", justify="right")
    
    for source_id, doc_count in metrics.source_document_counts.items():
        success_rate = metrics.source_success_rates.get(source_id, 0)
        source_table.add_row(
            source_id, 
            f"{doc_count:,}", 
            f"{success_rate:.1f}%"
        )
    
    # Display in columns
    console.print(Columns([overview_table, perf_table]))
    console.print(source_table)
    
    # Common errors
    if metrics.common_errors:
        error_table = Table(title="Recent Errors")
        error_table.add_column("Error Message", style="red")
        error_table.add_column("Count", justify="right")
        error_table.add_column("Last Seen", style="dim")
        
        for error in metrics.common_errors[:5]:
            error_table.add_row(
                error['error_message'][:60] + "..." if len(error['error_message']) > 60 else error['error_message'],
                str(error['count']),
                error['last_seen'].strftime("%Y-%m-%d") if error.get('last_seen') else "N/A"
            )
        
        console.print(error_table)

async def _display_business_analytics(analytics):
    """Display business analytics in rich format."""
    
    # Header
    header = Panel.fit(
        f"🏢 Business Analytics Summary ({analytics.reporting_period_days} days)",
        style="bold green"
    )
    console.print(header)
    
    # Global overview
    global_table = Table(title="Global Overview")
    global_table.add_column("Metric", style="bold")
    global_table.add_column("Value", justify="right")
    
    global_table.add_row("Knowledge Bases", f"{analytics.total_knowledge_bases:,}")
    global_table.add_row("Active KBs", f"{analytics.active_knowledge_bases:,}")
    global_table.add_row("Total Documents", f"{analytics.total_documents:,}")
    global_table.add_row("Total Storage", f"{analytics.total_storage_gb:.2f} GB")
    global_table.add_row("Overall Success Rate", f"{analytics.overall_success_rate:.1f}%")
    
    # Cost analysis
    cost_table = Table(title="Cost Analysis")
    cost_table.add_column("Metric", style="bold")
    cost_table.add_column("Value", justify="right")
    
    cost_table.add_row("Total Cost", f"${analytics.total_estimated_cost_usd:.2f}")
    cost_table.add_row("Cost per KB", f"${analytics.cost_per_knowledge_base:.2f}")
    cost_table.add_row("Cost per Document", f"${analytics.cost_per_document:.4f}")
    
    # Growth metrics
    growth_table = Table(title="Growth Metrics")
    growth_table.add_column("Metric", style="bold")
    growth_table.add_column("Value", justify="right")
    
    growth_table.add_row("Document Growth Rate", f"{analytics.document_growth_rate:.1f}%")
    growth_table.add_row("New KBs (30d)", str(analytics.new_knowledge_bases_30d))
    
    console.print(Columns([global_table, cost_table, growth_table]))
    
    # Top performers
    performers_table = Table(title="Top Performers")
    performers_table.add_column("Category", style="bold")
    performers_table.add_column("Knowledge Base", style="cyan")
    
    performers_table.add_row("Most Active", analytics.most_active_kb)
    performers_table.add_row("Largest (by docs)", analytics.largest_kb_by_docs)
    performers_table.add_row("Fastest Sync", analytics.fastest_sync_kb)
    
    # Issues summary
    issues_table = Table(title="Issues Summary")
    issues_table.add_column("Metric", style="bold")
    issues_table.add_column("Value", justify="right")
    
    issues_table.add_row("KBs with Issues", str(analytics.knowledge_bases_with_issues))
    issues_table.add_row("Total Errors (30d)", str(analytics.total_errors_30d))
    
    console.print(Columns([performers_table, issues_table]))
    
    # Top error types
    if analytics.top_error_types:
        error_table = Table(title="Top Error Types")
        error_table.add_column("Error Type", style="red")
        error_table.add_column("Count", justify="right")
        
        for error in analytics.top_error_types:
            error_table.add_row(
                error['error_type'][:50] + "..." if len(error['error_type']) > 50 else error['error_type'],
                str(error['count'])
            )
        
        console.print(error_table)

def _display_kb_trends(metrics, days):
    """Display knowledge base trends."""
    
    console.print(Panel.fit(f"📈 Trends for {metrics.config_name} (Last {days} days)", style="bold magenta"))
    
    # Document trend
    doc_trend_table = Table(title="Document Processing Trend")
    doc_trend_table.add_column("Day", justify="center")
    for i, count in enumerate(metrics.documents_trend_7d):
        doc_trend_table.add_column(f"Day {i+1}", justify="center")
    
    doc_row = ["Documents"]
    for count in metrics.documents_trend_7d:
        doc_row.append(str(count))
    doc_trend_table.add_row(*doc_row)
    
    # Sync performance trend
    sync_trend_table = Table(title="Sync Performance Trend (minutes)")
    sync_trend_table.add_column("Metric", justify="center")
    for i in range(len(metrics.sync_performance_trend_7d)):
        sync_trend_table.add_column(f"Day {i+1}", justify="center")
    
    sync_row = ["Avg Duration"]
    for duration in metrics.sync_performance_trend_7d:
        sync_row.append(f"{duration:.1f}")
    sync_trend_table.add_row(*sync_row)
    
    console.print(doc_trend_table)
    console.print(sync_trend_table)

def _display_global_trends(analytics, days):
    """Display global system trends."""
    
    console.print(Panel.fit(f"📈 Global System Trends (Last {days} days)", style="bold magenta"))
    
    # Simple trend display
    trend_table = Table(title="System Performance Overview")
    trend_table.add_column("Metric", style="bold")
    trend_table.add_column("Value", justify="right")
    
    trend_table.add_row("Document Growth Rate", f"{analytics.document_growth_rate:.1f}%")
    trend_table.add_row("Overall Success Rate", f"{analytics.overall_success_rate:.1f}%")
    trend_table.add_row("Avg Sync Duration", f"{analytics.avg_sync_duration_minutes:.1f} min")
    trend_table.add_row("Total Operations", str(analytics.total_sync_operations))
    
    console.print(trend_table)