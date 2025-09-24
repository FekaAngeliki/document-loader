-- Migration: Add Multi-Source Support to PostgreSQL Schema
-- This migration extends the existing schema to support multi-source knowledge bases

-- =====================================================
-- PHASE 1: Add new tables for multi-source support
-- =====================================================

-- Multi-source knowledge base table
CREATE TABLE IF NOT EXISTS multi_source_knowledge_base (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    
    -- RAG system configuration (shared across all sources)
    rag_type VARCHAR(50) NOT NULL,
    rag_config JSONB NOT NULL,
    
    -- Global settings
    file_organization JSONB,
    sync_strategy JSONB,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Source definitions within a multi-source knowledge base
CREATE TABLE IF NOT EXISTS source_definition (
    id SERIAL PRIMARY KEY,
    multi_source_kb_id INTEGER REFERENCES multi_source_knowledge_base(id) ON DELETE CASCADE,
    
    -- Source identification
    source_id VARCHAR(100) NOT NULL,  -- Unique within the KB (e.g., "sharepoint_hr")
    source_type VARCHAR(50) NOT NULL, -- Type: enterprise_sharepoint, file_system, etc.
    source_config JSONB NOT NULL,     -- Source-specific configuration
    
    -- Source settings
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sync_schedule VARCHAR(100),        -- Cron expression
    metadata_tags JSONB,              -- Additional metadata tags
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Ensure source_id is unique within each multi-source KB
    UNIQUE(multi_source_kb_id, source_id)
);

-- Multi-source sync runs
CREATE TABLE IF NOT EXISTS multi_source_sync_run (
    id SERIAL PRIMARY KEY,
    multi_source_kb_id INTEGER REFERENCES multi_source_knowledge_base(id) ON DELETE CASCADE,
    
    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    
    -- Overall statistics
    total_files INTEGER,
    new_files INTEGER,
    modified_files INTEGER,
    deleted_files INTEGER,
    error_message TEXT,
    
    -- Multi-source specific
    sync_mode VARCHAR(20) NOT NULL DEFAULT 'parallel', -- parallel, sequential, selective
    sources_processed TEXT[], -- Array of source IDs that were processed
    source_stats JSONB,      -- Per-source statistics
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =====================================================
-- PHASE 2: Extend file_record table for source tracking
-- =====================================================

-- Add new columns to existing file_record table
ALTER TABLE file_record 
ADD COLUMN IF NOT EXISTS source_id VARCHAR(100),           -- Which source this file came from
ADD COLUMN IF NOT EXISTS source_type VARCHAR(50),          -- Type of source
ADD COLUMN IF NOT EXISTS source_path TEXT,                 -- Original path in source system
ADD COLUMN IF NOT EXISTS content_type VARCHAR(100),        -- MIME type
ADD COLUMN IF NOT EXISTS source_metadata JSONB,            -- Source-specific metadata
ADD COLUMN IF NOT EXISTS rag_metadata JSONB,               -- RAG system metadata
ADD COLUMN IF NOT EXISTS tags TEXT[],                      -- Searchable tags array
ADD COLUMN IF NOT EXISTS source_created_at TIMESTAMP,      -- File creation time in source
ADD COLUMN IF NOT EXISTS source_modified_at TIMESTAMP,     -- File modification time in source
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW(); -- Record update time

-- Update existing records to have default values for new columns
UPDATE file_record 
SET 
    source_id = 'legacy',
    source_type = 'unknown',
    source_path = original_uri,
    content_type = 'application/octet-stream',
    source_metadata = '{}',
    rag_metadata = '{}',
    tags = '{}',
    updated_at = NOW()
WHERE source_id IS NULL;

-- =====================================================
-- PHASE 3: Create indexes for performance
-- =====================================================

-- Multi-source knowledge base indexes
CREATE INDEX IF NOT EXISTS idx_multi_source_kb_name ON multi_source_knowledge_base(name);
CREATE INDEX IF NOT EXISTS idx_multi_source_kb_rag_type ON multi_source_knowledge_base(rag_type);

-- Source definition indexes
CREATE INDEX IF NOT EXISTS idx_source_def_multi_kb_id ON source_definition(multi_source_kb_id);
CREATE INDEX IF NOT EXISTS idx_source_def_source_id ON source_definition(source_id);
CREATE INDEX IF NOT EXISTS idx_source_def_source_type ON source_definition(source_type);
CREATE INDEX IF NOT EXISTS idx_source_def_enabled ON source_definition(enabled);

-- Multi-source sync run indexes
CREATE INDEX IF NOT EXISTS idx_multi_sync_run_kb_id ON multi_source_sync_run(multi_source_kb_id);
CREATE INDEX IF NOT EXISTS idx_multi_sync_run_status ON multi_source_sync_run(status);
CREATE INDEX IF NOT EXISTS idx_multi_sync_run_start_time ON multi_source_sync_run(start_time);

-- Enhanced file record indexes
CREATE INDEX IF NOT EXISTS idx_file_record_source_id ON file_record(source_id);
CREATE INDEX IF NOT EXISTS idx_file_record_source_type ON file_record(source_type);
CREATE INDEX IF NOT EXISTS idx_file_record_content_type ON file_record(content_type);
CREATE INDEX IF NOT EXISTS idx_file_record_tags ON file_record USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_file_record_source_metadata ON file_record USING GIN(source_metadata);
CREATE INDEX IF NOT EXISTS idx_file_record_source_modified ON file_record(source_modified_at);

-- =====================================================
-- PHASE 4: Add new source types
-- =====================================================

-- Insert enterprise SharePoint source type
INSERT INTO source_type (name, class_name, config_schema) 
VALUES (
    'enterprise_sharepoint', 
    'src.implementations.enterprise_sharepoint_source.EnterpriseSharePointSource',
    '{
        "type": "object",
        "properties": {
            "tenant_id": {"type": "string"},
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
            "site_url": {"type": "string"},
            "sites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "site_url": {"type": "string"},
                        "department": {"type": "string"},
                        "include_libraries": {"type": "boolean"},
                        "include_lists": {"type": "boolean"},
                        "include_site_pages": {"type": "boolean"}
                    }
                }
            },
            "include_extensions": {"type": "array", "items": {"type": "string"}},
            "recursive": {"type": "boolean"}
        },
        "required": ["tenant_id", "client_id", "client_secret"]
    }'
)
ON CONFLICT (name) DO UPDATE SET 
    class_name = EXCLUDED.class_name,
    config_schema = EXCLUDED.config_schema;

