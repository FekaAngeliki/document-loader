"""
CLI Integration Service (mock implementation for local development)
"""
from typing import Optional, List
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class CLIResult(BaseModel):
    success: bool
    documents_processed: Optional[int] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None

class DocumentLoaderCLI:
    """Mock CLI integration for local development"""
    
    async def execute_sync(
        self, 
        config_name: str, 
        sync_mode: str, 
        sources: Optional[List[str]] = None
    ) -> CLIResult:
        """Mock sync execution"""
        logger.info(
            "Mock sync execution", 
            config_name=config_name, 
            sync_mode=sync_mode, 
            sources=sources
        )
        
        return CLIResult(
            success=True,
            documents_processed=100,
            duration_seconds=120.5
        )
    
    async def execute_emergency_sync(
        self, 
        config_name: str, 
        sync_mode: str, 
        sources: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> CLIResult:
        """Mock emergency sync execution"""
        logger.warning(
            "Mock emergency sync execution", 
            config_name=config_name, 
            priority=priority
        )
        
        return CLIResult(
            success=True,
            documents_processed=50,
            duration_seconds=60.0
        )