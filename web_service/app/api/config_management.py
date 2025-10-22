"""
Configuration Management API Endpoints

Provides business-friendly endpoints for configuration upload, management,
and knowledge base creation with enterprise audit trails.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog
import uuid
import json
import tempfile
import os
import sys

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ..core.auth import User, get_current_user, require_permission, Permission
from ..core.audit import audit_knowledge_base_operation
from ..api.models import BusinessError, OperationStatus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/configs", tags=["Configuration Management"])


class ConfigUploadRequest(BaseModel):
    """Config upload request model."""
    config_name: Optional[str] = None
    description: Optional[str] = None
    business_unit: str = "TECHNOLOGY"
    business_justification: str
    auto_create_kb: bool = False


class ConfigUploadResponse(BaseModel):
    """Config upload response model."""
    operation_id: str
    status: str
    message: str
    config_id: Optional[int] = None
    config_name: str
    validation_status: str
    business_impact: str
    next_steps: List[str] = []


class ConfigListResponse(BaseModel):
    """Config list response model."""
    operation_id: str
    configs: List[Dict[str, Any]]
    total_count: int
    business_context: Dict[str, Any]


@router.post("/upload", response_model=ConfigUploadResponse)
async def upload_config_file(
    background_tasks: BackgroundTasks,
    config_file: UploadFile = File(...),
    request_data: str = None,  # JSON string since we can't mix File and Pydantic easily
    current_user: User = Depends(require_permission(Permission.CONFIG_CREATE))
):
    """
    Upload a configuration file for knowledge base creation.
    
    Business-oriented endpoint that:
    - Validates configuration structure
    - Stores configuration in PostgreSQL
    - Provides business impact assessment
    - Optionally creates knowledge base
    """
    
    operation_id = str(uuid.uuid4())
    
    try:
        # Parse request data
        if request_data:
            request_info = json.loads(request_data)
            upload_request = ConfigUploadRequest(**request_info)
        else:
            upload_request = ConfigUploadRequest(
                business_justification="Configuration upload via API"
            )
        
        # Audit the upload request
        audit_knowledge_base_operation(
            action="config_upload",
            kb_name=upload_request.config_name or "new_config",
            user_id=current_user.user_id,
            details={
                "operation_id": operation_id,
                "filename": config_file.filename,
                "business_unit": upload_request.business_unit,
                "business_justification": upload_request.business_justification
            }
        )
        
        logger.info(
            "Config upload requested",
            operation_id=operation_id,
            user_id=current_user.user_id,
            filename=config_file.filename
        )
        
        # Read and validate config file
        config_content = await config_file.read()
        
        try:
            config_data = json.loads(config_content.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=BusinessError(
                    error_code="INVALID_CONFIG_FORMAT",
                    error_category="validation_error",
                    business_message="Configuration file is not valid JSON",
                    business_impact="Cannot process configuration upload",
                    support_contact="IT Support: ext-4357"
                ).dict()
            )
        
        # Save to temporary file for CLI processing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(config_data, temp_file, indent=2)
            temp_file_path = temp_file.name
        
        try:
            # Use CLI config manager to upload
            from src.admin.config_manager import create_config_manager
            
            config_manager = await create_config_manager()
            
            # Determine config name
            config_name = upload_request.config_name or config_data.get('name') or \
                         config_file.filename.replace('.json', '')
            
            # Upload configuration
            result = await config_manager.upload_config_file(
                file_path=temp_file_path,
                name=config_name,
                description=upload_request.description,
                created_by=current_user.username
            )
            
            # Determine business impact
            source_count = result.get('source_count', 0)
            if source_count == 1:
                business_impact = f"Single-source knowledge base configuration uploaded"
            else:
                business_impact = f"Multi-source knowledge base configuration uploaded ({source_count} sources)"
            
            # Determine next steps
            next_steps = [
                "Configuration validated and stored successfully",
                f"Use 'Create Knowledge Base' to deploy configuration '{config_name}'"
            ]
            
            if upload_request.auto_create_kb:
                # Add background task to create knowledge base
                background_tasks.add_task(
                    _create_knowledge_base_from_config,
                    config_name=config_name,
                    user=current_user,
                    operation_id=operation_id
                )
                next_steps.append("Knowledge base creation initiated in background")
            
            await config_manager.db.disconnect()
            
            # Success audit
            audit_knowledge_base_operation(
                action="config_upload",
                kb_name=config_name,
                user_id=current_user.user_id,
                operation_result="success",
                details={
                    "operation_id": operation_id,
                    "config_id": result['config_id'],
                    "source_count": source_count,
                    "auto_create_kb": upload_request.auto_create_kb
                }
            )
            
            return ConfigUploadResponse(
                operation_id=operation_id,
                status="success",
                message=f"Configuration '{config_name}' uploaded successfully",
                config_id=result['config_id'],
                config_name=config_name,
                validation_status="valid",
                business_impact=business_impact,
                next_steps=next_steps
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Config upload failed", operation_id=operation_id, error=str(e))
        
        audit_knowledge_base_operation(
            action="config_upload",
            kb_name=upload_request.config_name or "unknown",
            user_id=current_user.user_id,
            operation_result="error",
            details={
                "operation_id": operation_id,
                "error": str(e)
            }
        )
        
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BusinessError(
                error_code="CONFIG_UPLOAD_FAILED",
                error_category="system_error",
                business_message="Unable to process configuration upload",
                business_impact="Configuration management temporarily unavailable",
                support_contact="IT Support: ext-4357",
                technical_reference=operation_id
            ).dict()
        )


@router.get("/list", response_model=ConfigListResponse)
async def list_configurations(
    config_type: Optional[str] = None,
    business_unit: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    List stored configuration files with business context.
    
    Provides business-appropriate view of stored configurations including:
    - Usage statistics
    - Deployment history
    - Business ownership
    """
    
    operation_id = str(uuid.uuid4())
    
    try:
        # Audit the list request
        audit_knowledge_base_operation(
            action="config_list",
            kb_name="*",
            user_id=current_user.user_id,
            details={
                "operation_id": operation_id,
                "filters": {
                    "config_type": config_type,
                    "business_unit": business_unit
                }
            }
        )
        
        # Get configurations from database
        from src.admin.config_manager import create_config_manager
        
        config_manager = await create_config_manager()
        configs = await config_manager.list_configs(status="active")
        
        # Add business context to each config
        enriched_configs = []
        for config in configs:
            # Enrich with business information
            enriched_config = {
                **config,
                "business_friendly_name": config['name'].replace('_', ' ').title(),
                "deployment_status": _get_deployment_status(config),
                "business_owner": config.get('created_by', 'Unknown'),
                "risk_level": _assess_config_risk(config),
                "last_activity": config.get('last_deployed_at') or config.get('created_at')
            }
            
            # Apply filters
            if config_type and config.get('rag_type') != config_type:
                continue
            if business_unit:  # TODO: Add business unit to config storage
                pass
                
            enriched_configs.append(enriched_config)
        
        await config_manager.db.disconnect()
        
        # Business context
        business_context = {
            "requested_by": current_user.username,
            "business_unit": current_user.business_unit,
            "request_time": datetime.utcnow().isoformat(),
            "total_configurations": len(enriched_configs),
            "filters_applied": {
                "config_type": config_type,
                "business_unit": business_unit
            }
        }
        
        return ConfigListResponse(
            operation_id=operation_id,
            configs=enriched_configs,
            total_count=len(enriched_configs),
            business_context=business_context
        )
        
    except Exception as e:
        logger.error("Config list failed", operation_id=operation_id, error=str(e))
        
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BusinessError(
                error_code="CONFIG_LIST_FAILED",
                error_category="system_error",
                business_message="Unable to retrieve configuration list",
                business_impact="Configuration management temporarily unavailable",
                support_contact="IT Support: ext-4357",
                technical_reference=operation_id
            ).dict()
        )


