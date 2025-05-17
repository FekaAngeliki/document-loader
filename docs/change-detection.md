# Change Detection Implementation

## Overview

The document loader now includes comprehensive change detection functionality that compares files against previous scans/uploads using hash codes. This ensures efficient synchronization by only processing files that have actually changed.

## Features

### 1. Change Detection During Scan

When running a scan, the system now:
- Compares each file against the most recent file records in the database
- Uses SHA-256 hash comparison to detect actual content changes
- Categorizes files as: new, modified, unchanged, or deleted
- Displays visual indicators for each change type
- Shows a summary table of all detected changes

### 2. Change Detection During Upload

When running the upload (sync) process, the system:
- Lists all files from the source
- Detects changes compared to the last sync run
- Shows a change summary before processing
- Only uploads new or modified files
- Skips unchanged files to save time and resources
- Tracks deleted files for future handling

### 3. Real-time Database Updates

The database is updated in real-time during both scan and upload operations:
- Each file record is created immediately after processing
- Sync run statistics are updated continuously
- Error states are captured and stored
- Change history is preserved for auditing

## Visual Indicators

The system uses color-coded indicators for different change types:
- `[+]` Green: New files
- `[~]` Yellow: Modified files
- `[=]` Dim: Unchanged files
- `[-]` Red: Deleted files

## Change Summary Tables

Both scan and upload operations display summary tables showing:
- Count of files by change type
- Total files processed
- Processing duration
- Error count (if any)

## Database Schema Updates

The implementation leverages the existing database schema:
- `sync_run` table tracks statistics for each operation
- `file_record` table stores hash codes for comparison
- New repository methods support change detection queries

## Example Output

### Scan Operation
```
Scanning files... [10]
[+] /path/to/new-file.txt | UUID: abc123... | Hash: def456... | Size: 1.2KB | Type: text/plain
[~] /path/to/modified.pdf | UUID: ghi789... | Hash: jkl012... | Size: 5.3MB | Type: application/pdf
[=] /path/to/unchanged.doc | UUID: mno345... | Hash: pqr678... | Size: 2.1MB | Type: application/msword

Change Summary:
┌─────────────────┬───────┐
│ Change Type     │ Count │
├─────────────────┼───────┤
│ New Files       │ 1     │
│ Modified Files  │ 1     │
│ Unchanged Files │ 8     │
├─────────────────┼───────┤
│ Total Files     │ 10    │
└─────────────────┴───────┘
```

### Upload Operation
```
Starting synchronization for knowledge base: my-kb
Listing files from source...
Detecting changes...

Change Detection Summary:
┌─────────────────┬───────┐
│ Change Type     │ Count │
├─────────────────┼───────┤
│ New Files       │ 3     │
│ Modified Files  │ 2     │
│ Unchanged Files │ 15    │
│ Deleted Files   │ 0     │
├─────────────────┼───────┤
│ Total Files     │ 20    │
└─────────────────┴───────┘

Processing 5 files...
Processing: /path/to/file1.txt (new) [████████--] 80%

Synchronization Results:
┌──────────────────┬───────┐
│ Metric          │ Value │
├──────────────────┼───────┤
│ Duration        │ 12.3s │
│ Status          │ completed │
├──────────────────┼───────┤
│ Files Processed │ 5     │
│ Errors          │ 0     │
├──────────────────┼───────┤
│ New Files       │ 3     │
│ Modified Files  │ 2     │
│ Unchanged Files │ 15    │
│ Deleted Files   │ 0     │
└──────────────────┴───────┘
```

## Benefits

1. **Efficiency**: Only processes files that have actually changed
2. **Accuracy**: Uses hash comparison for true content change detection
3. **Visibility**: Clear visual feedback on what's changing
4. **Performance**: Reduces unnecessary uploads and processing time
5. **Auditability**: Maintains complete change history in the database

## Future Enhancements

- Handle deleted files by removing them from the RAG system
- Add support for custom change detection strategies
- Implement incremental hashing for very large files
- Add file versioning capabilities
- Support for rollback operations