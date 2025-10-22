"""
Connectivity testing API endpoints.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..core.auth import get_current_user, require_permission, Permission
from ..api.models import APIResponse
from ..core.audit import create_audit_event, AuditEventType

# Import RAG implementations with error handling
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    
    from src.implementations.mock_rag_system import MockRAGSystem
    from src.implementations.file_system_storage import FileSystemStorage
    
    # Try to import Azure implementation
    try:
        from src.implementations.azure_blob_rag_system import AzureBlobRAGSystem
        AZURE_AVAILABLE = True
    except ImportError:
        AZURE_AVAILABLE = False
        AzureBlobRAGSystem = None
    
    from src.data.database import Database, DatabaseConfig
    
except ImportError as e:
    logging.error(f"Error importing RAG implementations: {e}")
    MockRAGSystem = None
    FileSystemStorage = None
    AzureBlobRAGSystem = None
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connectivity", tags=["connectivity"])

async def _has_permission(user, permission: Permission) -> bool:
    """Check if user has the required permission."""
    # In development mode, allow all permissions
    from ..core.config import get_settings
    settings = get_settings()
    if settings.ENVIRONMENT == "development":
        return True
    
    # Check user permissions based on roles
    user_permissions = []
    user_roles = getattr(user, 'roles', [])
    from ..core.auth import ROLE_PERMISSIONS, UserRole
    
    for role_str in user_roles:
        try:
            role = UserRole(role_str)
            user_permissions.extend(ROLE_PERMISSIONS.get(role, []))
        except ValueError:
            continue
    
    return permission in user_permissions

# RAG system registry
RAG_SYSTEMS = {
    'mock': {
        'class': MockRAGSystem,
        'name': 'Mock RAG System',
        'description': 'In-memory mock system for testing',
        'required_config': [],
        'available': MockRAGSystem is not None
    },
    'file_system_storage': {
        'class': FileSystemStorage,
        'name': 'File System Storage',
        'description': 'Local file system storage with metadata',
        'required_config': ['storage_path'],
        'available': FileSystemStorage is not None
    }
}

# Add Azure support if available
if AZURE_AVAILABLE and AzureBlobRAGSystem is not None:
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
        ],
        'available': True
    }

class ConnectivityTestRequest(BaseModel):
    """Request model for connectivity testing."""
    rag_type: str = Field(..., description="RAG system type to test")
    config: Dict[str, Any] = Field(default_factory=dict, description="RAG system configuration")
    database_name: Optional[str] = Field(None, description="Custom database name to test")
    run_comprehensive_tests: bool = Field(True, description="Run comprehensive CRUD tests")

# Simplified response models - detailed testing is handled by CLI

@router.get("/systems")
async def list_rag_systems(
    current_user = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """List available RAG systems for connectivity testing."""
    if not await _has_permission(current_user, Permission.CONNECTIVITY_READ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    systems = {}
    for rag_type, info in RAG_SYSTEMS.items():
        systems[rag_type] = {
            'name': info['name'],
            'description': info['description'],
            'required_config': info['required_config'],
            'available': info['available']
        }
    
    create_audit_event(
        event_type=AuditEventType.BUSINESS_OPERATION,
        action="connectivity.list_systems",
        user_id=current_user.user_id,
        resource_type="connectivity",
        details={"systems_count": len(systems)}
    )
    
    return APIResponse(
        success=True,
        data=systems,
        message=f"Found {len(systems)} RAG systems"
    )

@router.post("/test")
async def test_connectivity(
    request: ConnectivityTestRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Test connectivity to a specified RAG system using CLI integration."""
    if not await _has_permission(current_user, Permission.CONNECTIVITY_TEST):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Validate RAG type
        if request.rag_type not in RAG_SYSTEMS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown RAG type: {request.rag_type}. Available: {list(RAG_SYSTEMS.keys())}"
            )
        
        rag_info = RAG_SYSTEMS[request.rag_type]
        
        if not rag_info['available']:
            raise HTTPException(
                status_code=400,
                detail=f"RAG type '{request.rag_type}' is not available (missing dependencies)"
            )
        
        # Use CLI integration to run the connectivity test
        from ..services.cli_integration import DocumentLoaderCLI
        cli = DocumentLoaderCLI()
        
        # Build the connectivity check command
        cmd_args = ["connectivity", "check", "--rag-type", request.rag_type, "--no-interactive"]
        if request.database_name:
            cmd_args.extend(["--database-name", request.database_name])
        if not request.run_comprehensive_tests:
            # Note: CLI always runs comprehensive tests, this is for future enhancement
            pass
        
        # Execute the command
        result = await cli.execute_command(cmd_args)
        
        end_time = asyncio.get_event_loop().time()
        total_duration = (end_time - start_time) * 1000
        
        # Parse CLI output into response format
        response_data = {
            "rag_type": request.rag_type,
            "rag_name": rag_info['name'],
            "database_connectivity": result.success,  # CLI tests DB first
            "rag_connectivity": result.success,
            "overall_success": result.success,
            "total_duration_ms": total_duration,
            "summary": "CLI connectivity test completed",
            "cli_output": result.stdout if result.stdout else result.stderr,
            "exit_code": result.return_code
        }
        
        # Log audit event
        create_audit_event(
            event_type=AuditEventType.BUSINESS_OPERATION,
            action="connectivity.test",
            user_id=current_user.user_id,
            resource_type="connectivity",
            resource_id=request.rag_type,
            details={
                "rag_type": request.rag_type,
                "database_name": request.database_name,
                "success": result.success,
                "duration_ms": total_duration,
                "exit_code": result.return_code
            }
        )
        
        return APIResponse(
            success=result.success,
            data=response_data,
            message=f"Connectivity test {'passed' if result.success else 'failed'}"
        )
        
    except Exception as e:
        logger.error(f"Connectivity test failed: {e}")
        
        # Log audit event
        create_audit_event(
            event_type=AuditEventType.ERROR,
            action="connectivity.test",
            user_id=current_user.user_id,
            resource_type="connectivity",
            resource_id=request.rag_type,
            details={
                "rag_type": request.rag_type,
                "error": str(e),
                "success": False
            }
        )
        
        raise HTTPException(status_code=500, detail=str(e))

# Note: All testing logic is now handled by CLI integration
# The API delegates to the CLI command which provides comprehensive testing