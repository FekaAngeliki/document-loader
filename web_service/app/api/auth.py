"""
Authentication endpoints (basic implementation for local testing)
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timedelta
import structlog

from ..core.auth import create_access_token, User, UserRole

logger = structlog.get_logger(__name__)
router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_info: dict

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login endpoint for local development"""
    
    # Mock authentication for local development
    if request.username == "admin" and request.password == "admin":
        mock_user = User(
            user_id="admin-001",
            username="admin",
            email="admin@localhost",
            full_name="Local Admin",
            roles=[UserRole.SUPER_ADMIN],
            business_unit="TECHNOLOGY",
            session_id="local-session"
        )
        
        token = create_access_token(mock_user)
        
        return LoginResponse(
            access_token=token,
            user_info={
                "user_id": mock_user.user_id,
                "username": mock_user.username,
                "roles": [role.value for role in mock_user.roles],
                "business_unit": mock_user.business_unit
            }
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials. Use admin/admin for local testing"
    )