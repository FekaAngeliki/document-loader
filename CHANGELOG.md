# Changelog

All notable changes to Document Loader will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **include_extensions** support for file_system source configuration
  - Allows specifying which file extensions to include (whitelist approach)
  - More performant than pattern-based filtering for extension-specific filtering
  - Works in conjunction with exclude_extensions for precise control
  - Example: `"include_extensions": [".pdf", ".docx", ".xlsx"]`
- Enhanced documentation for extension filtering in SOURCE_CONFIG_GUIDE.md
- Migration script to update existing databases with new schema
- **Enhanced scan command** with additional output and database update capability
  - Now displays original filename, UUID filename, and hash for each file
  - Added `--update-db` flag to update database as if performing a real sync
  - Added `--kb-name` parameter for use with `--update-db`
  - Table view now includes UUID column
  - Can use knowledge base configuration when --kb-name is provided without --path
- **Scan runs are now tracked separately in the database**
  - Added new sync run statuses: scan_running, scan_completed, scan_failed
  - Added new file statuses: scanned, scan_error
  - Scan runs are recorded with distinctive statuses to differentiate from actual sync runs
  - File records from scans are marked as 'scanned' instead of 'uploaded'

### Changed
- Updated FileSystemSource to support include_extensions filtering
- Updated source_type schema for file_system to include include_extensions
- Improved filtering logic with clear priority order:
  1. exclude_extensions (files with these extensions are excluded first)
  2. include_extensions (if specified, only these extensions are included)
  3. exclude_patterns (pattern-based exclusion)
  4. include_patterns (pattern-based inclusion)
- Modified scanner output to display more detailed file information
- Repository methods updated to support scanner's database update functionality

### Fixed
- None

### Deprecated
- None

### Removed
- None

### Security
- None