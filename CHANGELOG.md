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

### Changed
- Updated FileSystemSource to support include_extensions filtering
- Updated source_type schema for file_system to include include_extensions
- Improved filtering logic with clear priority order:
  1. exclude_extensions (files with these extensions are excluded first)
  2. include_extensions (if specified, only these extensions are included)
  3. exclude_patterns (pattern-based exclusion)
  4. include_patterns (pattern-based inclusion)

### Fixed
- None

### Deprecated
- None

### Removed
- None

### Security
- None