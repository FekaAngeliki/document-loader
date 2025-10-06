# SharePoint Folder Hierarchy Preservation

## Overview

The document-loader now supports preserving the original SharePoint folder hierarchy when syncing files to the destination RAG system. This allows you to maintain the organizational structure from SharePoint in your processed files.

## Configuration

### Basic Usage

Set `folder_structure` to `"preserve_hierarchy"` in your configuration:

```json
{
  "file_organization": {
    "naming_convention": "{source_id}/{uuid}{extension}",
    "folder_structure": "preserve_hierarchy"
  }
}
```

### Available Options

#### Folder Structure Types

- **`"source_based"`** (default): Flat structure
  - Result: `Sharepoint_1/550e8400-e29b-41d4-a716-446655440000.pdf`

- **`"preserve_hierarchy"`**: Maintains original folder structure
  - Result: `Sharepoint_1/HR/Policies/550e8400-e29b-41d4-a716-446655440000.pdf`

#### Naming Convention Patterns

- **Basic**: `"{source_id}/{uuid}{extension}"`
  - With hierarchy: `Sharepoint_1/HR/Policies/uuid.pdf`

- **With explicit folder path**: `"{source_id}/{folder_path}/{uuid}{extension}"`
  - Result: `Sharepoint_1/HR/Policies/uuid.pdf`

- **With original filename**: `"{source_id}/{folder_path}/{original_name}_{uuid}{extension}"`
  - Result: `Sharepoint_1/HR/Policies/Employee_Handbook_uuid.pdf`

## Examples

### Example 1: Basic Hierarchy Preservation

```json
{
  "name": "my-kb",
  "file_organization": {
    "naming_convention": "{source_id}/{uuid}{extension}",
    "folder_structure": "preserve_hierarchy"
  }
}
```

**SharePoint File**: `https://company.sharepoint.com/sites/hr/Documents/Policies/HR/Employee_Manual.pdf`
**Result**: `Sharepoint_1/Policies/HR/550e8400-e29b-41d4-a716-446655440000.pdf`

### Example 2: Hierarchy with Original Names

```json
{
  "name": "my-kb",
  "file_organization": {
    "naming_convention": "{source_id}/{folder_path}/{original_name}_{uuid}{extension}",
    "folder_structure": "preserve_hierarchy"
  }
}
```

**SharePoint File**: `https://company.sharepoint.com/sites/hr/Documents/Policies/HR/Employee_Manual.pdf`
**Result**: `Sharepoint_1/Policies/HR/Employee_Manual_550e8400-e29b-41d4-a716-446655440000.pdf`

## SharePoint URL Patterns Supported

The system automatically detects and processes these SharePoint URL patterns:

- Root level files: `/sites/sitename/LibraryName/file.pdf` → (no folder)
- Single folder: `/sites/sitename/LibraryName/Folder/file.pdf` → `Folder/`
- Nested folders: `/sites/sitename/LibraryName/Folder1/Folder2/file.pdf` → `Folder1/Folder2/`
- URL encoded paths: `/sites/sitename/Shared%20Documents/My%20Folder/file.pdf` → `My Folder/`

## Testing

Run the test script to verify functionality:

```bash
python3 test_scripts/test_folder_hierarchy_simple.py
```

## Migration

To migrate existing configurations:

1. **Backup existing data**: Ensure your current files are safely stored
2. **Update configuration**: Change `"folder_structure"` from `"source_based"` to `"preserve_hierarchy"`
3. **Test with new sync**: Run a test sync to verify the new structure
4. **Full resync if needed**: For complete migration, you may want to clear and resync all files

## Compatibility

- **Forward compatible**: New configurations work with existing systems
- **Backward compatible**: Old configurations continue to work unchanged
- **Mixed mode**: You can use different structures for different knowledge bases

## Use Cases

- **Document Management**: Maintain departmental folder structures
- **Compliance**: Preserve original filing systems for audit trails
- **User Experience**: Keep familiar folder navigation in processed documents
- **Content Organization**: Maintain logical groupings from source systems