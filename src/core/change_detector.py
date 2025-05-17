from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..abstractions.file_source import FileMetadata
from ..data.models import FileRecord, FileStatus
from ..data.repository import Repository
from ..core.file_processor import FileProcessor

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
    new_hash: str = None
    existing_hash: str = None

class ChangeDetector:
    """Detects changes in files between sync runs."""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self.file_processor = FileProcessor()
    
    async def detect_changes(self, 
                           source_files: List[FileMetadata], 
                           knowledge_base_id: int,
                           calculate_hashes: bool = False) -> List[FileChange]:
        """Detect changes between source files and existing records.
        
        Args:
            source_files: List of file metadata from the source
            knowledge_base_id: ID of the knowledge base
            calculate_hashes: If True, calculates file hashes for accurate modification detection
        """
        changes = []
        
        # Get URIs from source files
        source_uris = {file.uri for file in source_files}
        source_files_map = {file.uri: file for file in source_files}
        
        # Get all existing file records for this knowledge base (from the last sync)
        last_sync_run = await self.repository.get_last_sync_run(knowledge_base_id)
        existing_records = []
        existing_records_map = {}
        
        if last_sync_run:
            existing_records = await self.repository.get_file_records_by_sync_run(last_sync_run.id)
            existing_records_map = {record.original_uri: record for record in existing_records}
        
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
                
                # If hash calculation is requested, compare actual file content
                if calculate_hashes:
                    # This is handled by the scanner/batch runner to avoid redundant content fetching
                    # Just mark as potentially modified based on metadata
                    if (metadata.modified_at > existing_record.created_at or
                        metadata.size != existing_record.file_size):
                        changes.append(FileChange(
                            uri=uri,
                            change_type=ChangeType.MODIFIED,
                            metadata=metadata,
                            existing_record=existing_record,
                            existing_hash=existing_record.file_hash
                        ))
                    else:
                        changes.append(FileChange(
                            uri=uri,
                            change_type=ChangeType.UNCHANGED,
                            metadata=metadata,
                            existing_record=existing_record,
                            existing_hash=existing_record.file_hash
                        ))
                else:
                    # Use metadata comparison only
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
        
        # Detect deleted files
        for uri, existing_record in existing_records_map.items():
            if uri not in source_uris:
                changes.append(FileChange(
                    uri=uri,
                    change_type=ChangeType.DELETED,
                    existing_record=existing_record
                ))
        
        return changes
    
    async def compare_file_hashes(self, file_hash: str, existing_record: FileRecord) -> bool:
        """Compare a file hash with an existing record's hash.
        
        Returns:
            True if the hashes are the same (file unchanged), False if different (file modified)
        """
        return file_hash == existing_record.file_hash
    
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
    
    def get_actionable_changes(self, changes: List[FileChange]) -> List[FileChange]:
        """Get only the changes that require action (new, modified, or deleted files)."""
        return [
            change for change in changes 
            if change.change_type in [ChangeType.NEW, ChangeType.MODIFIED, ChangeType.DELETED]
        ]
    
    def filter_changes_by_type(self, changes: List[FileChange], change_types: List[ChangeType]) -> List[FileChange]:
        """Filter changes by specific change types."""
        return [
            change for change in changes 
            if change.change_type in change_types
        ]