-- Insert OneDrive source type
INSERT INTO source_type (name, class_name, config_schema)
VALUES (
    'onedrive',
    'src.implementations.onedrive_source.OneDriveSource',
    '{
        "type": "object", 
        "properties": {
            "user_id": {"type": "string"},
            "root_folder": {"type": "string"},
            "recursive": {"type": "boolean"},
            "account_type": {"type": "string", "enum": ["business", "personal"]}
        },
        "required": ["user_id"]
    }'
)
ON CONFLICT (name) DO UPDATE SET
    class_name = EXCLUDED.class_name,
    config_schema = EXCLUDED.config_schema;

-- =====================================================
-- PHASE 5: Create views for backward compatibility
-- =====================================================

-- View that presents multi-source KBs as individual KBs for legacy compatibility
CREATE OR REPLACE VIEW legacy_knowledge_base_view AS
SELECT 
    -- Generate unique IDs by combining multi-source KB ID with source definition ID
    (ms_kb.id * 1000 + sd.id) as id,
    (ms_kb.name || '_' || sd.source_id) as name,
    sd.source_type,
    sd.source_config,
    ms_kb.rag_type,
    ms_kb.rag_config,
    ms_kb.created_at,
    ms_kb.updated_at,
    -- Additional fields for multi-source context
    ms_kb.id as multi_source_kb_id,
    sd.source_id,
    sd.enabled
FROM multi_source_knowledge_base ms_kb
JOIN source_definition sd ON ms_kb.id = sd.multi_source_kb_id
WHERE sd.enabled = true;

-- =====================================================
-- PHASE 6: Create functions for data management
-- =====================================================

-- Function to get all sources for a multi-source KB
CREATE OR REPLACE FUNCTION get_sources_for_multi_kb(kb_id INTEGER)
RETURNS TABLE(
    source_id VARCHAR(100),
    source_type VARCHAR(50),
    source_config JSONB,
    enabled BOOLEAN,
    sync_schedule VARCHAR(100),
    metadata_tags JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sd.source_id,
        sd.source_type,
        sd.source_config,
        sd.enabled,
        sd.sync_schedule,
        sd.metadata_tags
    FROM source_definition sd
    WHERE sd.multi_source_kb_id = kb_id
    ORDER BY sd.source_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get file statistics by source
CREATE OR REPLACE FUNCTION get_file_stats_by_source(kb_id INTEGER)
RETURNS TABLE(
    source_id VARCHAR(100),
    total_files BIGINT,
    total_size BIGINT,
    latest_upload TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fr.source_id,
        COUNT(*) as total_files,
        SUM(fr.file_size) as total_size,
        MAX(fr.upload_time) as latest_upload
    FROM file_record fr
    JOIN sync_run sr ON fr.sync_run_id = sr.id
    JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
    WHERE kb.id = kb_id
    GROUP BY fr.source_id
    ORDER BY fr.source_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- PHASE 7: Data validation and constraints
-- =====================================================

-- Add check constraints for data validation
ALTER TABLE multi_source_sync_run 
ADD CONSTRAINT IF NOT EXISTS chk_sync_mode 
CHECK (sync_mode IN ('parallel', 'sequential', 'selective', 'incremental'));

ALTER TABLE multi_source_sync_run
ADD CONSTRAINT IF NOT EXISTS chk_status
CHECK (status IN ('running', 'completed', 'failed', 'scan_running', 'scan_completed', 'scan_failed'));

-- Ensure source_id follows naming convention (alphanumeric + underscore)
ALTER TABLE source_definition
ADD CONSTRAINT IF NOT EXISTS chk_source_id_format
CHECK (source_id ~ '^[a-zA-Z0-9_]+$');

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

-- Log migration completion
INSERT INTO migration_log (migration_name, applied_at) 
VALUES ('001_multi_source_support', NOW())
ON CONFLICT DO NOTHING;

-- Create migration log table if it doesn't exist
CREATE TABLE IF NOT EXISTS migration_log (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
);