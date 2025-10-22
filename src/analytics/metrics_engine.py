"""
Analytics and Metrics Engine for Knowledge Base Operations

Provides business-oriented analytics, performance metrics, and operational insights
for enterprise knowledge base management.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from decimal import Decimal

from ..data.database import Database


@dataclass
class KnowledgeBaseMetrics:
    """Comprehensive metrics for a knowledge base."""
    config_name: str
    kb_name: str
    
    # Document metrics
    total_documents: int
    new_documents_30d: int
    updated_documents_30d: int
    deleted_documents_30d: int
    
    # Sync performance
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    avg_sync_duration_minutes: float
    last_sync_time: Optional[datetime]
    
    # Source breakdown
    source_document_counts: Dict[str, int]
    source_success_rates: Dict[str, float]
    
    # Storage metrics
    total_size_gb: float
    avg_document_size_kb: float
    
    # Business metrics
    success_rate_percentage: float
    uptime_percentage: float
    cost_estimate_usd: float
    
    # Time-based analytics
    documents_trend_7d: List[int]
    sync_performance_trend_7d: List[float]
    
    # Error analysis
    common_errors: List[Dict[str, Any]]
    error_rate_trend: List[float]


@dataclass
class BusinessAnalytics:
    """High-level business analytics across all knowledge bases."""
    reporting_period_days: int
    generated_at: datetime
    
    # Global metrics
    total_knowledge_bases: int
    active_knowledge_bases: int
    total_documents: int
    total_storage_gb: float
    
    # Performance summary
    overall_success_rate: float
    avg_sync_duration_minutes: float
    total_sync_operations: int
    
    # Cost analysis
    total_estimated_cost_usd: float
    cost_per_knowledge_base: float
    cost_per_document: float
    
    # Growth metrics
    document_growth_rate: float
    new_knowledge_bases_30d: int
    
    # Top performers
    most_active_kb: str
    largest_kb_by_docs: str
    fastest_sync_kb: str
    
    # Issues summary
    knowledge_bases_with_issues: int
    total_errors_30d: int
    top_error_types: List[Dict[str, Any]]


class MetricsEngine:
    """Enterprise analytics and metrics calculation engine."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def calculate_kb_metrics(self, config_name: str, days: int = 30) -> KnowledgeBaseMetrics:
        """Calculate comprehensive metrics for a specific knowledge base."""
        
        # Get knowledge base info
        kb_query = """
        SELECT kb.*, kc.name as config_name
        FROM multi_source_knowledge_base kb
        LEFT JOIN kb_config_files kc ON kb.config_file_id = kc.id
        WHERE kc.name = $1 OR kb.kb_name = $1
        """
        kb_info = await self.db.fetchrow(kb_query, config_name)
        
        if not kb_info:
            raise ValueError(f"Knowledge base not found: {config_name}")
        
        kb_id = kb_info['id']
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Document metrics
        doc_metrics = await self._calculate_document_metrics(kb_id, cutoff_date)
        
        # Sync performance metrics
        sync_metrics = await self._calculate_sync_metrics(kb_id, cutoff_date)
        
        # Source breakdown
        source_metrics = await self._calculate_source_metrics(kb_id, cutoff_date)
        
        # Storage metrics
        storage_metrics = await self._calculate_storage_metrics(kb_id)
        
        # Trend analysis
        trends = await self._calculate_trends(kb_id, days=7)
        
        # Error analysis
        error_analysis = await self._calculate_error_analysis(kb_id, cutoff_date)
        
        return KnowledgeBaseMetrics(
            config_name=kb_info['config_name'] or config_name,
            kb_name=kb_info['kb_name'],
            
            # Document metrics
            total_documents=doc_metrics['total'],
            new_documents_30d=doc_metrics['new'],
            updated_documents_30d=doc_metrics['updated'],
            deleted_documents_30d=doc_metrics['deleted'],
            
            # Sync performance
            total_syncs=sync_metrics['total'],
            successful_syncs=sync_metrics['successful'],
            failed_syncs=sync_metrics['failed'],
            avg_sync_duration_minutes=sync_metrics['avg_duration'],
            last_sync_time=sync_metrics['last_sync'],
            
            # Source breakdown
            source_document_counts=source_metrics['document_counts'],
            source_success_rates=source_metrics['success_rates'],
            
            # Storage metrics
            total_size_gb=storage_metrics['total_gb'],
            avg_document_size_kb=storage_metrics['avg_size_kb'],
            
            # Business metrics
            success_rate_percentage=sync_metrics['success_rate'],
            uptime_percentage=sync_metrics['uptime'],
            cost_estimate_usd=storage_metrics['cost_estimate'],
            
            # Trends
            documents_trend_7d=trends['documents'],
            sync_performance_trend_7d=trends['sync_performance'],
            
            # Error analysis
            common_errors=error_analysis['common_errors'],
            error_rate_trend=error_analysis['error_trend']
        )
    
    async def calculate_business_analytics(self, days: int = 30) -> BusinessAnalytics:
        """Calculate high-level business analytics across all knowledge bases."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Global counts
        global_metrics = await self._calculate_global_metrics(cutoff_date)
        
        # Performance summary
        performance_metrics = await self._calculate_global_performance(cutoff_date)
        
        # Cost analysis
        cost_metrics = await self._calculate_global_costs(cutoff_date)
        
        # Growth metrics
        growth_metrics = await self._calculate_growth_metrics(cutoff_date)
        
        # Top performers
        top_performers = await self._calculate_top_performers(cutoff_date)
        
        # Issues summary
        issues_summary = await self._calculate_issues_summary(cutoff_date)
        
        return BusinessAnalytics(
            reporting_period_days=days,
            generated_at=datetime.utcnow(),
            
            # Global metrics
            total_knowledge_bases=global_metrics['total_kbs'],
            active_knowledge_bases=global_metrics['active_kbs'],
            total_documents=global_metrics['total_docs'],
            total_storage_gb=global_metrics['total_storage'],
            
            # Performance summary
            overall_success_rate=performance_metrics['success_rate'],
            avg_sync_duration_minutes=performance_metrics['avg_duration'],
            total_sync_operations=performance_metrics['total_syncs'],
            
            # Cost analysis
            total_estimated_cost_usd=cost_metrics['total_cost'],
            cost_per_knowledge_base=cost_metrics['cost_per_kb'],
            cost_per_document=cost_metrics['cost_per_doc'],
            
            # Growth metrics
            document_growth_rate=growth_metrics['doc_growth_rate'],
            new_knowledge_bases_30d=growth_metrics['new_kbs'],
            
            # Top performers
            most_active_kb=top_performers['most_active'],
            largest_kb_by_docs=top_performers['largest'],
            fastest_sync_kb=top_performers['fastest'],
            
            # Issues summary
            knowledge_bases_with_issues=issues_summary['kbs_with_issues'],
            total_errors_30d=issues_summary['total_errors'],
            top_error_types=issues_summary['top_errors']
        )
    
    async def _calculate_document_metrics(self, kb_id: int, cutoff_date: datetime) -> Dict[str, int]:
        """Calculate document-related metrics."""
        
        # Total documents
        total_query = """
        SELECT COUNT(*) as total
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE sr.kb_id = $1 AND fr.status = 'success'
        """
        total_result = await self.db.fetchrow(total_query, kb_id)
        
        # New documents in period
        new_query = """
        SELECT COUNT(*) as new_docs
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE sr.kb_id = $1 AND fr.status = 'success' 
        AND fr.first_discovered >= $2
        """
        new_result = await self.db.fetchrow(new_query, kb_id, cutoff_date)
        
        # Updated documents in period
        updated_query = """
        SELECT COUNT(*) as updated_docs
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE sr.kb_id = $1 AND fr.status = 'success'
        AND fr.last_modified >= $2 AND fr.first_discovered < $2
        """
        updated_result = await self.db.fetchrow(updated_query, kb_id, cutoff_date)
        
        return {
            'total': total_result['total'] or 0,
            'new': new_result['new_docs'] or 0,
            'updated': updated_result['updated_docs'] or 0,
            'deleted': 0  # TODO: Implement delete tracking
        }
    
    async def _calculate_sync_metrics(self, kb_id: int, cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate sync performance metrics."""
        
        sync_query = """
        SELECT 
            COUNT(*) as total_syncs,
            COUNT(*) FILTER (WHERE status = 'completed') as successful,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_duration_minutes,
            MAX(completed_at) as last_sync,
            COUNT(*) FILTER (WHERE started_at >= $2) as recent_syncs
        FROM sync_run
        WHERE kb_id = $1
        """
        
        result = await self.db.fetchrow(sync_query, kb_id, cutoff_date)
        
        total = result['total_syncs'] or 0
        successful = result['successful'] or 0
        
        success_rate = (successful / total * 100) if total > 0 else 0
        uptime = 95.0  # TODO: Calculate actual uptime based on sync frequency
        
        return {
            'total': total,
            'successful': successful,
            'failed': result['failed'] or 0,
            'avg_duration': float(result['avg_duration_minutes'] or 0),
            'last_sync': result['last_sync'],
            'success_rate': success_rate,
            'uptime': uptime
        }
    
    async def _calculate_source_metrics(self, kb_id: int, cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate per-source metrics."""
        
        source_query = """
        SELECT 
            source_id,
            COUNT(*) as doc_count,
            COUNT(*) FILTER (WHERE fr.status = 'success') as successful_docs,
            AVG(CASE WHEN fr.status = 'success' THEN 1.0 ELSE 0.0 END) * 100 as success_rate
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE sr.kb_id = $1
        GROUP BY source_id
        """
        
        rows = await self.db.fetch(source_query, kb_id)
        
        document_counts = {}
        success_rates = {}
        
        for row in rows:
            source_id = row['source_id']
            document_counts[source_id] = row['doc_count']
            success_rates[source_id] = float(row['success_rate'] or 0)
        
        return {
            'document_counts': document_counts,
            'success_rates': success_rates
        }
    
    async def _calculate_storage_metrics(self, kb_id: int) -> Dict[str, float]:
        """Calculate storage and size metrics."""
        
        # TODO: Implement actual blob storage size calculation
        # For now, estimate based on document count
        doc_count_query = """
        SELECT COUNT(*) as total_docs
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE sr.kb_id = $1 AND fr.status = 'success'
        """
        
        result = await self.db.fetchrow(doc_count_query, kb_id)
        total_docs = result['total_docs'] or 0
        
        # Rough estimates
        avg_size_kb = 150.0  # Average document size
        total_size_gb = (total_docs * avg_size_kb) / (1024 * 1024)
        cost_per_gb = 0.023  # Azure Blob Storage cost
        cost_estimate = total_size_gb * cost_per_gb
        
        return {
            'total_gb': total_size_gb,
            'avg_size_kb': avg_size_kb,
            'cost_estimate': cost_estimate
        }
    
    async def _calculate_trends(self, kb_id: int, days: int = 7) -> Dict[str, List]:
        """Calculate trend data for the last N days."""
        
        # Daily document counts
        doc_trend_query = """
        SELECT 
            DATE(fr.first_discovered) as day,
            COUNT(*) as doc_count
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE sr.kb_id = $1 
        AND fr.first_discovered >= $2
        GROUP BY DATE(fr.first_discovered)
        ORDER BY day
        """
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        doc_rows = await self.db.fetch(doc_trend_query, kb_id, cutoff)
        
        # Daily sync performance
        sync_trend_query = """
        SELECT 
            DATE(started_at) as day,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_duration
        FROM sync_run
        WHERE kb_id = $1 
        AND started_at >= $2
        AND status = 'completed'
        GROUP BY DATE(started_at)
        ORDER BY day
        """
        
        sync_rows = await self.db.fetch(sync_trend_query, kb_id, cutoff)
        
        # Create daily arrays (fill missing days with 0)
        documents_trend = [0] * days
        sync_trend = [0.0] * days
        
        base_date = datetime.utcnow().date() - timedelta(days=days-1)
        
        for row in doc_rows:
            day_offset = (row['day'] - base_date).days
            if 0 <= day_offset < days:
                documents_trend[day_offset] = row['doc_count']
        
        for row in sync_rows:
            day_offset = (row['day'] - base_date).days
            if 0 <= day_offset < days:
                sync_trend[day_offset] = float(row['avg_duration'] or 0)
        
        return {
            'documents': documents_trend,
            'sync_performance': sync_trend
        }
    
    async def _calculate_error_analysis(self, kb_id: int, cutoff_date: datetime) -> Dict[str, Any]:
        """Analyze errors and failure patterns."""
        
        # Common error types
        error_query = """
        SELECT 
            error_message,
            COUNT(*) as error_count,
            MAX(created_at) as last_occurrence
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE sr.kb_id = $1 
        AND fr.status = 'failed'
        AND fr.created_at >= $2
        GROUP BY error_message
        ORDER BY error_count DESC
        LIMIT 10
        """
        
        error_rows = await self.db.fetch(error_query, kb_id, cutoff_date)
        
        common_errors = []
        for row in error_rows:
            common_errors.append({
                'error_message': row['error_message'],
                'count': row['error_count'],
                'last_seen': row['last_occurrence']
            })
        
        # TODO: Calculate error rate trend
        error_trend = [2.1, 1.8, 2.3, 1.5, 1.2, 0.8, 1.1]  # Mock data
        
        return {
            'common_errors': common_errors,
            'error_trend': error_trend
        }
    
    async def _calculate_global_metrics(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate global system metrics."""
        
        kb_query = """
        SELECT 
            COUNT(*) as total_kbs,
            COUNT(*) FILTER (WHERE status = 'active') as active_kbs
        FROM multi_source_knowledge_base
        """
        
        kb_result = await self.db.fetchrow(kb_query)
        
        doc_query = """
        SELECT COUNT(*) as total_docs
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE fr.status = 'success'
        """
        
        doc_result = await self.db.fetchrow(doc_query)
        
        return {
            'total_kbs': kb_result['total_kbs'] or 0,
            'active_kbs': kb_result['active_kbs'] or 0,
            'total_docs': doc_result['total_docs'] or 0,
            'total_storage': 0.0  # TODO: Calculate from blob storage
        }
    
    async def _calculate_global_performance(self, cutoff_date: datetime) -> Dict[str, float]:
        """Calculate global performance metrics."""
        
        perf_query = """
        SELECT 
            COUNT(*) as total_syncs,
            COUNT(*) FILTER (WHERE status = 'completed') as successful_syncs,
            AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_duration
        FROM sync_run
        WHERE started_at >= $1
        """
        
        result = await self.db.fetchrow(perf_query, cutoff_date)
        
        total = result['total_syncs'] or 0
        successful = result['successful_syncs'] or 0
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        return {
            'success_rate': success_rate,
            'avg_duration': float(result['avg_duration'] or 0),
            'total_syncs': total
        }
    
    async def _calculate_global_costs(self, cutoff_date: datetime) -> Dict[str, float]:
        """Calculate global cost metrics."""
        
        # TODO: Implement actual cost calculation
        return {
            'total_cost': 127.50,
            'cost_per_kb': 15.30,
            'cost_per_doc': 0.0085
        }
    
    async def _calculate_growth_metrics(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate growth and trend metrics."""
        
        growth_query = """
        SELECT 
            COUNT(*) FILTER (WHERE created_at >= $1) as new_kbs_30d,
            COUNT(*) as total_kbs
        FROM multi_source_knowledge_base
        """
        
        result = await self.db.fetchrow(growth_query, cutoff_date)
        
        return {
            'new_kbs': result['new_kbs_30d'] or 0,
            'doc_growth_rate': 15.2  # TODO: Calculate actual growth rate
        }
    
    async def _calculate_top_performers(self, cutoff_date: datetime) -> Dict[str, str]:
        """Calculate top performing knowledge bases."""
        
        # Most active (most syncs)
        active_query = """
        SELECT kb.kb_name, COUNT(*) as sync_count
        FROM sync_run sr
        JOIN multi_source_knowledge_base kb ON sr.kb_id = kb.id
        WHERE sr.started_at >= $1
        GROUP BY kb.kb_name
        ORDER BY sync_count DESC
        LIMIT 1
        """
        
        active_result = await self.db.fetchrow(active_query, cutoff_date)
        
        # Largest by documents
        largest_query = """
        SELECT kb.kb_name, COUNT(*) as doc_count
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        JOIN multi_source_knowledge_base kb ON sr.kb_id = kb.id
        WHERE fr.status = 'success'
        GROUP BY kb.kb_name
        ORDER BY doc_count DESC
        LIMIT 1
        """
        
        largest_result = await self.db.fetchrow(largest_query)
        
        # Fastest sync
        fastest_query = """
        SELECT kb.kb_name, AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/60) as avg_duration
        FROM sync_run sr
        JOIN multi_source_knowledge_base kb ON sr.kb_id = kb.id
        WHERE sr.started_at >= $1 AND sr.status = 'completed'
        GROUP BY kb.kb_name
        ORDER BY avg_duration ASC
        LIMIT 1
        """
        
        fastest_result = await self.db.fetchrow(fastest_query, cutoff_date)
        
        return {
            'most_active': active_result['kb_name'] if active_result else 'N/A',
            'largest': largest_result['kb_name'] if largest_result else 'N/A',
            'fastest': fastest_result['kb_name'] if fastest_result else 'N/A'
        }
    
    async def _calculate_issues_summary(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Calculate issues and error summary."""
        
        issues_query = """
        SELECT 
            COUNT(DISTINCT sr.kb_id) as kbs_with_issues,
            COUNT(*) as total_errors
        FROM file_record fr
        JOIN sync_run sr ON fr.sync_run_id = sr.id
        WHERE fr.status = 'failed' AND fr.created_at >= $1
        """
        
        result = await self.db.fetchrow(issues_query, cutoff_date)
        
        # Top error types
        top_errors_query = """
        SELECT 
            error_message,
            COUNT(*) as error_count
        FROM file_record
        WHERE status = 'failed' AND created_at >= $1
        GROUP BY error_message
        ORDER BY error_count DESC
        LIMIT 5
        """
        
        error_rows = await self.db.fetch(top_errors_query, cutoff_date)
        
        top_errors = []
        for row in error_rows:
            top_errors.append({
                'error_type': row['error_message'],
                'count': row['error_count']
            })
        
        return {
            'kbs_with_issues': result['kbs_with_issues'] or 0,
            'total_errors': result['total_errors'] or 0,
            'top_errors': top_errors
        }


async def create_metrics_engine() -> MetricsEngine:
    """Factory function to create a MetricsEngine with database connection."""
    from ..data.database import Database, DatabaseConfig
    
    config = DatabaseConfig()
    db = Database(config)
    await db.connect()
    
    return MetricsEngine(db)