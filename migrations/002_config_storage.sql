-- Migration: Add configuration file storage support
-- This allows admins to upload and manage KB config files in the database

-- Table to store configuration files
CREATE TABLE IF NOT EXISTS kb_config_files (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    config_content JSONB NOT NULL,
    file_path VARCHAR(500),                    -- Original file path for reference
    file_hash VARCHAR(64) NOT NULL,            -- SHA-256 hash for integrity
    version INTEGER NOT NULL DEFAULT 1,       -- Version number for updates
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, archived, draft
    created_by VARCHAR(100),                   -- Admin user who uploaded
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_deployed_at TIMESTAMP,               -- When config was last used for KB creation
    deployment_count INTEGER DEFAULT 0        -- How many times this config was used
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_kb_config_name ON kb_config_files(name);
CREATE INDEX IF NOT EXISTS idx_kb_config_status ON kb_config_files(status);
CREATE INDEX IF NOT EXISTS idx_kb_config_created_by ON kb_config_files(created_by);

-- Link multi-source KBs to their original config files
ALTER TABLE multi_source_knowledge_base 
ADD COLUMN IF NOT EXISTS config_file_id INTEGER REFERENCES kb_config_files(id),
ADD COLUMN IF NOT EXISTS config_version INTEGER DEFAULT 1;

-- Function to validate config file structure
CREATE OR REPLACE FUNCTION validate_kb_config(config_content JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check required fields exist
    IF NOT (config_content ? 'name' AND 
            config_content ? 'rag_type' AND 
            config_content ? 'sources') THEN
        RETURN FALSE;
    END IF;
    
    -- Check sources is an array
    IF jsonb_typeof(config_content->'sources') != 'array' THEN
        RETURN FALSE;
    END IF;
    
    -- Check each source has required fields
    IF EXISTS (
        SELECT 1 FROM jsonb_array_elements(config_content->'sources') AS source
        WHERE NOT (source ? 'source_id' AND 
                  source ? 'source_type' AND 
                  source ? 'source_config')
    ) THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update timestamp on config changes
CREATE OR REPLACE FUNCTION update_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_config_timestamp
    BEFORE UPDATE ON kb_config_files
    FOR EACH ROW
    EXECUTE FUNCTION update_config_timestamp();

-- Function to get config by name with version history
CREATE OR REPLACE FUNCTION get_config_versions(config_name VARCHAR)
RETURNS TABLE(
    id INTEGER,
    version INTEGER,
    status VARCHAR,
    created_at TIMESTAMP,
    created_by VARCHAR,
    deployment_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kc.id,
        kc.version,
        kc.status,
        kc.created_at,
        kc.created_by,
        kc.deployment_count
    FROM kb_config_files kc
    WHERE kc.name = config_name
    ORDER BY kc.version DESC;
END;
$$ LANGUAGE plpgsql;

-- View for admin config management
CREATE OR REPLACE VIEW admin_config_summary AS
SELECT 
    name,
    description,
    status,
    version,
    created_by,
    created_at,
    last_deployed_at,
    deployment_count,
    CASE 
        WHEN last_deployed_at IS NULL THEN 'Never deployed'
        WHEN last_deployed_at < (NOW() - INTERVAL '30 days') THEN 'Deployed over 30 days ago'
        WHEN last_deployed_at < (NOW() - INTERVAL '7 days') THEN 'Deployed over 7 days ago'
        ELSE 'Recently deployed'
    END as deployment_status,
    jsonb_array_length(config_content->'sources') as source_count,
    config_content->>'rag_type' as rag_type
FROM kb_config_files
WHERE status = 'active'
ORDER BY updated_at DESC;

-- Insert audit log entry
INSERT INTO migration_log (migration_name, applied_at) 
VALUES ('002_config_storage', NOW())
ON CONFLICT (migration_name) DO UPDATE SET applied_at = NOW();