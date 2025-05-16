def create_schema_sql():
    """Return SQL for creating the database schema."""
    return """
    CREATE TABLE IF NOT EXISTS knowledge_base (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        source_type VARCHAR(50) NOT NULL,
        source_config JSONB NOT NULL,
        rag_type VARCHAR(50) NOT NULL,
        rag_config JSONB NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS sync_run (
        id SERIAL PRIMARY KEY,
        knowledge_base_id INTEGER REFERENCES knowledge_base(id) ON DELETE CASCADE,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        status VARCHAR(20) NOT NULL,
        total_files INTEGER,
        new_files INTEGER,
        modified_files INTEGER,
        deleted_files INTEGER,
        error_message TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS file_record (
        id SERIAL PRIMARY KEY,
        sync_run_id INTEGER REFERENCES sync_run(id) ON DELETE CASCADE,
        original_uri TEXT NOT NULL,
        rag_uri TEXT NOT NULL,
        file_hash VARCHAR(64) NOT NULL,
        uuid_filename VARCHAR(40) NOT NULL,
        upload_time TIMESTAMP NOT NULL,
        file_size BIGINT NOT NULL,
        status VARCHAR(20) NOT NULL,
        error_message TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS source_type (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL UNIQUE,
        class_name VARCHAR(100) NOT NULL,
        config_schema JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rag_type (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL UNIQUE,
        class_name VARCHAR(100) NOT NULL,
        config_schema JSONB NOT NULL
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_file_record_original_uri ON file_record(original_uri);
    CREATE INDEX IF NOT EXISTS idx_file_record_file_hash ON file_record(file_hash);
    CREATE INDEX IF NOT EXISTS idx_file_record_sync_run_id ON file_record(sync_run_id);
    CREATE INDEX IF NOT EXISTS idx_sync_run_knowledge_base_id ON sync_run(knowledge_base_id);

    -- Insert default source types
    INSERT INTO source_type (name, class_name, config_schema) 
    VALUES ('file_system', 'src.implementations.file_system_source.FileSystemSource', 
           '{"type": "object", "properties": {"root_path": {"type": "string"}, "include_patterns": {"type": "array", "items": {"type": "string"}}, "exclude_patterns": {"type": "array", "items": {"type": "string"}}, "include_extensions": {"type": "array", "items": {"type": "string"}}, "exclude_extensions": {"type": "array", "items": {"type": "string"}}}}')
    ON CONFLICT (name) DO NOTHING;
    
    INSERT INTO source_type (name, class_name, config_schema)
    VALUES ('sharepoint', 'src.implementations.sharepoint_source.SharePointSource',
           '{"type": "object", "properties": {"site_url": {"type": "string"}, "path": {"type": "string"}, "username": {"type": "string"}, "password": {"type": "string"}, "recursive": {"type": "boolean"}}}')
    ON CONFLICT (name) DO NOTHING;

    -- Insert default RAG types
    INSERT INTO rag_type (name, class_name, config_schema) 
    VALUES ('mock', 'src.implementations.mock_rag_system.MockRAGSystem', 
           '{"type": "object", "properties": {}}')
    ON CONFLICT (name) DO NOTHING;
    """