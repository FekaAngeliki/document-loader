"""
Multi-Source Repository Layer

Provides database operations for multi-source knowledge bases,
extending the existing repository with multi-source capabilities.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .database import Database, JSONEncoder
from .models import KnowledgeBase
from .repository import Repository
from .multi_source_models import (
    MultiSourceKnowledgeBase,
    SourceDefinition,
    MultiSourceSyncRun,
    EnhancedFileRecord,
    SourceSyncStatus
)

logger = logging.getLogger(__name__)

class MultiSourceRepository:
    """Repository for multi-source knowledge base operations."""
    
    def __init__(self, database: Database):
        self.db = database
        # Create a regular repository instance for delegating common operations
        self._repository = Repository(database)
    
    # =====================================================
    # Multi-Source Knowledge Base Operations
    # =====================================================
    
    async def create_multi_source_kb(self, multi_kb: MultiSourceKnowledgeBase) -> int:
        """Create a new multi-source knowledge base."""
        
        # Start transaction
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # Create the multi-source KB
                kb_query = """
                    INSERT INTO multi_source_knowledge_base 
                    (name, description, rag_type, rag_config, file_organization, sync_strategy)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """
                
                kb_id = await conn.fetchval(
                    kb_query,
                    multi_kb.name,
                    multi_kb.description,
                    multi_kb.rag_type,
                    json.dumps(multi_kb.rag_config, cls=JSONEncoder),
                    json.dumps(multi_kb.file_organization, cls=JSONEncoder),
                    json.dumps(multi_kb.sync_strategy, cls=JSONEncoder)
                )
                
                # Create source definitions
                source_query = """
                    INSERT INTO source_definition
                    (multi_source_kb_id, source_id, source_type, source_config, 
                     enabled, sync_schedule, metadata_tags)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """
                
                for source in multi_kb.sources:
                    await conn.execute(
                        source_query,
                        kb_id,
                        source.source_id,
                        source.source_type,
                        json.dumps(source.source_config, cls=JSONEncoder),
                        source.enabled,
                        source.sync_schedule,
                        json.dumps(source.metadata_tags, cls=JSONEncoder)
                    )
                
                return kb_id
    
    async def get_multi_source_kb(self, kb_id: int) -> Optional[MultiSourceKnowledgeBase]:
        """Get a multi-source knowledge base by ID."""
        
        # Get the main KB record
        kb_query = """
            SELECT id, name, description, rag_type, rag_config, 
                   file_organization, sync_strategy, created_at, updated_at
            FROM multi_source_knowledge_base
            WHERE id = $1
        """
        
        kb_row = await self.db.fetchrow(kb_query, kb_id)
        if not kb_row:
            return None
        
        # Get source definitions
        sources_query = """
            SELECT source_id, source_type, source_config, enabled, 
                   sync_schedule, metadata_tags, created_at, updated_at
            FROM source_definition
            WHERE multi_source_kb_id = $1
            ORDER BY source_id
        """
        
        source_rows = await self.db.fetch(sources_query, kb_id)
        
        # Build source definitions
        sources = []
        for row in source_rows:
            source = SourceDefinition(
                source_id=row['source_id'],
                source_type=row['source_type'],
                source_config=json.loads(row['source_config']),
                enabled=row['enabled'],
                sync_schedule=row['sync_schedule'],
                metadata_tags=json.loads(row['metadata_tags']) if row['metadata_tags'] else {},
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            sources.append(source)
        
        # Build multi-source KB
        multi_kb = MultiSourceKnowledgeBase(
            id=kb_row['id'],
            name=kb_row['name'],
            description=kb_row['description'],
            rag_type=kb_row['rag_type'],
            rag_config=json.loads(kb_row['rag_config']),
            sources=sources,
            file_organization=json.loads(kb_row['file_organization']) if kb_row['file_organization'] else {},
            sync_strategy=json.loads(kb_row['sync_strategy']) if kb_row['sync_strategy'] else {},
            created_at=kb_row['created_at'],
            updated_at=kb_row['updated_at']
        )
        
        return multi_kb
    
    async def get_multi_source_kb_by_name(self, name: str) -> Optional[MultiSourceKnowledgeBase]:
        """Get a multi-source knowledge base by name."""
        
        kb_query = "SELECT id FROM multi_source_knowledge_base WHERE name = $1"
        kb_id = await self.db.fetchval(kb_query, name)
        
        if kb_id:
            return await self.get_multi_source_kb(kb_id)
        return None
    
    async def list_multi_source_kbs(self) -> List[MultiSourceKnowledgeBase]:
        """List all multi-source knowledge bases."""
        
        query = """
            SELECT id, name, description, rag_type, rag_config,
                   file_organization, sync_strategy, created_at, updated_at
            FROM multi_source_knowledge_base
            ORDER BY name
        """
        
        rows = await self.db.fetch(query)
        kbs = []
        
        for row in rows:
            # Get sources for each KB
            kb = await self.get_multi_source_kb(row['id'])
            if kb:
                kbs.append(kb)
        
        return kbs
    
    async def update_multi_source_kb(self, kb_id: int, updates: Dict[str, Any]) -> bool:
        """Update a multi-source knowledge base."""
        
        # Build update query dynamically based on provided fields
        update_fields = []
        values = []
        param_count = 1
        
        for field, value in updates.items():
            if field in ['name', 'description', 'rag_type']:
                update_fields.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
            elif field in ['rag_config', 'file_organization', 'sync_strategy']:
                update_fields.append(f"{field} = ${param_count}")
                values.append(json.dumps(value, cls=JSONEncoder))
                param_count += 1
        
        if not update_fields:
            return False
        
        update_fields.append(f"updated_at = ${param_count}")
        values.append(datetime.utcnow())
        values.append(kb_id)  # For WHERE clause
        
        query = f"""
            UPDATE multi_source_knowledge_base 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count + 1}
        """
        
        result = await self.db.execute(query, *values)
        return result == "UPDATE 1"
    
    async def delete_multi_source_kb(self, kb_id: int) -> bool:
        """Delete a multi-source knowledge base and all related data."""
        
        query = "DELETE FROM multi_source_knowledge_base WHERE id = $1"
        result = await self.db.execute(query, kb_id)
        return result == "DELETE 1"
    
    # =====================================================
    # Source Definition Operations
    # =====================================================
    
    async def add_source_to_kb(self, kb_id: int, source: SourceDefinition) -> bool:
        """Add a new source to an existing multi-source knowledge base."""
        
        query = """
            INSERT INTO source_definition
            (multi_source_kb_id, source_id, source_type, source_config,
             enabled, sync_schedule, metadata_tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        try:
            await self.db.execute(
                query,
                kb_id,
                source.source_id,
                source.source_type,
                json.dumps(source.source_config, cls=JSONEncoder),
                source.enabled,
                source.sync_schedule,
                json.dumps(source.metadata_tags, cls=JSONEncoder)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add source to KB: {e}")
            return False
    
    async def update_source_definition(self, kb_id: int, source_id: str, updates: Dict[str, Any]) -> bool:
        """Update a source definition."""
        
        update_fields = []
        values = []
        param_count = 1
        
        for field, value in updates.items():
            if field in ['source_type', 'enabled', 'sync_schedule']:
                update_fields.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
            elif field in ['source_config', 'metadata_tags']:
                update_fields.append(f"{field} = ${param_count}")
                values.append(json.dumps(value, cls=JSONEncoder))
                param_count += 1
        
        if not update_fields:
            return False
        
        update_fields.append(f"updated_at = ${param_count}")
        values.append(datetime.utcnow())
        values.extend([kb_id, source_id])  # For WHERE clause
        
        query = f"""
            UPDATE source_definition 
            SET {', '.join(update_fields)}
            WHERE multi_source_kb_id = ${param_count + 1} AND source_id = ${param_count + 2}
        """
        
        result = await self.db.execute(query, *values)
        return result == "UPDATE 1"
    
    async def remove_source_from_kb(self, kb_id: int, source_id: str) -> bool:
        """Remove a source from a multi-source knowledge base."""
        
        query = """
            DELETE FROM source_definition 
            WHERE multi_source_kb_id = $1 AND source_id = $2
        """
        
        result = await self.db.execute(query, kb_id, source_id)
        return result == "DELETE 1"
    
    # =====================================================
    # Multi-Source Sync Run Operations
    # =====================================================
    
    async def create_multi_source_sync_run(self, sync_run: MultiSourceSyncRun) -> int:
        """Create a new multi-source sync run."""
        
        query = """
            INSERT INTO multi_source_sync_run
            (multi_source_kb_id, start_time, status, sync_mode, sources_processed)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        
        return await self.db.fetchval(
            query,
            sync_run.knowledge_base_id,
            sync_run.start_time,
            sync_run.status,
            sync_run.sync_mode,
            sync_run.sources_processed
        )
    
    async def update_multi_source_sync_run(self, sync_run: MultiSourceSyncRun) -> bool:
        """Update a multi-source sync run."""
        
        query = """
            UPDATE multi_source_sync_run
            SET end_time = $1, status = $2, total_files = $3, new_files = $4,
                modified_files = $5, deleted_files = $6, error_message = $7,
                source_stats = $8
            WHERE id = $9
        """
        
        result = await self.db.execute(
            query,
            sync_run.end_time,
            sync_run.status,
            sync_run.total_files,
            sync_run.new_files,
            sync_run.modified_files,
            sync_run.deleted_files,
            sync_run.error_message,
            json.dumps(sync_run.source_stats, cls=JSONEncoder),
            sync_run.id
        )
        
        return result == "UPDATE 1"
    
    async def get_multi_source_sync_runs(self, kb_id: int, limit: int = 10) -> List[MultiSourceSyncRun]:
        """Get sync runs for a multi-source knowledge base."""
        
        query = """
            SELECT id, multi_source_kb_id, start_time, end_time, status,
                   total_files, new_files, modified_files, deleted_files,
                   error_message, sync_mode, sources_processed, source_stats,
                   created_at
            FROM multi_source_sync_run
            WHERE multi_source_kb_id = $1
            ORDER BY start_time DESC
            LIMIT $2
        """
        
        rows = await self.db.fetch(query, kb_id, limit)
        
        sync_runs = []
        for row in rows:
            sync_run = MultiSourceSyncRun(
                id=row['id'],
                knowledge_base_id=row['multi_source_kb_id'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                status=row['status'],
                total_files=row['total_files'],
                new_files=row['new_files'],
                modified_files=row['modified_files'],
                deleted_files=row['deleted_files'],
                error_message=row['error_message'],
                sync_mode=row['sync_mode'],
                sources_processed=row['sources_processed'] or [],
                source_stats=json.loads(row['source_stats']) if row['source_stats'] else {},
                created_at=row['created_at']
            )
            sync_runs.append(sync_run)
        
        return sync_runs
    
    # =====================================================
    # Enhanced File Record Operations
    # =====================================================
    
    async def create_enhanced_file_record(self, file_record: EnhancedFileRecord) -> int:
        """Create an enhanced file record with source tracking."""
        
        query = """
            INSERT INTO file_record
            (sync_run_id, source_id, source_type, source_path, original_uri,
             rag_uri, file_hash, uuid_filename, upload_time, file_size,
             content_type, status, error_message, source_metadata, rag_metadata,
             tags, source_created_at, source_modified_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            RETURNING id
        """
        
        return await self.db.fetchval(
            query,
            file_record.sync_run_id,
            file_record.source_id,
            file_record.source_type,
            file_record.source_path,
            file_record.original_uri,
            file_record.rag_uri,
            file_record.file_hash,
            file_record.uuid_filename,
            file_record.upload_time,
            file_record.file_size,
            file_record.content_type,
            file_record.status,
            file_record.error_message,
            json.dumps(file_record.source_metadata, cls=JSONEncoder),
            json.dumps(file_record.rag_metadata, cls=JSONEncoder),
            file_record.tags,
            file_record.source_created_at,
            file_record.source_modified_at
        )
    
    async def get_files_by_source(self, kb_id: int, source_id: str, limit: int = 100) -> List[EnhancedFileRecord]:
        """Get files from a specific source in a multi-source KB."""
        
        query = """
            SELECT fr.id, fr.sync_run_id, fr.source_id, fr.source_type, fr.source_path,
                   fr.original_uri, fr.rag_uri, fr.file_hash, fr.uuid_filename,
                   fr.upload_time, fr.file_size, fr.content_type, fr.status,
                   fr.error_message, fr.source_metadata, fr.rag_metadata, fr.tags,
                   fr.source_created_at, fr.source_modified_at, fr.created_at, fr.updated_at
            FROM file_record fr
            JOIN multi_source_sync_run mssr ON fr.sync_run_id = mssr.id
            WHERE mssr.multi_source_kb_id = $1 AND fr.source_id = $2
            ORDER BY fr.upload_time DESC
            LIMIT $3
        """
        
        rows = await self.db.fetch(query, kb_id, source_id, limit)
        
        files = []
        for row in rows:
            file_record = EnhancedFileRecord(
                id=row['id'],
                sync_run_id=row['sync_run_id'],
                source_id=row['source_id'],
                source_type=row['source_type'],
                source_path=row['source_path'],
                original_uri=row['original_uri'],
                rag_uri=row['rag_uri'],
                file_hash=row['file_hash'],
                uuid_filename=row['uuid_filename'],
                upload_time=row['upload_time'],
                file_size=row['file_size'],
                content_type=row['content_type'],
                status=row['status'],
                error_message=row['error_message'],
                source_metadata=json.loads(row['source_metadata']) if row['source_metadata'] else {},
                rag_metadata=json.loads(row['rag_metadata']) if row['rag_metadata'] else {},
                tags=row['tags'] or [],
                source_created_at=row['source_created_at'],
                source_modified_at=row['source_modified_at'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            files.append(file_record)
        
        return files
    
    # =====================================================
    # Statistics and Reporting
    # =====================================================
    
    async def get_multi_source_stats(self, kb_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a multi-source knowledge base."""
        
        # Get file stats by source using the database function
        stats_query = "SELECT * FROM get_file_stats_by_source($1)"
        source_stats = await self.db.fetch(stats_query, kb_id)
        
        # Get recent sync run information
        sync_query = """
            SELECT status, start_time, end_time, total_files, source_stats
            FROM multi_source_sync_run
            WHERE multi_source_kb_id = $1
            ORDER BY start_time DESC
            LIMIT 1
        """
        
        latest_sync = await self.db.fetchrow(sync_query, kb_id)
        
        # Compile statistics
        stats = {
            "kb_id": kb_id,
            "sources": {},
            "totals": {
                "total_files": 0,
                "total_size": 0
            },
            "latest_sync": None
        }
        
        # Process source statistics
        for row in source_stats:
            source_id = row['source_id']
            stats["sources"][source_id] = {
                "total_files": row['total_files'],
                "total_size": row['total_size'],
                "latest_upload": row['latest_upload']
            }
            stats["totals"]["total_files"] += row['total_files']
            stats["totals"]["total_size"] += row['total_size']
        
        # Add latest sync information
        if latest_sync:
            stats["latest_sync"] = {
                "status": latest_sync['status'],
                "start_time": latest_sync['start_time'],
                "end_time": latest_sync['end_time'],
                "total_files": latest_sync['total_files'],
                "source_stats": json.loads(latest_sync['source_stats']) if latest_sync['source_stats'] else {}
            }
        
        return stats
    
    # =====================================================
    # Backward Compatibility
    # =====================================================
    
    async def get_legacy_kb_for_source(self, multi_kb_id: int, source_id: str) -> Optional[KnowledgeBase]:
        """Get a legacy KB representation for a specific source in a multi-source KB."""
        
        query = """
            SELECT * FROM legacy_knowledge_base_view
            WHERE multi_source_kb_id = $1 AND source_id = $2
        """
        
        row = await self.db.fetchrow(query, multi_kb_id, source_id)
        if not row:
            return None
        
        return KnowledgeBase(
            id=row['id'],
            name=row['name'],
            source_type=row['source_type'],
            source_config=json.loads(row['source_config']),
            rag_type=row['rag_type'],
            rag_config=json.loads(row['rag_config']),
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    # =====================================================
    # Delegated Methods for Batch Runner Compatibility
    # =====================================================
    
    async def create_sync_run(self, knowledge_base_id: int) -> int:
        """Create a sync run - delegated to regular repository."""
        return await self._repository.create_sync_run(knowledge_base_id)
    
    async def update_sync_run(self, sync_run) -> None:
        """Update a sync run - delegated to regular repository."""
        return await self._repository.update_sync_run(sync_run)
    
    async def create_file_record_original(self, file_record) -> None:
        """Create a file record with JSON conversion for metadata and timezone fixes - delegated to regular repository."""
        import json
        from datetime import datetime
        
        def convert_to_utc_naive(dt):
            """Convert timezone-aware datetime to UTC timezone-naive datetime."""
            if dt is None:
                return None
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                # Convert timezone-aware datetime to UTC and remove timezone info
                utc_dt = dt.utctimetuple()
                return datetime(*utc_dt[:6])  # Convert time.struct_time back to datetime
            return dt
        
        # Always create a copy to handle JSON conversion and timezone fixes
        from ..data.models import FileRecord
        
        # Convert source_metadata dict to JSON string for PostgreSQL JSONB
        source_metadata_json = None
        if hasattr(file_record, 'source_metadata') and file_record.source_metadata is not None:
            if isinstance(file_record.source_metadata, dict):
                source_metadata_json = json.dumps(file_record.source_metadata)
        
        # Fix timezone issues for datetime fields
        source_created_at = convert_to_utc_naive(getattr(file_record, 'source_created_at', None))
        source_modified_at = convert_to_utc_naive(getattr(file_record, 'source_modified_at', None))
        upload_time = convert_to_utc_naive(file_record.upload_time)
        
        file_record_copy = FileRecord(
            id=file_record.id,
            sync_run_id=file_record.sync_run_id,
            original_uri=file_record.original_uri,
            rag_uri=file_record.rag_uri,
            file_hash=file_record.file_hash,
            uuid_filename=file_record.uuid_filename,
            upload_time=upload_time,
            file_size=file_record.file_size,
            status=file_record.status,
            error_message=getattr(file_record, 'error_message', None),
            source_id=getattr(file_record, 'source_id', None),
            source_type=getattr(file_record, 'source_type', None),
            source_path=getattr(file_record, 'source_path', None),
            content_type=getattr(file_record, 'content_type', None),
            source_metadata=source_metadata_json,
            source_created_at=source_created_at,
            source_modified_at=source_modified_at,
            updated_at=getattr(file_record, 'updated_at', None)
        )
        
        return await self._repository.create_file_record_original(file_record_copy)
    
    async def get_knowledge_base(self, knowledge_base_id: int):
        """Get knowledge base - delegated to regular repository."""
        return await self._repository.get_knowledge_base(knowledge_base_id)
    
    async def get_latest_file_records_for_kb(self, kb_name: str):
        """Get latest file records for KB - delegated to regular repository."""
        return await self._repository.get_latest_file_records_for_kb(kb_name)
    
    async def get_file_records_by_uri(self, uri: str):
        """Get file records by URI - delegated to regular repository."""
        return await self._repository.get_file_records_by_uri(uri)