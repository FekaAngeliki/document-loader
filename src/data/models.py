from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class SyncRunStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SCAN_RUNNING = "scan_running"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"

class FileStatus(Enum):
    NEW = "new"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    DELETED = "deleted"
    ERROR = "error"
    SCANNED = "scanned"
    SCAN_ERROR = "scan_error"

@dataclass
class KnowledgeBase:
    id: Optional[int] = None
    name: str = ""
    source_type: str = ""
    source_config: Dict[str, Any] = None
    rag_type: str = ""
    rag_config: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class SyncRun:
    id: Optional[int] = None
    knowledge_base_id: int = 0
    start_time: datetime = None
    end_time: Optional[datetime] = None
    status: str = SyncRunStatus.RUNNING.value
    total_files: Optional[int] = None
    new_files: Optional[int] = None
    modified_files: Optional[int] = None
    deleted_files: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass
class FileRecord:
    id: Optional[int] = None
    sync_run_id: int = 0
    original_uri: str = ""
    rag_uri: str = ""
    file_hash: str = ""
    uuid_filename: str = ""
    upload_time: datetime = None
    file_size: int = 0
    status: str = FileStatus.NEW.value
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass
class SourceType:
    id: Optional[int] = None
    name: str = ""
    class_name: str = ""
    config_schema: Dict[str, Any] = None

@dataclass
class RagType:
    id: Optional[int] = None
    name: str = ""
    class_name: str = ""
    config_schema: Dict[str, Any] = None