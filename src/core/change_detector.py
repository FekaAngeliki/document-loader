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
                           calculate_hashes: bool = True) -> List[FileChange]:
        """Detect changes between source files and existing records using hash comparison.
        
        Args:
            source_files: List of file metadata from the source
            knowledge_base_id: ID of the knowledge base
            calculate_hashes: Always True - we only use hash-based comparison
        """
        changes = []
        
        # Get URIs from source files
        source_uris = {file.uri for file in source_files}
        source_files_map = {file.uri: file for file in source_files}
        
        # Get the knowledge base name from ID
        knowledge_base = await self.repository.get_knowledge_base(knowledge_base_id)
        existing_records_map = {}
        
        if knowledge_base:
            # Get the latest file records across ALL sync runs for this knowledge base
            all_latest_records = await self.repository.get_latest_file_records_for_kb(knowledge_base.name)
            existing_records_map = {record.original_uri: record for record in all_latest_records}
        
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
                # Existing file - will be checked by hash comparison later
                existing_record = existing_records_map[uri]
                
                # For existing files, we'll mark them all as potentially modified
                # The batch runner will calculate hashes and determine the actual status
                changes.append(FileChange(
                    uri=uri,
                    change_type=ChangeType.MODIFIED,  # Will be verified by hash
                    metadata=metadata,
                    existing_record=existing_record,
                    existing_hash=existing_record.file_hash
                ))
        
        # Detect deleted files (files that existed in previous runs but not in current source)
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