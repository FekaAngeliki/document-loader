"""
Enhanced data models for multi-source Knowledge Bases

Extends the existing models to support multiple sources feeding into a single RAG system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from .models import SyncRunStatus, FileStatus

@dataclass
class SourceDefinition:
    """Definition of a source within a knowledge base."""
    source_id: str                              # Unique identifier within the KB
    source_type: str                           # Type: enterprise_sharepoint, file_system, etc.
    source_config: Dict[str, Any]              # Source-specific configuration
    enabled: bool = True                       # Whether this source is active
    sync_schedule: Optional[str] = None        # Cron expression for scheduling
    metadata_tags: Dict[str, str] = field(default_factory=dict)  # Additional metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class MultiSourceKnowledgeBase:
    """Knowledge Base that can aggregate multiple sources into single RAG."""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    
    # RAG system configuration (single RAG for all sources)
    rag_type: str = ""
    rag_config: Dict[str, Any] = field(default_factory=dict)
    
    # Multiple source definitions
    sources: List[SourceDefinition] = field(default_factory=list)
    
    # Global settings
    file_organization: Dict[str, Any] = field(default_factory=dict)
    sync_strategy: Dict[str, Any] = field(default_factory=dict)
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass 
class MultiSourceSyncRun:
    """Sync run for multi-source knowledge base."""
    id: Optional[int] = None
    knowledge_base_id: int = 0
    start_time: datetime = None
    end_time: Optional[datetime] = None
    status: str = SyncRunStatus.RUNNING.value
    
    # Overall statistics
    total_files: Optional[int] = None
    new_files: Optional[int] = None
    modified_files: Optional[int] = None
    deleted_files: Optional[int] = None
    error_message: Optional[str] = None
    
    # Per-source statistics
    source_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Sync strategy used
    sync_mode: str = "parallel"  # parallel, sequential, selective
    sources_processed: List[str] = field(default_factory=list)
    
    created_at: Optional[datetime] = None

@dataclass
class EnhancedFileRecord:
    """File record with source tracking and enhanced metadata."""
    id: Optional[int] = None
    sync_run_id: int = 0
    
    # Source information
    source_id: str = ""                        # Which source this file came from
    source_type: str = ""                      # Type of source
    source_path: str = ""                      # Original path in source system
    
    # File information
    original_uri: str = ""
    rag_uri: str = ""
    file_hash: str = ""
    uuid_filename: str = ""
    upload_time: Optional[datetime] = None
    file_size: int = 0
    content_type: str = ""
    
    # Status and processing
    status: str = FileStatus.NEW.value
    error_message: Optional[str] = None
    
    # Enhanced metadata
    source_metadata: Dict[str, Any] = field(default_factory=dict)  # Source-specific metadata
    rag_metadata: Dict[str, Any] = field(default_factory=dict)     # RAG system metadata
    tags: List[str] = field(default_factory=list)                 # Searchable tags
    
    # Timestamps
    source_created_at: Optional[datetime] = None
    source_modified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SyncMode(Enum):
    """Sync modes for multi-source knowledge bases."""
    PARALLEL = "parallel"         # Sync all sources simultaneously
    SEQUENTIAL = "sequential"     # Sync sources one after another
    SELECTIVE = "selective"       # Sync only specified sources
    INCREMENTAL = "incremental"   # Only sync changed files

@dataclass
class SourceSyncStatus:
    """Status tracking for individual source within a sync run."""
    source_id: str
    status: str = SyncRunStatus.RUNNING.value
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    files_processed: int = 0
    files_new: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    files_error: int = 0
    error_message: Optional[str] = None
    
def create_multi_source_kb_from_config(config: Dict[str, Any]) -> MultiSourceKnowledgeBase:
    """Create a MultiSourceKnowledgeBase from configuration dictionary."""
    
    # Parse sources
    sources = []
    for source_config in config.get("sources", []):
        source = SourceDefinition(
            source_id=source_config["source_id"],
            source_type=source_config["source_type"],
            source_config=source_config["source_config"],
            enabled=source_config.get("enabled", True),
            sync_schedule=source_config.get("sync_schedule"),
            metadata_tags=source_config.get("metadata_tags", {})
        )
        sources.append(source)
    
    # Create knowledge base
    kb = MultiSourceKnowledgeBase(
        name=config["name"],
        description=config.get("description", ""),
        rag_type=config["rag_type"],
        rag_config=config["rag_config"],
        sources=sources,
        file_organization=config.get("file_organization", {}),
        sync_strategy=config.get("sync_strategy", {})
    )
    
    return kb

def convert_to_legacy_kb(multi_kb: MultiSourceKnowledgeBase, source_id: str):
    """Convert a multi-source KB to legacy format for backward compatibility."""
    from .models import KnowledgeBase
    
    # Find the specific source
    source = next((s for s in multi_kb.sources if s.source_id == source_id), None)
    if not source:
        raise ValueError(f"Source {source_id} not found in knowledge base")
    
    return KnowledgeBase(
        id=multi_kb.id,
        name=f"{multi_kb.name}_{source_id}",
        source_type=source.source_type,
        source_config=source.source_config,
        rag_type=multi_kb.rag_type,
        rag_config=multi_kb.rag_config,
        created_at=multi_kb.created_at,
        updated_at=multi_kb.updated_at
    )