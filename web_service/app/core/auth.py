"""
Banking-grade authentication and authorization system

Implements:
- JWT token authentication
- Role-based access control (RBAC)
- Multi-factor authentication support
- Session management
- Audit logging of authentication events
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import structlog
from enum import Enum

from .config import get_settings
from .audit import create_audit_event


logger = structlog.get_logger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security
security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """Banking user roles with hierarchical permissions"""
    SUPER_ADMIN = "super_admin"
    IT_ADMIN = "it_admin"
    BUSINESS_ADMIN = "business_admin"
    DATA_STEWARD = "data_steward"
    BUSINESS_ANALYST = "business_analyst"
    COMPLIANCE_OFFICER = "compliance_officer"
    AUDITOR = "auditor"
    READ_ONLY = "read_only"
    # Schema management roles
    ADMIN = "admin"
    SCHEMA_MANAGER = "schema_manager"
    CONFIG_MANAGER = "config_manager"
    KB_MANAGER = "kb_manager"
    SYNC_OPERATOR = "sync_operator"


class Permission(str, Enum):
    """Granular permissions for document loader operations"""
    # Knowledge Base Operations
    KB_CREATE = "kb:create"
    KB_READ = "kb:read"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"
    KB_SYNC = "kb:sync"
    
    # Configuration Management
    CONFIG_CREATE = "config:create"
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"
    CONFIG_DELETE = "config:delete"
    
    # Administrative Operations
    ADMIN_USER_MANAGEMENT = "admin:users"
    ADMIN_SYSTEM_CONFIG = "admin:system"
    ADMIN_AUDIT_LOGS = "admin:audit"
    
    # Scheduler Operations
    SCHEDULER_READ = "scheduler:read"
    SCHEDULER_MANAGE = "scheduler:manage"
    SCHEDULER_TRIGGER = "scheduler:trigger"
    
    # Connectivity Testing Operations
    CONNECTIVITY_READ = "connectivity:read"
    CONNECTIVITY_TEST = "connectivity:test"
    
    # Emergency Operations
    EMERGENCY_SYNC = "emergency:sync"
    EMERGENCY_OVERRIDE = "emergency:override"
    
    # Schema Management Operations
    SCHEMA_CREATE = "schema:create"
    SCHEMA_READ = "schema:read"
    SCHEMA_DELETE = "schema:delete"
    SCHEMA_MANAGE = "schema:manage"


# Role-Permission Mapping (Banking RBAC)
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: [p for p in Permission],  # All permissions
    UserRole.IT_ADMIN: [
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_DELETE, Permission.KB_SYNC,
        Permission.CONFIG_CREATE, Permission.CONFIG_READ, Permission.CONFIG_UPDATE, Permission.CONFIG_DELETE,
        Permission.SCHEDULER_READ, Permission.SCHEDULER_MANAGE, Permission.SCHEDULER_TRIGGER,
        Permission.CONNECTIVITY_READ, Permission.CONNECTIVITY_TEST,
        Permission.ADMIN_SYSTEM_CONFIG, Permission.EMERGENCY_SYNC
    ],
    UserRole.BUSINESS_ADMIN: [
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_SYNC,
        Permission.CONFIG_READ, Permission.CONFIG_UPDATE,
        Permission.SCHEDULER_READ, Permission.SCHEDULER_TRIGGER,
        Permission.CONNECTIVITY_READ, Permission.CONNECTIVITY_TEST
    ],
    UserRole.DATA_STEWARD: [
        Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_SYNC,
        Permission.CONFIG_READ,
        Permission.CONNECTIVITY_READ
    ],
    UserRole.BUSINESS_ANALYST: [
        Permission.KB_READ, Permission.KB_SYNC,
        Permission.CONFIG_READ
    ],
    UserRole.COMPLIANCE_OFFICER: [
        Permission.KB_READ, Permission.CONFIG_READ,
        Permission.ADMIN_AUDIT_LOGS
    ],
    UserRole.AUDITOR: [
        Permission.KB_READ, Permission.CONFIG_READ,
        Permission.ADMIN_AUDIT_LOGS
    ],
    UserRole.READ_ONLY: [
        Permission.KB_READ, Permission.CONFIG_READ
    ],
    # Schema Management Roles
    UserRole.ADMIN: [p for p in Permission],  # All permissions including schema operations
    UserRole.SCHEMA_MANAGER: [
        Permission.SCHEMA_CREATE, Permission.SCHEMA_READ, Permission.SCHEMA_DELETE, Permission.SCHEMA_MANAGE,
        Permission.KB_READ, Permission.CONFIG_READ
    ],
    UserRole.CONFIG_MANAGER: [
        Permission.CONFIG_CREATE, Permission.CONFIG_READ, Permission.CONFIG_UPDATE, Permission.CONFIG_DELETE,
        Permission.KB_READ, Permission.SCHEMA_READ
    ],
    UserRole.KB_MANAGER: [
        Permission.KB_CREATE, Permission.KB_READ, Permission.KB_UPDATE, Permission.KB_DELETE, Permission.KB_SYNC,
        Permission.CONFIG_READ, Permission.SCHEMA_READ
    ],
    UserRole.SYNC_OPERATOR: [
        Permission.KB_READ, Permission.KB_SYNC,
        Permission.CONFIG_READ, Permission.SCHEMA_READ,
        Permission.CONNECTIVITY_READ, Permission.CONNECTIVITY_TEST
    ]
}


class User(BaseModel):
    """User model with banking-specific attributes"""
    user_id: str
    username: str
    email: str
    full_name: str
    roles: List[UserRole]
    business_unit: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    mfa_enabled: bool = True
    session_id: Optional[str] = None


class TokenData(BaseModel):
    """JWT token payload"""
    user_id: str
    username: str
    roles: List[str]
    business_unit: str
    session_id: str
    iat: datetime
    exp: datetime


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token for authenticated user"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "user_id": user.user_id,
        "username": user.username,
        "roles": [role.value for role in user.roles],
        "business_unit": user.business_unit,
        "session_id": user.session_id,
        "iat": datetime.utcnow(),
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Audit token creation
    create_audit_event(
        event_type="authentication",
        action="token_created",
        user_id=user.user_id,
        details={
            "username": user.username,
            "expires_at": expire.isoformat(),
            "session_id": user.session_id
        }
    )
    
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        roles: List[str] = payload.get("roles", [])
        business_unit: str = payload.get("business_unit")
        session_id: str = payload.get("session_id")
        
        if user_id is None or username is None:
            raise AuthenticationError("Invalid token payload")
        
        token_data = TokenData(
            user_id=user_id,
            username=username,
            roles=roles,
            business_unit=business_unit,
            session_id=session_id,
            iat=datetime.fromtimestamp(payload.get("iat")),
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
        
        return token_data
        
    except JWTError as e:
        logger.warning("JWT token verification failed", error=str(e))
        raise AuthenticationError("Invalid token")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Get current authenticated user from JWT token"""
    
    # DEVELOPMENT MODE: Bypass authentication for localhost
    if settings.ENVIRONMENT == "development":
        logger.info("Development mode: bypassing authentication")
        
        # Create a mock development user
        dev_user = User(
            user_id="dev-user-001",
            username="dev-admin",
            email="dev-admin@localhost",
            full_name="Development Admin",
            roles=[UserRole.SUPER_ADMIN],
            business_unit="TECHNOLOGY",
            session_id="dev-session"
        )
        
        request.state.current_user = dev_user
        return dev_user
    
    if not credentials:
        create_audit_event(
            event_type="authentication",
            action="missing_credentials",
            details={"ip_address": request.client.host}
        )
        raise AuthenticationError("Missing authentication credentials")
    
    token_data = verify_token(credentials.credentials)
    
    # In a real banking environment, you would fetch user from database
    # Here we'll create a user object from token data
    user = User(
        user_id=token_data.user_id,
        username=token_data.username,
        email=f"{token_data.username}@bank.com",
        full_name=token_data.username.replace(".", " ").title(),
        roles=[UserRole(role) for role in token_data.roles],
        business_unit=token_data.business_unit,
        session_id=token_data.session_id
    )
    
    # Check if session is still valid (in production, check against session store)
    if token_data.exp < datetime.utcnow():
        create_audit_event(
            event_type="authentication",
            action="token_expired",
            user_id=user.user_id,
            details={"expired_at": token_data.exp.isoformat()}
        )
        raise AuthenticationError("Token has expired")
    
    # Update last seen
    request.state.current_user = user
    
    return user


