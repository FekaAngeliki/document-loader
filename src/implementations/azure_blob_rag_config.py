"""
Azure Blob RAG System Configuration Schema
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class AzureAuthMethod(Enum):
    """Azure authentication methods"""
    CONNECTION_STRING = "connection_string"
    SERVICE_PRINCIPAL = "service_principal"
    MANAGED_IDENTITY = "managed_identity"
    DEFAULT_CREDENTIAL = "default_credential"

class AzureStorageRedundancy(Enum):
    """Azure storage redundancy options"""
    LRS = "Standard_LRS"  # Locally redundant storage
    ZRS = "Standard_ZRS"  # Zone-redundant storage
    GRS = "Standard_GRS"  # Geo-redundant storage
    RAGRS = "Standard_RAGRS"  # Read-access geo-redundant storage

@dataclass
class AzureBlobConfig:
    """Azure Blob Storage configuration"""
    # Container settings
    container_name: str
    storage_account_name: str
    
    # Optional settings
    public_access_level: str = "private"  # private, blob, container
    enable_versioning: bool = False
    enable_soft_delete: bool = True
    soft_delete_retention_days: int = 7
    
@dataclass
class AzureSearchConfig:
    """Azure Cognitive Search configuration (optional)"""
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    index_name: Optional[str] = None
    enable_semantic_search: bool = False
    use_skillset: bool = False
    skillset_name: Optional[str] = None

@dataclass
class AzureServicePrincipalAuth:
    """Service Principal authentication configuration"""
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str

@dataclass
class AzureResourceConfig:
    """Azure resource configuration"""
    resource_group_name: str
    location: str = "eastus"
    storage_redundancy: AzureStorageRedundancy = AzureStorageRedundancy.LRS

@dataclass
class AzureBlobRAGConfig:
    """Complete Azure Blob RAG System configuration"""
    # Authentication (one of these must be provided)
    auth_method: AzureAuthMethod
    
    # Auth method specific configs
    connection_string: Optional[str] = None
    service_principal: Optional[AzureServicePrincipalAuth] = None
    use_managed_identity: bool = False
    
    # Storage configuration
    blob_config: AzureBlobConfig = None
    
    # Resource configuration
    resource_config: AzureResourceConfig = None
    
    # Optional Azure Search integration
    search_config: Optional[AzureSearchConfig] = None
    
    # Performance settings
    max_concurrent_uploads: int = 5
    max_upload_retry_attempts: int = 3
    upload_timeout_seconds: int = 300
    
    # Blob settings
    blob_tier: str = "hot"  # hot, cool, archive
    enable_blob_indexing: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        config = {
            "auth_method": self.auth_method.value,
            "connection_string": self.connection_string,
            "use_managed_identity": self.use_managed_identity,
            "max_concurrent_uploads": self.max_concurrent_uploads,
            "max_upload_retry_attempts": self.max_upload_retry_attempts,
            "upload_timeout_seconds": self.upload_timeout_seconds,
            "blob_tier": self.blob_tier,
            "enable_blob_indexing": self.enable_blob_indexing
        }
        
        if self.service_principal:
            config["service_principal"] = asdict(self.service_principal)
            
        if self.blob_config:
            config["blob_config"] = asdict(self.blob_config)
            
        if self.resource_config:
            config["resource_config"] = {
                **asdict(self.resource_config),
                "storage_redundancy": self.resource_config.storage_redundancy.value
            }
            
        if self.search_config:
            config["search_config"] = asdict(self.search_config)
            
        return config
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'AzureBlobRAGConfig':
        """Create configuration from dictionary"""
        auth_method = AzureAuthMethod(config.get("auth_method", AzureAuthMethod.SERVICE_PRINCIPAL.value))
        
        # Parse service principal auth if present
        service_principal = None
        if "service_principal" in config:
            sp_config = config["service_principal"]
            service_principal = AzureServicePrincipalAuth(**sp_config)
        
        # Parse blob config
        blob_config = None
        if "blob_config" in config:
            blob_config = AzureBlobConfig(**config["blob_config"])
        
        # Parse resource config
        resource_config = None
        if "resource_config" in config:
            rc = config["resource_config"].copy()
            if "storage_redundancy" in rc:
                rc["storage_redundancy"] = AzureStorageRedundancy(rc["storage_redundancy"])
            resource_config = AzureResourceConfig(**rc)
        
        # Parse search config
        search_config = None
        if "search_config" in config:
            search_config = AzureSearchConfig(**config["search_config"])
        
        return cls(
            auth_method=auth_method,
            connection_string=config.get("connection_string"),
            service_principal=service_principal,
            use_managed_identity=config.get("use_managed_identity", False),
            blob_config=blob_config,
            resource_config=resource_config,
            search_config=search_config,
            max_concurrent_uploads=config.get("max_concurrent_uploads", 5),
            max_upload_retry_attempts=config.get("max_upload_retry_attempts", 3),
            upload_timeout_seconds=config.get("upload_timeout_seconds", 300),
            blob_tier=config.get("blob_tier", "hot"),
            enable_blob_indexing=config.get("enable_blob_indexing", True)
        )

def get_default_config() -> AzureBlobRAGConfig:
    """Get default Azure Blob RAG configuration"""
    return AzureBlobRAGConfig(
        auth_method=AzureAuthMethod.SERVICE_PRINCIPAL,
        blob_config=AzureBlobConfig(
            container_name="documents",
            storage_account_name="mystorageaccount"
        ),
        resource_config=AzureResourceConfig(
            resource_group_name="myresourcegroup",
            location="eastus"
        )
    )