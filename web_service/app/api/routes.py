"""
Main API router that aggregates all endpoint modules
"""

from fastapi import APIRouter
from .knowledge_bases import router as kb_router
from .auth import router as auth_router
from .admin import router as admin_router
from .config_management import router as config_router
from .scheduler import router as scheduler_router
from .connectivity import router as connectivity_router
from .schema_management import router as schema_router
from .cli_operations import router as cli_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(kb_router, tags=["Knowledge Bases"])
api_router.include_router(config_router, tags=["Configuration Management"])
api_router.include_router(scheduler_router, tags=["Scheduler"])
api_router.include_router(connectivity_router, tags=["Connectivity"])
api_router.include_router(admin_router, prefix="/admin", tags=["Administration"])
api_router.include_router(schema_router, prefix="/schemas", tags=["Schema Management"])
api_router.include_router(cli_router, prefix="/cli", tags=["CLI Operations"])