def require_permission(permission: Permission):
    """Decorator to require specific permission for endpoint access"""
    def decorator(user: User = Depends(get_current_user)):
        user_permissions = []
        for role in user.roles:
            user_permissions.extend(ROLE_PERMISSIONS.get(role, []))
        
        if permission not in user_permissions:
            create_audit_event(
                event_type="authorization",
                action="permission_denied",
                user_id=user.user_id,
                details={
                    "required_permission": permission.value,
                    "user_roles": [role.value for role in user.roles],
                    "user_permissions": [p.value for p in user_permissions]
                }
            )
            raise AuthorizationError(f"Missing required permission: {permission.value}")
        
        return user
    return decorator


def require_roles(required_roles: List[UserRole]):
    """Decorator to require specific roles for endpoint access"""
    def decorator(user: User = Depends(get_current_user)):
        if not any(role in user.roles for role in required_roles):
            create_audit_event(
                event_type="authorization",
                action="role_denied",
                user_id=user.user_id,
                details={
                    "required_roles": [role.value for role in required_roles],
                    "user_roles": [role.value for role in user.roles]
                }
            )
            raise AuthorizationError(f"Missing required role: {[r.value for r in required_roles]}")
        
        return user
    return decorator


def require_business_unit(allowed_units: List[str]):
    """Decorator to restrict access by business unit"""
    def decorator(user: User = Depends(get_current_user)):
        if user.business_unit not in allowed_units:
            create_audit_event(
                event_type="authorization",
                action="business_unit_denied",
                user_id=user.user_id,
                details={
                    "user_business_unit": user.business_unit,
                    "allowed_units": allowed_units
                }
            )
            raise AuthorizationError(f"Access denied for business unit: {user.business_unit}")
        
        return user
    return decorator