@router.get("/{config_name}/analytics")
async def get_config_analytics(
    config_name: str,
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics for a specific configuration.
    
    Provides business metrics including:
    - Usage statistics
    - Performance metrics
    - Cost analysis
    - Document processing trends
    """
    
    operation_id = str(uuid.uuid4())
    
    try:
        # Use analytics engine
        from src.analytics.metrics_engine import create_metrics_engine
        
        metrics_engine = await create_metrics_engine()
        
        # Get knowledge base metrics for this config
        try:
            metrics = await metrics_engine.calculate_kb_metrics(config_name, days)
            
            # Convert to business-friendly response
            analytics_response = {
                "operation_id": operation_id,
                "config_name": config_name,
                "reporting_period_days": days,
                "generated_at": datetime.utcnow().isoformat(),
                "status": "success",
                
                # Business summary
                "business_summary": {
                    "knowledge_base_name": metrics.kb_name,
                    "total_documents": metrics.total_documents,
                    "operational_health": "Healthy" if metrics.success_rate_percentage > 90 else "Needs Attention",
                    "last_sync": metrics.last_sync_time.isoformat() if metrics.last_sync_time else None,
                    "cost_estimate": f"${metrics.cost_estimate_usd:.2f}"
                },
                
                # Performance metrics
                "performance": {
                    "success_rate": f"{metrics.success_rate_percentage:.1f}%",
                    "average_sync_duration": f"{metrics.avg_sync_duration_minutes:.1f} minutes",
                    "total_sync_operations": metrics.total_syncs,
                    "uptime": f"{metrics.uptime_percentage:.1f}%"
                },
                
                # Growth metrics
                "growth": {
                    "new_documents_30d": metrics.new_documents_30d,
                    "updated_documents_30d": metrics.updated_documents_30d,
                    "document_growth_trend": metrics.documents_trend_7d
                },
                
                # Source analysis
                "sources": {
                    "source_breakdown": metrics.source_document_counts,
                    "source_performance": metrics.source_success_rates
                },
                
                # Issues analysis
                "issues": {
                    "recent_errors": len(metrics.common_errors),
                    "error_rate_trend": metrics.error_rate_trend,
                    "top_issues": metrics.common_errors[:3]
                }
            }
            
            await metrics_engine.db.disconnect()
            return analytics_response
            
        except ValueError:
            # Knowledge base not found
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=BusinessError(
                    error_code="CONFIG_NOT_DEPLOYED",
                    error_category="not_found",
                    business_message=f"Configuration '{config_name}' has not been deployed as a knowledge base",
                    business_impact="Cannot generate analytics for undeployed configuration",
                    support_contact="Data Steward: data-team@bank.com"
                ).dict()
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Config analytics failed", operation_id=operation_id, error=str(e))
        
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BusinessError(
                error_code="ANALYTICS_FAILED",
                error_category="system_error",
                business_message="Unable to generate configuration analytics",
                business_impact="Analytics temporarily unavailable",
                support_contact="Business Intelligence: bi-team@bank.com",
                technical_reference=operation_id
            ).dict()
        )


# Background task functions

async def _create_knowledge_base_from_config(
    config_name: str,
    user: User,
    operation_id: str
):
    """Create knowledge base from uploaded configuration in background."""
    
    try:
        logger.info("Creating KB from config", config_name=config_name, operation_id=operation_id)
        
        # Use CLI to create knowledge base
        from src.data.database import Database, DatabaseConfig
        from src.data.multi_source_repository import MultiSourceRepository
        from src.admin.config_manager import create_config_manager
        
        # Get configuration
        config_manager = await create_config_manager()
        config = await config_manager.get_config(config_name)
        
        if not config:
            logger.error("Config not found for KB creation", config_name=config_name)
            return
        
        # Create knowledge base
        db_config = DatabaseConfig()
        db = Database(db_config)
        await db.connect()
        
        repo = MultiSourceRepository(db)
        
        # Create KB from config
        kb = await repo.create_multi_source_knowledge_base_from_config(
            config_name=config_name,
            config_data=config['config_content'],
            created_by=user.username
        )
        
        logger.info("KB created successfully", kb_name=kb.kb_name, operation_id=operation_id)
        
        # Audit success
        audit_knowledge_base_operation(
            action="auto_kb_creation",
            kb_name=kb.kb_name,
            user_id=user.user_id,
            operation_result="success",
            details={
                "operation_id": operation_id,
                "config_name": config_name,
                "kb_id": kb.id
            }
        )
        
        await db.disconnect()
        await config_manager.db.disconnect()
        
    except Exception as e:
        logger.error("Auto KB creation failed", config_name=config_name, error=str(e))
        
        audit_knowledge_base_operation(
            action="auto_kb_creation",
            kb_name=config_name,
            user_id=user.user_id,
            operation_result="error",
            details={
                "operation_id": operation_id,
                "error": str(e)
            }
        )


# Helper functions

def _get_deployment_status(config: dict) -> str:
    """Get human-readable deployment status."""
    last_deployed = config.get('last_deployed_at')
    deployment_count = config.get('deployment_count', 0)
    
    if not last_deployed:
        return "Never deployed"
    elif deployment_count == 1:
        return "Deployed once"
    elif deployment_count > 1:
        return f"Deployed {deployment_count} times"
    else:
        return "Unknown"


def _assess_config_risk(config: dict) -> str:
    """Assess configuration risk level."""
    source_count = config.get('source_count', 0)
    
    if source_count == 1:
        return "Low"
    elif source_count <= 3:
        return "Medium"
    else:
        return "High"