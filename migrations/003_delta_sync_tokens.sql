-- Migration: Add delta sync token storage
-- This enables Graph API delta queries for fast incremental sync

CREATE TABLE IF NOT EXISTS delta_sync_tokens (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(255) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    drive_id VARCHAR(255) NOT NULL,
    delta_token TEXT NOT NULL,
    last_sync_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Ensure one token per source/drive combination
    UNIQUE(source_id, drive_id)
);

-- Add index for fast lookups
CREATE INDEX IF NOT EXISTS idx_delta_tokens_source 
ON delta_sync_tokens(source_id, source_type);

-- Add index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_delta_tokens_last_sync 
ON delta_sync_tokens(last_sync_time);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_delta_token_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_delta_token_timestamp ON delta_sync_tokens;
CREATE TRIGGER trigger_update_delta_token_timestamp
    BEFORE UPDATE ON delta_sync_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_delta_token_timestamp();