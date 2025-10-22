"""
Business-oriented data models for banking document loader operations

These models represent business concepts rather than technical CLI parameters,
providing a banking-appropriate abstraction layer.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Generic, TypeVar
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

# Generic type for API responses
T = TypeVar('T')

# Generic API Response Models
class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[T] = Field(default=None, description="Response data")
    operation_id: Optional[str] = Field(default=None, description="Operation identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = Field(default=False, description="Always false for errors")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

# Scheduler Models (for type hints in API)
class ScheduleInfo(BaseModel):
    """Schedule configuration information"""
    config_name: str
    enabled: bool
    frequency: str
    time: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: str = "UTC"
    max_duration_hours: int = 4
    retry_attempts: int = 3
    notification_emails: List[str] = []
    next_execution: Optional[str] = None

class ExecutionInfo(BaseModel):
    """Execution information"""
    execution_id: str
    config_name: str
    scheduled_time: datetime
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class SchedulerStatus(BaseModel):
    """Scheduler status response"""
    running: bool
    active_schedules: int
    pending_executions: int
    running_executions: int
    schedules: Dict[str, ScheduleInfo]
    generated_at: datetime

class ExecutionsResponse(BaseModel):
    """Executions list response"""
    executions: List[ExecutionInfo]
    total_count: int
    filters: Dict[str, Optional[str]]
    generated_at: datetime


class BusinessPriority(str, Enum):
    """Business priority levels for operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SyncMode(str, Enum):
    """Document synchronization modes"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    FULL_REFRESH = "full_refresh"
    DELTA_ONLY = "delta_only"


class OperationStatus(str, Enum):
    """Operation status for tracking business processes"""
    PENDING = "pending"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataClassification(str, Enum):
    """Banking data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"  # Personally Identifiable Information


class BusinessUnit(str, Enum):
    """Bank business units"""
    RETAIL_BANKING = "retail_banking"
    COMMERCIAL_BANKING = "commercial_banking"
    INVESTMENT_BANKING = "investment_banking"
    RISK_MANAGEMENT = "risk_management"
    COMPLIANCE = "compliance"
    TECHNOLOGY = "technology"
    OPERATIONS = "operations"
    HUMAN_RESOURCES = "human_resources"


# Request Models

class BusinessSyncRequest(BaseModel):
    """Business-oriented sync request with banking context"""
    
    # Business context (required for banking)
    business_justification: str = Field(
        ..., 
        description="Business justification for the sync operation",
        min_length=10,
        max_length=500
    )
    business_unit: BusinessUnit = Field(..., description="Requesting business unit")
    priority: BusinessPriority = Field(default=BusinessPriority.MEDIUM, description="Business priority")
    
    # Technical parameters
    config_name: str = Field(..., description="Configuration name")
    sync_mode: SyncMode = Field(default=SyncMode.PARALLEL, description="Synchronization mode")
    sources: Optional[List[str]] = Field(default=None, description="Specific sources to sync")
    
    # Data context
    data_classification: DataClassification = Field(
        default=DataClassification.INTERNAL,
        description="Data classification level"
    )
    affected_customers: Optional[int] = Field(
        default=None,
        description="Estimated number of customers affected"
    )
    
    # Approval and compliance
    approver_id: Optional[str] = Field(default=None, description="Pre-approver user ID")
    compliance_tags: List[str] = Field(default=[], description="Compliance framework tags")
    
    # Scheduling
    scheduled_time: Optional[datetime] = Field(default=None, description="Scheduled execution time")
    max_duration_hours: int = Field(default=4, description="Maximum allowed duration")
    
    @validator('business_justification')
    def validate_business_justification(cls, v):
        if not v.strip():
            raise ValueError('Business justification cannot be empty')
        return v.strip()


class EmergencySyncRequest(BaseModel):
    """Emergency sync request with expedited approval"""
    
    config_name: str = Field(..., description="Configuration name")
    incident_number: str = Field(..., description="Incident or ticket number")
    emergency_justification: str = Field(
        ...,
        description="Emergency justification",
        min_length=20,
        max_length=1000
    )
    approver_id: str = Field(..., description="Emergency approver user ID")
    business_impact: str = Field(..., description="Business impact description")
    
    # Optional technical parameters
    sync_mode: SyncMode = Field(default=SyncMode.PARALLEL, description="Sync mode")
    sources: Optional[List[str]] = Field(default=None, description="Specific sources")


class KnowledgeBaseUpdateRequest(BaseModel):
    """Request to update knowledge base configuration"""
    
    business_justification: str = Field(..., description="Justification for changes")
    changes: Dict[str, Any] = Field(..., description="Configuration changes")
    impact_assessment: str = Field(..., description="Impact assessment")
    rollback_plan: str = Field(..., description="Rollback plan if needed")


# Response Models

class BusinessSyncResponse(BaseModel):
    """Business-oriented sync response"""
    
    operation_id: str = Field(..., description="Unique operation identifier")
    status: OperationStatus = Field(..., description="Current operation status")
    message: str = Field(..., description="Human-readable status message")
    
    # Business context
    business_impact: Optional[str] = Field(default=None, description="Expected business impact")
    estimated_completion: Optional[datetime] = Field(default=None, description="Estimated completion time")
    affected_sources: List[str] = Field(default=[], description="Sources being synchronized")
    
    # Progress tracking
    progress_percentage: Optional[float] = Field(default=None, description="Completion percentage")
    current_phase: Optional[str] = Field(default=None, description="Current operation phase")
    
    # Approval workflow
    approval_required: bool = Field(default=False, description="Whether approval is required")
    approval_id: Optional[str] = Field(default=None, description="Approval workflow ID")
    required_approvers: List[str] = Field(default=[], description="Required approver roles")


