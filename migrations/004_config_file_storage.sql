-- Migration: Config File Storage System
-- Stores multi-source configuration files as assets in PostgreSQL

CREATE TABLE IF NOT EXISTS config_assets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    config_type VARCHAR(100) NOT NULL DEFAULT 'multi_source',
    config_data JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    tags VARCHAR(255)[] DEFAULT '{}',
    
    -- Metadata
    file_size INTEGER,
    file_hash VARCHAR(64),
    original_filename VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',
    
    -- Validation
    is_valid BOOLEAN NOT NULL DEFAULT true,
    validation_errors JSONB,
    last_validated_at TIMESTAMP WITH TIME ZONE,
    
    -- Usage tracking
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0
);

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_config_assets_name ON config_assets(name);
CREATE INDEX IF NOT EXISTS idx_config_assets_type ON config_assets(config_type);
CREATE INDEX IF NOT EXISTS idx_config_assets_active ON config_assets(is_active);
CREATE INDEX IF NOT EXISTS idx_config_assets_tags ON config_assets USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_config_assets_created ON config_assets(created_at);

-- Create a view for active configs only
CREATE OR REPLACE VIEW active_config_assets AS
SELECT 
    id,
    name,
    description,
    config_type,
    config_data,
    version,
    tags,
    file_size,
    original_filename,
    created_at,
    updated_at,
    last_used_at,
    usage_count
FROM config_assets 
WHERE is_active = true AND is_valid = true;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_config_asset_timestamp()
RETURNS TRIGGER AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_config_asset_timestamp ON config_assets;
CREATE TRIGGER trigger_update_config_asset_timestamp
    BEFORE UPDATE ON config_assets
    FOR EACH ROW
    EXECUTE FUNCTION update_config_asset_timestamp();

-- Function to track config usage
CREATE OR REPLACE FUNCTION track_config_usage(config_name VARCHAR(255))
RETURNS VOID AS $function$
BEGIN
    UPDATE config_assets 
    SET 
        last_used_at = NOW(),
        usage_count = COALESCE(usage_count, 0) + 1
    WHERE name = config_name AND is_active = true;
END;
$function$ LANGUAGE plpgsql;