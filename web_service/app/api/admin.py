"""
Administration endpoints (basic implementation for local testing)
"""
from fastapi import APIRouter, Depends
from ..core.auth import User, get_current_user

router = APIRouter()

@router.get("/status")
async def admin_status(current_user: User = Depends(get_current_user)):
    """Admin status endpoint"""
    return {
        "status": "ok",
        "user": current_user.username,
        "roles": [role.value for role in current_user.roles]
    }