"""
Banking-grade audit logging and compliance system

Implements comprehensive audit trails for:
- Authentication and authorization events
- Business operations and data access
- System configuration changes
- Compliance reporting
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel
import structlog
import json
import uuid
from fastapi import Request, Response
import asyncio

from .config import get_settings


logger = structlog.get_logger(__name__)
settings = get_settings()


class AuditEventType(str, Enum):
    """Audit event categories for banking compliance"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIGURATION = "system_configuration"
    BUSINESS_OPERATION = "business_operation"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    ERROR = "error"


class AuditSeverity(str, Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""
    SOX = "sox"          # Sarbanes-Oxley
    GDPR = "gdpr"        # General Data Protection Regulation
    PCI_DSS = "pci_dss"  # Payment Card Industry Data Security Standard
    BASEL_III = "basel_iii"  # Basel III banking regulations
    FFIEC = "ffiec"      # Federal Financial Institutions Examination Council


class AuditEvent(BaseModel):
    """Comprehensive audit event model for banking compliance"""
    
    # Core identifiers
    audit_id: str
    timestamp: datetime
    event_type: AuditEventType
    action: str
    severity: AuditSeverity = AuditSeverity.MEDIUM
    
    # User context
    user_id: Optional[str] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    business_unit: Optional[str] = None
    
    # Request context
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    http_method: Optional[str] = None
    
    # Business context
    business_justification: Optional[str] = None
    affected_data_types: List[str] = []
    data_classification: Optional[str] = None
    
    # Technical details
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    operation_result: str = "unknown"  # success, failure, error
    error_message: Optional[str] = None
    
    # Compliance
    compliance_frameworks: List[ComplianceFramework] = []
    regulatory_requirement: Optional[str] = None
    
    # Additional context
    details: Dict[str, Any] = {}
    
    # Retention and classification
    retention_period_days: int = 2555  # 7 years default for banking
    
    class Config:
        use_enum_values = True


class AuditLogger:
    """Centralized audit logging system"""
    
    def __init__(self):
        self.logger = structlog.get_logger("audit")
    
    async def log_event(self, event: AuditEvent):
        """Log audit event with proper formatting and routing"""
        
        # Enrich event with system context
        event.audit_id = event.audit_id or str(uuid.uuid4())
        event.timestamp = event.timestamp or datetime.utcnow()
        
        # Determine compliance frameworks based on event type
        if not event.compliance_frameworks:
            event.compliance_frameworks = self._determine_compliance_frameworks(event)
        
        # Structure the log entry
        log_entry = {
            "audit_id": event.audit_id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "action": event.action,
            "severity": event.severity,
            "user_context": {
                "user_id": event.user_id,
                "username": event.username,
                "session_id": event.session_id,
                "business_unit": event.business_unit
            },
            "request_context": {
                "request_id": event.request_id,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "endpoint": event.endpoint,
                "http_method": event.http_method
            },
            "business_context": {
                "justification": event.business_justification,
                "affected_data_types": event.affected_data_types,
                "data_classification": event.data_classification
            },
            "technical_details": {
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "operation_result": event.operation_result,
                "error_message": event.error_message
            },
            "compliance": {
                "frameworks": [f.value for f in event.compliance_frameworks],
                "regulatory_requirement": event.regulatory_requirement,
                "retention_period_days": event.retention_period_days
            },
            "details": event.details
        }
        
        # Log to structured logger
        self.logger.info(
            "audit_event",
            **log_entry
        )
        
        # For critical events, also send to security monitoring
        if event.severity == AuditSeverity.CRITICAL:
            await self._send_to_security_monitoring(event)
        
        # Store in audit database (in production environment)
        if settings.ENVIRONMENT == "production":
            await self._store_in_audit_db(event)
    
    def _determine_compliance_frameworks(self, event: AuditEvent) -> List[ComplianceFramework]:
        """Determine applicable compliance frameworks based on event characteristics"""
        frameworks = []
        
        # SOX applies to all financial data and system controls
        if event.event_type in [
            AuditEventType.DATA_MODIFICATION,
            AuditEventType.SYSTEM_CONFIGURATION,
            AuditEventType.BUSINESS_OPERATION
        ]:
            frameworks.append(ComplianceFramework.SOX)
        
        # GDPR applies to personal data processing
        if "personal_data" in event.affected_data_types or "pii" in event.affected_data_types:
            frameworks.append(ComplianceFramework.GDPR)
        
        # Banking regulations apply to all banking operations
        frameworks.append(ComplianceFramework.FFIEC)
        
        return frameworks
    
    async def _send_to_security_monitoring(self, event: AuditEvent):
        """Send critical events to security monitoring system"""
        # In production, integrate with SIEM/security monitoring
        logger.critical(
            "security_alert",
            audit_id=event.audit_id,
            event_type=event.event_type,
            action=event.action,
            user_id=event.user_id,
            details=event.details
        )
    
    async def _store_in_audit_db(self, event: AuditEvent):
        """Store audit event in dedicated audit database"""
        # In production, store in immutable audit database
        # This is a placeholder for the actual implementation
        pass


# Global audit logger instance
audit_logger = AuditLogger()


def create_audit_event(
    event_type: AuditEventType,
    action: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    operation_result: str = "success",
    severity: AuditSeverity = AuditSeverity.MEDIUM,
    business_justification: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    **kwargs
) -> AuditEvent:
    """Create and log an audit event"""
    
    event = AuditEvent(
        audit_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        event_type=event_type,
        action=action,
        severity=severity,
        user_id=user_id,
        username=username,
        resource_type=resource_type,
        resource_id=resource_id,
        operation_result=operation_result,
        business_justification=business_justification,
        details=details or {},
        **kwargs
    )
    
    # Log the event asynchronously, but handle case where no event loop is running
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(audit_logger.log_event(event))
    except RuntimeError:
        # No event loop is running (e.g., in thread pool), schedule for later
        import threading
        import concurrent.futures
        
        # Use a thread pool to run the async function
        def run_audit_log():
            asyncio.run(audit_logger.log_event(event))
        
        # Run in background thread to avoid blocking
        threading.Thread(target=run_audit_log, daemon=True).start()
    
    return event


async def audit_middleware(request: Request, call_next):
    """Middleware to automatically audit HTTP requests"""
    
    start_time = datetime.utcnow()
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # Extract user context if available
    user = getattr(request.state, 'current_user', None)
    user_id = user.user_id if user else None
    username = user.username if user else None
    business_unit = user.business_unit if user else None
    
    # Process the request
    try:
        response: Response = await call_next(request)
        operation_result = "success" if response.status_code < 400 else "failure"
        
    except Exception as e:
        operation_result = "error"
        error_message = str(e)
        
        # Log the error
        create_audit_event(
            event_type=AuditEventType.ERROR,
            action="request_error",
            user_id=user_id,
            username=username,
            request_id=request_id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=str(request.url.path),
            http_method=request.method,
            operation_result=operation_result,
            severity=AuditSeverity.HIGH,
            details={
                "error_message": error_message,
                "request_body_size": request.headers.get("content-length", 0)
            }
        )
        raise
    
    # Calculate request duration
    end_time = datetime.utcnow()
    duration_ms = (end_time - start_time).total_seconds() * 1000
    
    # Determine if this request should be audited
    should_audit = (
        request.method in ["POST", "PUT", "PATCH", "DELETE"] or  # State-changing operations
        "sync" in request.url.path or  # Business operations
        "admin" in request.url.path or  # Administrative operations
        response.status_code >= 400  # Errors
    )
    
    if should_audit:
        # Determine event type based on request characteristics
        if "auth" in request.url.path:
            event_type = AuditEventType.AUTHENTICATION
        elif request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            event_type = AuditEventType.DATA_MODIFICATION
        else:
            event_type = AuditEventType.DATA_ACCESS
        
        # Determine severity
        if response.status_code >= 500:
            severity = AuditSeverity.HIGH
        elif response.status_code >= 400:
            severity = AuditSeverity.MEDIUM
        else:
            severity = AuditSeverity.LOW
        
        # Create audit event
        create_audit_event(
            event_type=event_type,
            action=f"{request.method.lower()}_{request.url.path.replace('/', '_')}",
            user_id=user_id,
            username=username,
            business_unit=business_unit,
            request_id=request_id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            endpoint=str(request.url.path),
            http_method=request.method,
            operation_result=operation_result,
            severity=severity,
            details={
                "response_status": response.status_code,
                "duration_ms": duration_ms,
                "request_size": request.headers.get("content-length", 0),
                "response_size": response.headers.get("content-length", 0)
            }
        )
    
    return response


# Helper functions for common audit scenarios

def audit_knowledge_base_operation(
    action: str,
    kb_name: str,
    user_id: str,
    operation_result: str = "success",
    business_justification: Optional[str] = None,
    **kwargs
):
    """Audit knowledge base operations"""
    return create_audit_event(
        event_type=AuditEventType.BUSINESS_OPERATION,
        action=f"knowledge_base_{action}",
        user_id=user_id,
        resource_type="knowledge_base",
        resource_id=kb_name,
        operation_result=operation_result,
        business_justification=business_justification,
        severity=AuditSeverity.MEDIUM,
        **kwargs
    )


def audit_config_operation(
    action: str,
    config_name: str,
    user_id: str,
    operation_result: str = "success",
    **kwargs
):
    """Audit configuration operations"""
    return create_audit_event(
        event_type=AuditEventType.SYSTEM_CONFIGURATION,
        action=f"configuration_{action}",
        user_id=user_id,
        resource_type="configuration",
        resource_id=config_name,
        operation_result=operation_result,
        severity=AuditSeverity.HIGH,
        **kwargs
    )


def audit_sync_operation(
    kb_name: str,
    user_id: str,
    sync_mode: str,
    operation_result: str = "success",
    business_justification: Optional[str] = None,
    **kwargs
):
    """Audit document synchronization operations"""
    return create_audit_event(
        event_type=AuditEventType.BUSINESS_OPERATION,
        action="document_sync",
        user_id=user_id,
        resource_type="knowledge_base",
        resource_id=kb_name,
        operation_result=operation_result,
        business_justification=business_justification,
        severity=AuditSeverity.MEDIUM,
        details={
            "sync_mode": sync_mode,
            **kwargs
        }
    )