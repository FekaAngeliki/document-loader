"""
Approval Service (mock implementation for local development)  
"""
from typing import List
import structlog
from ..api.models import ApprovalWorkflow

logger = structlog.get_logger(__name__)

class ApprovalService:
    """Mock approval service for local development"""
    
    async def create_approval_workflow(self, **kwargs) -> ApprovalWorkflow:
        """Mock approval workflow creation"""
        return ApprovalWorkflow(
            approval_id="approval-123",
            operation_id=kwargs.get("operation_id", "op-123"),
            status="pending",
            requested_by=kwargs.get("requested_by", "admin"),
            requested_at=kwargs.get("requested_at"),
            business_justification=kwargs.get("business_justification", "Test"),
            required_approvers=["manager"],
            risk_level="low",
            risk_factors=[]
        )
    
    async def validate_emergency_request(self, request, requesting_user):
        """Mock emergency validation"""
        logger.info("Emergency request validated", user=requesting_user.username)