class KnowledgeBaseInfo(BaseModel):
    """Business view of knowledge base information"""
    
    name: str = Field(..., description="Knowledge base name")
    business_owner: str = Field(..., description="Business owner")
    business_unit: BusinessUnit = Field(..., description="Owning business unit")
    
    # Operational info
    last_sync_time: Optional[datetime] = Field(default=None, description="Last successful sync")
    document_count: Optional[int] = Field(default=None, description="Total document count")
    health_status: str = Field(..., description="Health status")
    
    # Business metadata
    business_purpose: str = Field(..., description="Business purpose description")
    data_classification: DataClassification = Field(..., description="Data classification")
    compliance_frameworks: List[str] = Field(default=[], description="Applicable compliance frameworks")
    
    # Sync configuration
    sync_schedule: Optional[str] = Field(default=None, description="Sync schedule")
    sync_frequency: Optional[str] = Field(default=None, description="Sync frequency")
    
    # Metrics
    avg_sync_duration_minutes: Optional[float] = Field(default=None, description="Average sync duration")
    success_rate_percentage: Optional[float] = Field(default=None, description="Success rate")


class SyncOperationDetails(BaseModel):
    """Detailed sync operation information for business users"""
    
    operation_id: str = Field(..., description="Operation identifier")
    status: OperationStatus = Field(..., description="Current status")
    
    # Timeline
    requested_at: datetime = Field(..., description="Request timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    
    # Business context
    requested_by: str = Field(..., description="Requesting user")
    business_justification: str = Field(..., description="Business justification")
    business_unit: BusinessUnit = Field(..., description="Requesting business unit")
    
    # Technical details (business-appropriate level)
    config_name: str = Field(..., description="Configuration used")
    sync_mode: SyncMode = Field(..., description="Sync mode")
    sources_synced: List[str] = Field(default=[], description="Sources processed")
    
    # Results
    documents_processed: Optional[int] = Field(default=None, description="Documents processed")
    documents_added: Optional[int] = Field(default=None, description="New documents")
    documents_updated: Optional[int] = Field(default=None, description="Updated documents")
    documents_removed: Optional[int] = Field(default=None, description="Removed documents")
    
    # Error information (if applicable)
    error_summary: Optional[str] = Field(default=None, description="Error summary for business users")
    resolution_steps: Optional[str] = Field(default=None, description="Recommended resolution steps")


class ApprovalWorkflow(BaseModel):
    """Approval workflow information"""
    
    approval_id: str = Field(..., description="Approval workflow ID")
    operation_id: str = Field(..., description="Related operation ID")
    status: str = Field(..., description="Approval status")
    
    # Request details
    requested_by: str = Field(..., description="Requesting user")
    requested_at: datetime = Field(..., description="Request timestamp")
    business_justification: str = Field(..., description="Business justification")
    
    # Approval requirements
    required_approvers: List[str] = Field(..., description="Required approver roles/users")
    current_approvers: List[str] = Field(default=[], description="Users who have approved")
    pending_approvers: List[str] = Field(default=[], description="Pending approvers")
    
    # Risk assessment
    risk_level: str = Field(..., description="Assessed risk level")
    risk_factors: List[str] = Field(default=[], description="Identified risk factors")
    
    # Timing
    approval_deadline: Optional[datetime] = Field(default=None, description="Approval deadline")
    auto_approve_after: Optional[datetime] = Field(default=None, description="Auto-approval time")


class BusinessMetrics(BaseModel):
    """Business-oriented metrics and KPIs"""
    
    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")
    
    # Operational metrics
    total_syncs: int = Field(..., description="Total sync operations")
    successful_syncs: int = Field(..., description="Successful syncs")
    failed_syncs: int = Field(..., description="Failed syncs")
    avg_sync_duration_minutes: float = Field(..., description="Average sync duration")
    
    # Business impact metrics
    documents_processed: int = Field(..., description="Total documents processed")
    data_volume_gb: float = Field(..., description="Data volume processed (GB)")
    business_units_served: int = Field(..., description="Number of business units served")
    
    # Compliance metrics
    audit_events: int = Field(..., description="Total audit events")
    compliance_violations: int = Field(..., description="Compliance violations")
    sla_breaches: int = Field(..., description="SLA breaches")
    
    # Cost metrics
    estimated_cost_usd: Optional[float] = Field(default=None, description="Estimated operational cost")
    cost_per_document: Optional[float] = Field(default=None, description="Cost per document processed")


# Error Models

class BusinessError(BaseModel):
    """Business-appropriate error information"""
    
    error_code: str = Field(..., description="Business error code")
    error_category: str = Field(..., description="Error category")
    business_message: str = Field(..., description="Business-friendly error message")
    
    # Impact assessment
    business_impact: str = Field(..., description="Impact on business operations")
    affected_processes: List[str] = Field(default=[], description="Affected business processes")
    
    # Resolution information
    estimated_resolution_time: Optional[str] = Field(default=None, description="Estimated resolution time")
    workaround_available: bool = Field(default=False, description="Whether workaround exists")
    workaround_description: Optional[str] = Field(default=None, description="Workaround description")
    
    # Technical details (minimal for business users)
    technical_reference: Optional[str] = Field(default=None, description="Technical reference ID")
    
    # Contact information
    support_contact: str = Field(..., description="Support contact information")
    escalation_contact: Optional[str] = Field(default=None, description="Escalation contact")