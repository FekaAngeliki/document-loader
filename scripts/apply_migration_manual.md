# Manual Database Migration Guide

Since the Python dependencies aren't available in this environment, here's how to apply the migration manually.

## Step 1: Apply the Migration to PostgreSQL

### Option A: Using psql command line
```bash
# Connect to your PostgreSQL database
psql -h localhost -p 5432 -U biks -d document_loader

# Apply the migration
\i migrations/001_multi_source_support.sql

# Verify tables were created
\dt multi_source*
\dt source_definition

# Check new columns in file_record
\d file_record

# Check views and functions
\dv legacy_knowledge_base_view
\df get_sources_for_multi_kb
\df get_file_stats_by_source

# Exit psql
\q
```

### Option B: Using pgAdmin or other GUI tool
1. Open pgAdmin and connect to your database
2. Open the SQL editor
3. Copy and paste the contents of `migrations/001_multi_source_support.sql`
4. Execute the SQL
5. Verify the tables were created in the Object Browser

### Option C: Using existing document-loader setup command
```bash
# If you have the document-loader CLI working with dependencies
source .venv/bin/activate  # Activate your virtual environment
python scripts/apply_migration.py
```

## Step 2: Verify Migration Success

Run this SQL to check if migration was successful:

```sql
-- Check new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'multi_source_knowledge_base',
    'source_definition', 
    'multi_source_sync_run'
);

-- Check new columns in file_record
SELECT column_name 
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'file_record'
AND column_name IN (
    'source_id', 'source_type', 'source_path', 'content_type',
    'source_metadata', 'rag_metadata', 'tags'
);

-- Check new source types
SELECT name FROM source_type 
WHERE name IN ('enterprise_sharepoint', 'onedrive');

-- Check legacy view
SELECT COUNT(*) FROM legacy_knowledge_base_view;
```

Expected results:
- 3 new tables created
- 7+ new columns in file_record  
- 2 new source types added
- Legacy view accessible

## Step 3: Test the Migration

Once applied, you can test with these SQL commands:

```sql
-- Test creating a multi-source KB
INSERT INTO multi_source_knowledge_base 
(name, description, rag_type, rag_config) 
VALUES (
    'test-kb', 
    'Test multi-source KB', 
    'azure_blob', 
    '{"azure_storage_container_name": "test"}'
);

-- Get the KB ID
SELECT id FROM multi_source_knowledge_base WHERE name = 'test-kb';

-- Add a source (replace 1 with actual KB ID)
INSERT INTO source_definition 
(multi_source_kb_id, source_id, source_type, source_config, metadata_tags)
VALUES (
    1,
    'test_source',
    'file_system',
    '{"root_path": "/test"}',
    '{"department": "IT"}'
);

-- Test the legacy view
SELECT * FROM legacy_knowledge_base_view WHERE multi_source_kb_id = 1;

-- Cleanup test data
DELETE FROM multi_source_knowledge_base WHERE name = 'test-kb';
```

## Step 4: Backup Considerations

Before applying the migration in production:

1. **Create a backup:**
   ```bash
   pg_dump -h localhost -U biks document_loader > backup_before_migration.sql
   ```

2. **Test on a copy first:**
   ```bash
   createdb document_loader_test
   psql -h localhost -U biks document_loader_test < backup_before_migration.sql
   psql -h localhost -U biks document_loader_test < migrations/001_multi_source_support.sql
   ```

3. **Verify the test database works correctly**

4. **Apply to production only after testing**

## Troubleshooting

### Common Issues:

1. **Permission denied errors:**
   ```sql
   GRANT CREATE ON SCHEMA public TO biks;
   ```

2. **Function creation errors:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS plpgsql;
   ```

3. **Index creation failures:**
   - Check if indexes already exist
   - Drop conflicting indexes if necessary

4. **Data type errors:**
   - Ensure PostgreSQL version supports JSONB (9.4+)
   - Check array support for TEXT[] columns

### Rollback if needed:
```sql
-- Drop new tables (this will also drop dependent data)
DROP TABLE IF EXISTS multi_source_sync_run CASCADE;
DROP TABLE IF EXISTS source_definition CASCADE;  
DROP TABLE IF EXISTS multi_source_knowledge_base CASCADE;

-- Remove new columns from file_record
ALTER TABLE file_record 
DROP COLUMN IF EXISTS source_id,
DROP COLUMN IF EXISTS source_type,
DROP COLUMN IF EXISTS source_path,
DROP COLUMN IF EXISTS content_type,
DROP COLUMN IF EXISTS source_metadata,
DROP COLUMN IF EXISTS rag_metadata,
DROP COLUMN IF EXISTS tags,
DROP COLUMN IF EXISTS source_created_at,
DROP COLUMN IF EXISTS source_modified_at,
DROP COLUMN IF EXISTS updated_at;

-- Drop views and functions
DROP VIEW IF EXISTS legacy_knowledge_base_view;
DROP FUNCTION IF EXISTS get_sources_for_multi_kb(INTEGER);
DROP FUNCTION IF EXISTS get_file_stats_by_source(INTEGER);
```

Once the migration is applied successfully, we can proceed with the next steps!