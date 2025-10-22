"""
Banking-grade configuration management with security and compliance features
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with banking security requirements"""
    
    # Environment
    ENVIRONMENT: str = Field(default="production", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Debug mode (NEVER enable in production)")
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8080, description="API port")
    API_PREFIX: str = Field(default="/api/v1", description="API prefix")
    
    # Security Configuration
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens (REQUIRED)")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    
    # Banking-specific security
    REQUIRE_MFA: bool = Field(default=True, description="Require multi-factor authentication")
    SESSION_TIMEOUT_MINUTES: int = Field(default=15, description="Session timeout")
    MAX_LOGIN_ATTEMPTS: int = Field(default=3, description="Maximum login attempts")
    PASSWORD_MIN_LENGTH: int = Field(default=12, description="Minimum password length")
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=[
            "https://bankportal.internal",
            "https://documentloader-ui.bank.com"
        ],
        description="Allowed CORS origins"
    )
    
    # Trusted hosts (banking security requirement)
    ALLOWED_HOSTS: List[str] = Field(
        default=[
            "documentloader-api.bank.com",
            "localhost",
            "127.0.0.1"
        ],
        description="Allowed host headers"
    )
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/document_loader",
        description="Database connection URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow connections")
    
    # Document Loader CLI Integration
    DOCUMENT_LOADER_PATH: str = Field(
        default="/opt/document-loader",
        description="Path to document-loader CLI installation"
    )
    DOCUMENT_LOADER_TIMEOUT: int = Field(
        default=7200,  # 2 hours
        description="CLI operation timeout in seconds"
    )
    
    # Audit and Compliance
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=2555, description="Audit log retention (7 years)")
    ENABLE_DETAILED_AUDIT: bool = Field(default=True, description="Enable detailed audit logging")
    COMPLIANCE_MODE: str = Field(default="SOX", description="Compliance mode: SOX, GDPR, PCI")
    
    # Monitoring and Observability
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    STRUCTURED_LOGGING: bool = Field(default=True, description="Enable structured logging")
    
    # Business Configuration
    DEFAULT_BUSINESS_UNIT: str = Field(default="TECHNOLOGY", description="Default business unit")
    REQUIRE_BUSINESS_JUSTIFICATION: bool = Field(default=True, description="Require business justification")
    
    # Azure Integration (for banking environments)
    AZURE_KEY_VAULT_URL: Optional[str] = Field(default=None, description="Azure Key Vault URL")
    AZURE_TENANT_ID: Optional[str] = Field(default=None, description="Azure tenant ID")
    AZURE_CLIENT_ID: Optional[str] = Field(default=None, description="Azure client ID")
    
    # Control-M Integration
    CONTROLM_API_ENDPOINT: Optional[str] = Field(default=None, description="Control-M API endpoint")
    CONTROLM_TOKEN: Optional[str] = Field(default=None, description="Control-M API token")
    
    # Document Loader Database Configuration (from root .env)
    DOCUMENT_LOADER_DB_HOST: Optional[str] = Field(default=None, description="Document loader database host")
    DOCUMENT_LOADER_DB_PORT: Optional[int] = Field(default=None, description="Document loader database port")
    DOCUMENT_LOADER_DB_NAME: Optional[str] = Field(default=None, description="Document loader database name")
    DOCUMENT_LOADER_DB_USER: Optional[str] = Field(default=None, description="Document loader database user")
    DOCUMENT_LOADER_DB_PASSWORD: Optional[str] = Field(default=None, description="Document loader database password")
    DOCUMENT_LOADER_DB_MIN_POOL_SIZE: Optional[int] = Field(default=None, description="Document loader database min pool size")
    DOCUMENT_LOADER_DB_MAX_POOL_SIZE: Optional[int] = Field(default=None, description="Document loader database max pool size")
    
    # SharePoint Configuration (from root .env)
    SHAREPOINT_TENANT_ID: Optional[str] = Field(default=None, description="SharePoint tenant ID")
    SHAREPOINT_CLIENT_ID: Optional[str] = Field(default=None, description="SharePoint client ID")
    SHAREPOINT_CLIENT_SECRET: Optional[str] = Field(default=None, description="SharePoint client secret")
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("DEBUG")
    def validate_debug_in_production(cls, v, values):
        if values.get("ENVIRONMENT") == "production" and v:
            raise ValueError("DEBUG cannot be True in production environment")
        return v
    
    class Config:
        # Look for .env file in current directory first, then parent directories
        env_file = [".env", "../.env", "../../.env", "../../../.env"]
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Banking-specific configuration validation
def validate_banking_compliance():
    """Validate that configuration meets banking compliance requirements"""
    settings = get_settings()
    
    issues = []
    
    # Security validations
    if not settings.REQUIRE_MFA:
        issues.append("MFA must be required for banking applications")
    
    if settings.SESSION_TIMEOUT_MINUTES > 30:
        issues.append("Session timeout exceeds banking security guidelines (max 30 minutes)")
    
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 60:
        issues.append("Token expiration exceeds banking security guidelines (max 60 minutes)")
    
    if settings.ENVIRONMENT == "production":
        if settings.DEBUG:
            issues.append("DEBUG mode cannot be enabled in production")
        
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
            issues.append("Production requires strong SECRET_KEY (min 32 characters)")
        
        if not settings.ENABLE_DETAILED_AUDIT:
            issues.append("Detailed audit logging required for banking compliance")
    
    # Compliance validations
    if settings.AUDIT_LOG_RETENTION_DAYS < 2555:  # 7 years
        issues.append("Audit log retention must be at least 7 years for banking compliance")
    
    if issues:
        raise ValueError(f"Banking compliance validation failed: {issues}")
    
    return True