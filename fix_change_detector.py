#!/usr/bin/env python3
"""
Fix the change detector to look for existing files across all sync runs
"""

# Show the fixed change detector implementation
fixed_change_detector = '''
async def detect_changes(self, 
                        source_files: List[FileMetadata], 
                        knowledge_base_id: int,
                        calculate_hashes: bool = False) -> List[FileChange]:
    """Detect changes between source files and existing records.
    
    This version looks for existing files across ALL sync runs,
    not just the last one.
    """
    changes = []
    
    # Get URIs from source files
    source_uris = {file.uri for file in source_files}
    source_files_map = {file.uri: file for file in source_files}
    
    # Get ALL existing file records for this knowledge base
    existing_records_map = await self.get_all_kb_files(knowledge_base_id)
    
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
            
            # ... rest of the logic remains the same
'''

print("The issue is that the change detector only looks at the LAST sync run.")
print("If that sync run didn't find the files (marked them as new), the next run will also mark them as new.")
print("\nWe need to modify the change detector to look for existing files across ALL sync runs.")
print("\nHere's what we need to add to the Repository class:")

repository_method = '''
async def get_latest_file_records_for_kb(self, knowledge_base_id: int) -> Dict[str, FileRecord]:
    """Get the most recent file record for each unique file URI in a knowledge base."""
    query = """
        WITH latest_records AS (
            SELECT DISTINCT ON (original_uri) 
                fr.id, fr.sync_run_id, fr.original_uri, fr.rag_uri, 
                fr.file_hash, fr.uuid_filename, fr.upload_time, 
                fr.file_size, fr.status, fr.error_message, fr.created_at
            FROM file_record fr
            JOIN sync_run sr ON fr.sync_run_id = sr.id
            WHERE sr.knowledge_base_id = $1
            ORDER BY original_uri, fr.created_at DESC
        )
        SELECT * FROM latest_records
    """
    
    rows = await self.db.fetch(query, knowledge_base_id)
    records_map = {}
    
    for row in rows:
        record = FileRecord(
            id=row['id'],
            sync_run_id=row['sync_run_id'],
            original_uri=row['original_uri'],
            rag_uri=row['rag_uri'],
            file_hash=row['file_hash'],
            uuid_filename=row['uuid_filename'],
            upload_time=row['upload_time'],
            file_size=row['file_size'],
            status=row['status'],
            error_message=row['error_message'],
            created_at=row['created_at']
        )
        records_map[record.original_uri] = record
    
    return records_map
'''

print(repository_method)

print("\nAnd modify the change detector:")

change_detector_fix = '''
async def detect_changes(self, 
                        source_files: List[FileMetadata], 
                        knowledge_base_id: int,
                        calculate_hashes: bool = False) -> List[FileChange]:
    """Detect changes between source files and existing records."""
    changes = []
    
    # Get URIs from source files
    source_uris = {file.uri for file in source_files}
    source_files_map = {file.uri: file for file in source_files}
    
    # Get the latest record for each file across ALL sync runs
    existing_records_map = await self.repository.get_latest_file_records_for_kb(knowledge_base_id)
    
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
            
            # Rest of the logic remains the same...
'''

print(change_detector_fix)