# UUID Consistency Implementation

## Overview

The document loader now maintains a consistent UUID mapping from original filenames/filepaths to UUID-based filenames. Once a UUID is assigned to a file during the first scan/upload, it remains consistent across all subsequent operations.

## Why UUID Consistency Matters

1. **Stable RAG URIs**: The RAG system uses the UUID filename to create URIs (e.g., `/kb-name/uuid-filename.pdf`)
2. **Update Tracking**: Modified files retain the same UUID, allowing proper updates in the RAG system
3. **Audit Trail**: Consistent UUIDs enable tracking of file history and changes over time
4. **Data Integrity**: Prevents duplicate entries in the RAG system for the same source file

## Implementation Details

### File Processor Changes

The `FileProcessor` class now accepts an optional `existing_uuid` parameter:

```python
def generate_uuid_filename(self, original_filename: str, existing_uuid: Optional[str] = None) -> str:
    """Generate a UUID-based filename or use existing UUID."""
    file_extension = ""
    if '.' in original_filename:
        file_extension = '.' + original_filename.split('.')[-1]
    
    # If we have an existing UUID, preserve it
    if existing_uuid:
        # Extract just the UUID part if it includes extension
        if '.' in existing_uuid:
            uuid_part = existing_uuid.split('.')[0]
        else:
            uuid_part = existing_uuid
        return f"{uuid_part}{file_extension}"
    
    # Generate new UUID only if none exists
    return f"{uuid.uuid4()}{file_extension}"
```

### Scanner Updates

The scanner now:
1. Checks if a file already has a UUID in the database
2. Uses the existing UUID if found
3. Only generates a new UUID for new files

```python
# Check for existing record and get existing UUID
existing_uuid = None
if change_detector and kb:
    existing_record = await repository.get_file_record_by_uri(file_metadata.uri, kb.id)
    if existing_record:
        existing_uuid = existing_record.uuid_filename

# Generate UUID filename - use existing if available
uuid_filename = self.file_processor.generate_uuid_filename(
    file_metadata.uri, 
    existing_uuid=existing_uuid
)
```

### Batch Runner Updates

The batch runner follows a similar pattern during uploads:

```python
# Get existing UUID if this is a modified file
existing_uuid = None
if change.existing_record:
    existing_uuid = change.existing_record.uuid_filename

# Process file - use existing UUID if available
file_hash, uuid_filename, rag_uri = await self.file_processor.process_file(
    content, change.uri, kb_name, existing_uuid
)
```

## Database Considerations

The UUID consistency is maintained through:
1. The `file_record` table stores the `uuid_filename` for each file
2. The `get_file_record_by_uri()` method retrieves existing records
3. New records preserve the UUID when updating files

## Benefits

1. **Predictable RAG URIs**: The same file always maps to the same RAG URI
2. **Efficient Updates**: Modified files update the existing RAG document instead of creating duplicates
3. **Better Tracking**: File history is preserved through consistent UUIDs
4. **Reduced Storage**: Prevents duplicate documents in the RAG system

## Example Flow

### First Scan/Upload
1. File: `/data/report.pdf` (no existing record)
2. Generate new UUID: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
3. UUID filename: `a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf`
4. RAG URI: `/my-kb/a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf`

### Subsequent Scan/Upload (File Modified)
1. File: `/data/report.pdf` (existing record found)
2. Retrieve existing UUID: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
3. UUID filename: `a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf` (same)
4. RAG URI: `/my-kb/a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf` (same)
5. Result: RAG document is updated, not duplicated

## Console Output

The consistent UUID mapping is visible in the console output:

```
[~] /data/report.pdf | UUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf | Hash: abc123... | Size: 1.2MB | Type: application/pdf
```

Even after modifications, the same file retains its UUID:

```
[~] /data/report.pdf | UUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf | Hash: def456... | Size: 1.3MB | Type: application/pdf
```

## Future Enhancements

1. **UUID Migration**: Tool to regenerate UUIDs if needed
2. **UUID Lookup API**: Quick API to find UUID by original path
3. **UUID History**: Track all historical UUIDs for a file
4. **Collision Detection**: Handle the extremely rare case of UUID collisions