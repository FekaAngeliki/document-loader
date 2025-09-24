-- Query to verify delta sync worked correctly
-- Run this after the next sync to confirm only 3 files were processed

-- 1. Check the latest sync run
SELECT 
    sr.id,
    sr.start_time,
    sr.end_time,
    sr.status,
    sr.total_files,
    sr.new_files,
    sr.modified_files,
    EXTRACT(EPOCH FROM (sr.end_time - sr.start_time))/60 as duration_minutes
FROM sync_run sr
ORDER BY sr.start_time DESC
LIMIT 1;

-- 2. Count files processed in the latest run (should be only 3)
SELECT 
    COUNT(*) as files_in_latest_run,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_files,
    COUNT(CASE WHEN status != 'error' THEN 1 END) as success_files
FROM file_record fr
WHERE fr.sync_run_id = (SELECT MAX(id) FROM sync_run);

-- 3. Check the 3 specific files got fixed
SELECT 
    fr.original_uri,
    fr.status,
    fr.file_size,
    fr.rag_uri,
    CASE WHEN fr.rag_uri LIKE '%error-%' THEN 'Error URI' ELSE 'Normal URI' END as uri_type
FROM file_record fr
WHERE fr.sync_run_id = (SELECT MAX(id) FROM sync_run)
  AND fr.original_uri LIKE '%Easter%20Premium%20Card%'
   OR fr.original_uri LIKE '%Auto_Protect_e-leaflet%'
ORDER BY fr.original_uri;

-- 4. Verify performance optimization worked (no hash calculations for unchanged files)
-- This should show the sync completed much faster
SELECT 
    'Delta sync performance' as metric,
    CASE 
        WHEN EXTRACT(EPOCH FROM (end_time - start_time)) < 300 THEN 'EXCELLENT (<5 min)'
        WHEN EXTRACT(EPOCH FROM (end_time - start_time)) < 600 THEN 'GOOD (<10 min)' 
        ELSE 'SLOW (>10 min)'
    END as performance_rating,
    ROUND(EXTRACT(EPOCH FROM (end_time - start_time))/60, 1) as duration_minutes
FROM sync_run 
WHERE id = (SELECT MAX(id) FROM sync_run);