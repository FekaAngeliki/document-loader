"""
Prometheus metrics for banking operations monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
import time

# Business metrics
sync_operations_total = Counter(
    'document_loader_sync_operations_total',
    'Total sync operations',
    ['business_unit', 'operation_type', 'status']
)

sync_duration_seconds = Histogram(
    'document_loader_sync_duration_seconds',
    'Sync operation duration',
    ['business_unit', 'kb_name']
)

active_operations = Gauge(
    'document_loader_active_operations',
    'Currently active operations',
    ['operation_type']
)

# Authentication metrics
auth_requests_total = Counter(
    'document_loader_auth_requests_total',
    'Authentication requests',
    ['status', 'business_unit']
)

# API metrics
api_requests_total = Counter(
    'document_loader_api_requests_total',
    'API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration_seconds = Histogram(
    'document_loader_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

async def metrics_middleware(request: Request, call_next):
    """Middleware to collect API metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Record metrics
    api_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    api_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response