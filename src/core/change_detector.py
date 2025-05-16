from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..abstractions.file_source import FileMetadata
from ..data.models import FileRecord, FileStatus
from ..data.repository import Repository

class ChangeType(Enum):
    NEW = "new"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    DELETED = "deleted"

@dataclass
class FileChange:
    """Represents a change to a file."""
    uri: str
    change_type: ChangeType
    metadata: FileMetadata = None
    existing_record: FileRecord = None

class ChangeDetector:
    """Detects changes in files between sync runs."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
    
    async def detect_changes(self, 
                           source_files: List[FileMetadata], 
                           knowledge_base_id: int) -> List[FileChange]:
        """Detect changes between source files and existing records."""
        changes = []
        
        # Get URIs from source files
        source_uris = {file.uri for file in source_files}
        source_files_map = {file.uri: file for file in source_files}
        
        # Get existing file records for this knowledge base
        existing_records_map = {}
        for uri in source_uris:
            record = await self.repository.get_file_record_by_uri(uri, knowledge_base_id)
            if record:
                existing_records_map[uri] = record
        
        # Detect new and modified files
        for uri, metadata in source_files_map.items():
            if uri not in existing_records_map:
                # New file
                changes.append(FileChange(
                    uri=uri,
                    change_type=ChangeType.NEW,
                    metadata=metadata
                ))
            else:
                # Existing file - check if modified
                existing_record = existing_records_map[uri]
                
                # Compare modification time or size to detect changes
                if (metadata.modified_at > existing_record.created_at or
                    metadata.size != existing_record.file_size):
                    changes.append(FileChange(
                        uri=uri,
                        change_type=ChangeType.MODIFIED,
                        metadata=metadata,
                        existing_record=existing_record
                    ))
                else:
                    changes.append(FileChange(
                        uri=uri,
                        change_type=ChangeType.UNCHANGED,
                        metadata=metadata,
                        existing_record=existing_record
                    ))
        
        # TODO: Detect deleted files
        # This would require comparing with all files from the last sync run
        # For now, we'll skip deletion detection
        
        return changes
    
    def get_change_summary(self, changes: List[FileChange]) -> Dict[str, int]:
        """Get a summary of changes by type."""
        summary = {
            "new": 0,
            "modified": 0,
            "unchanged": 0,
            "deleted": 0
        }
        
        for change in changes:
            summary[change.change_type.value] += 1
        
        return summary