# Common permission dependencies for banking operations
RequireKBRead = Depends(require_permission(Permission.KB_READ))
RequireKBSync = Depends(require_permission(Permission.KB_SYNC))
RequireKBAdmin = Depends(require_permission(Permission.KB_CREATE))
RequireConfigRead = Depends(require_permission(Permission.CONFIG_READ))
RequireConfigAdmin = Depends(require_permission(Permission.CONFIG_CREATE))
RequireAuditAccess = Depends(require_permission(Permission.ADMIN_AUDIT_LOGS))
RequireEmergencyAccess = Depends(require_permission(Permission.EMERGENCY_SYNC))

# Scheduler permissions
RequireSchedulerRead = Depends(require_permission(Permission.SCHEDULER_READ))
RequireSchedulerManage = Depends(require_permission(Permission.SCHEDULER_MANAGE))
RequireSchedulerTrigger = Depends(require_permission(Permission.SCHEDULER_TRIGGER))

# Connectivity permissions
RequireConnectivityRead = Depends(require_permission(Permission.CONNECTIVITY_READ))
RequireConnectivityTest = Depends(require_permission(Permission.CONNECTIVITY_TEST))

# Convenience class for easier imports
class Permissions:
    KB_READ = Permission.KB_READ
    KB_SYNC = Permission.KB_SYNC
    KB_CREATE = Permission.KB_CREATE
    CONFIG_READ = Permission.CONFIG_READ
    SCHEDULER_READ = Permission.SCHEDULER_READ
    SCHEDULER_MANAGE = Permission.SCHEDULER_MANAGE
    SCHEDULER_TRIGGER = Permission.SCHEDULER_TRIGGER
    CONNECTIVITY_READ = Permission.CONNECTIVITY_READ
    CONNECTIVITY_TEST = Permission.CONNECTIVITY_TEST