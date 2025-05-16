-- Migration to add include_extensions to file_system source config schema
-- This updates the existing source_type entry for file_system

UPDATE source_type 
SET config_schema = '{"type": "object", "properties": {"root_path": {"type": "string"}, "include_patterns": {"type": "array", "items": {"type": "string"}}, "exclude_patterns": {"type": "array", "items": {"type": "string"}}, "include_extensions": {"type": "array", "items": {"type": "string"}}, "exclude_extensions": {"type": "array", "items": {"type": "string"}}}}'
WHERE name = 'file_system';

-- This migration only updates the schema definition
-- Existing knowledge bases will continue to work as include_extensions defaults to empty array