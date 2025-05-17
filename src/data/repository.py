from pydapper import connect
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import KnowledgeBase, SyncRun, FileRecord, SourceType, RagType
from .database import Database, JSONEncoder

class Repository:
    def __init__(self, database: Database):
        self.db = database
    
    async def create_knowledge_base(self, kb: KnowledgeBase) -> int:
        """Create a new knowledge base."""
        query = """
            INSERT INTO knowledge_base 
            (name, source_type, source_config, rag_type, rag_config)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """
        
        return await self.db.fetchval(
            query,
            kb.name,
            kb.source_type,
            json.dumps(kb.source_config, cls=JSONEncoder),
            kb.rag_type,
            json.dumps(kb.rag_config, cls=JSONEncoder)
        )
    
    async def get_knowledge_base(self, kb_id: int) -> Optional[KnowledgeBase]:
        """Get a knowledge base by ID."""
        query = """
            SELECT id, name, source_type, source_config, rag_type, rag_config,
                   created_at, updated_at
            FROM knowledge_base
            WHERE id = $1
        """
        
        row = await self.db.fetchrow(query, kb_id)
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
    
    async def get_knowledge_base_by_name(self, name: str) -> Optional[KnowledgeBase]:
        """Get a knowledge base by name."""
        query = """
            SELECT id, name, source_type, source_config, rag_type, rag_config,
                   created_at, updated_at
            FROM knowledge_base
            WHERE name = $1
        """
        
        row = await self.db.fetchrow(query, name)
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
    
    async def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """List all knowledge bases."""
        query = """
            SELECT id, name, source_type, source_config, rag_type, rag_config,
                   created_at, updated_at
            FROM knowledge_base
            ORDER BY name
        """
        
        rows = await self.db.fetch(query)
        return [
            KnowledgeBase(
                id=row['id'],
                name=row['name'],
                source_type=row['source_type'],
                source_config=json.loads(row['source_config']),
                rag_type=row['rag_type'],
                rag_config=json.loads(row['rag_config']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]
    
    async def update_knowledge_base(self, kb_name: str, updates: Dict[str, Any]) -> bool:
        """Update a knowledge base configuration."""
        # Build the update query dynamically based on provided fields
        update_fields = []
        params = []
        param_count = 1
        
        if 'source_type' in updates:
            update_fields.append(f"source_type = ${param_count}")
            params.append(updates['source_type'])
            param_count += 1
        
        if 'source_config' in updates:
            update_fields.append(f"source_config = ${param_count}")
            params.append(json.dumps(updates['source_config'], cls=JSONEncoder))
            param_count += 1
        
        if 'rag_type' in updates:
            update_fields.append(f"rag_type = ${param_count}")
            params.append(updates['rag_type'])
            param_count += 1
        
        if 'rag_config' in updates:
            update_fields.append(f"rag_config = ${param_count}")
            params.append(json.dumps(updates['rag_config'], cls=JSONEncoder))
            param_count += 1
        
        if not update_fields:
            return False
        
        # Always update the updated_at timestamp
        update_fields.append(f"updated_at = ${param_count}")
        params.append(datetime.utcnow())
        param_count += 1
        
        # Add the WHERE clause parameter
        params.append(kb_name)
        
        query = f"""
            UPDATE knowledge_base
            SET {', '.join(update_fields)}
            WHERE name = ${param_count}
        """
        
        result = await self.db.execute(query, *params)
        return result != "UPDATE 0"
    
    async def get_source_types(self) -> List[Dict[str, Any]]:
        """Get all available source types."""
        query = "SELECT id, name, class_name, config_schema FROM source_type ORDER BY name"
        rows = await self.db.fetch(query)
        return [dict(row) for row in rows]
    
    async def get_rag_types(self) -> List[Dict[str, Any]]:
        """Get all available RAG types."""
        query = "SELECT id, name, class_name, config_schema FROM rag_type ORDER BY name"
        rows = await self.db.fetch(query)
        return [dict(row) for row in rows]
    
    async def create_sync_run(self, knowledge_base_id: int, status: str = 'running') -> int:
        """Create a new sync run."""
        query = """
            INSERT INTO sync_run
            (knowledge_base_id, start_time, status)
            VALUES ($1, $2, $3)
            RETURNING id
        """
        
        return await self.db.fetchval(
            query,
            knowledge_base_id,
            datetime.utcnow(),
            status
        )
    
    async def update_sync_run(self, sync_run: SyncRun):
        """Update a sync run."""
        query = """
            UPDATE sync_run
            SET end_time = $2, status = $3, total_files = $4,
                new_files = $5, modified_files = $6, deleted_files = $7,
                error_message = $8
            WHERE id = $1
        """
        
        await self.db.execute(
            query,
            sync_run.id,
            sync_run.end_time,
            sync_run.status,
            sync_run.total_files,
            sync_run.new_files,
            sync_run.modified_files,
            sync_run.deleted_files,
            sync_run.error_message
        )
    
    async def create_file_record_original(self, file_record: FileRecord) -> int:
        """Create a new file record."""
        query = """
            INSERT INTO file_record
            (sync_run_id, original_uri, rag_uri, file_hash, uuid_filename,
             upload_time, file_size, status, error_message)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """
        
        return await self.db.fetchval(
            query,
            file_record.sync_run_id,
            file_record.original_uri,
            file_record.rag_uri,
            file_record.file_hash,
            file_record.uuid_filename,
            file_record.upload_time,
            file_record.file_size,
            file_record.status,
            file_record.error_message
        )
    
    async def update_sync_run_status(self, sync_run_id: int, status: str, error_message: str = None):
        """Update sync run status (simpler method for scanner)."""
        query = """
            UPDATE sync_run
            SET status = $2, 
                end_time = $3,
                error_message = $4
            WHERE id = $1
        """
        
        end_statuses = ('completed', 'failed', 'scan_completed', 'scan_failed')
        await self.db.execute(
            query,
            sync_run_id,
            status,
            datetime.utcnow() if status in end_statuses else None,
            error_message
        )
    
    async def update_sync_run_stats(self, sync_run_id: int, stats: Dict[str, int]):
        """Update sync run statistics."""
        query = """
            UPDATE sync_run
            SET total_files = $2,
                new_files = $3,
                modified_files = $4
            WHERE id = $1
        """
        
        await self.db.execute(
            query,
            sync_run_id,
            stats.get('total', 0),
            stats.get('new', 0),
            stats.get('modified', 0)
        )
    
    async def create_file_record(self, file_data: Dict[str, Any]) -> int:
        """Create a new file record (overloaded for dict input)."""
        # Handle both FileRecord object and dict input
        if isinstance(file_data, dict):
            query = """
                INSERT INTO file_record
                (sync_run_id, original_uri, rag_uri, file_hash, uuid_filename,
                 upload_time, file_size, status, error_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """
            
            return await self.db.fetchval(
                query,
                file_data['sync_run_id'],
                file_data['original_uri'],
                file_data.get('rag_uri'),
                file_data['file_hash'],
                file_data['uuid_filename'],
                datetime.utcnow(),
                file_data.get('size', 0),
                file_data.get('status', 'uploaded'),
                file_data.get('error_message')
            )
        else:
            # Original implementation for FileRecord object
            return await self.create_file_record_object(file_data)
    
    async def create_file_record_object(self, file_record: FileRecord) -> int:
        """Create a new file record from FileRecord object."""
        query = """
            INSERT INTO file_record
            (sync_run_id, original_uri, rag_uri, file_hash, uuid_filename,
             upload_time, file_size, status, error_message)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """
        
        return await self.db.fetchval(
            query,
            file_record.sync_run_id,
            file_record.original_uri,
            file_record.rag_uri,
            file_record.file_hash,
            file_record.uuid_filename,
            file_record.upload_time,
            file_record.file_size,
            file_record.status,
            file_record.error_message
        )
    
    async def get_file_record_by_uri(self, original_uri: str, knowledge_base_id: int) -> Optional[FileRecord]:
        """Get the most recent file record for a URI in a knowledge base."""
        query = """
            SELECT fr.* 
            FROM file_record fr
            JOIN sync_run sr ON fr.sync_run_id = sr.id
            WHERE fr.original_uri = $1 
            AND sr.knowledge_base_id = $2
            ORDER BY fr.created_at DESC
            LIMIT 1
        """
        
        row = await self.db.fetchrow(query, original_uri, knowledge_base_id)
        if not row:
            return None
        
        return FileRecord(
            id=row['id'],
            sync_run_id=row['sync_run_id'],
            original_uri=row['original_uri'],
            rag_uri=row['rag_uri'],
            file_hash=row['file_hash'],
            uuid_filename=row['uuid_filename'],
            upload_time=row['upload_time'],
            file_size=row['file_size'],
            status=row['status'],
            error_message=row['error_message'],
            created_at=row['created_at']
        )
    
    async def get_source_type(self, name: str) -> Optional[SourceType]:
        """Get a source type by name."""
        query = """
            SELECT id, name, class_name, config_schema
            FROM source_type
            WHERE name = $1
        """
        
        row = await self.db.fetchrow(query, name)
        if not row:
            return None
        
        return SourceType(
            id=row['id'],
            name=row['name'],
            class_name=row['class_name'],
            config_schema=json.loads(row['config_schema'])
        )
    
    async def get_rag_type(self, name: str) -> Optional[RagType]:
        """Get a RAG type by name."""
        query = """
            SELECT id, name, class_name, config_schema
            FROM rag_type
            WHERE name = $1
        """
        
        row = await self.db.fetchrow(query, name)
        if not row:
            return None
        
        return RagType(
            id=row['id'],
            name=row['name'],
            class_name=row['class_name'],
            config_schema=json.loads(row['config_schema'])
        )
    
    async def get_last_sync_run(self, knowledge_base_id: int) -> Optional[SyncRun]:
        """Get the most recent sync run for a knowledge base."""
        query = """
            SELECT id, knowledge_base_id, start_time, end_time, status,
                   total_files, new_files, modified_files, deleted_files,
                   error_message, created_at
            FROM sync_run
            WHERE knowledge_base_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        row = await self.db.fetchrow(query, knowledge_base_id)
        if not row:
            return None
        
        return SyncRun(
            id=row['id'],
            knowledge_base_id=row['knowledge_base_id'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            status=row['status'],
            total_files=row['total_files'],
            new_files=row['new_files'],
            modified_files=row['modified_files'],
            deleted_files=row['deleted_files'],
            error_message=row['error_message'],
            created_at=row['created_at']
        )
    
    async def get_file_records_by_sync_run(self, sync_run_id: int) -> List[FileRecord]:
        """Get all file records for a specific sync run."""
        query = """
            SELECT id, sync_run_id, original_uri, rag_uri, file_hash,
                   uuid_filename, upload_time, file_size, status,
                   error_message, created_at
            FROM file_record
            WHERE sync_run_id = $1
            ORDER BY original_uri
        """
        
        rows = await self.db.fetch(query, sync_run_id)
        return [
            FileRecord(
                id=row['id'],
                sync_run_id=row['sync_run_id'],
                original_uri=row['original_uri'],
                rag_uri=row['rag_uri'],
                file_hash=row['file_hash'],
                uuid_filename=row['uuid_filename'],
                upload_time=row['upload_time'],
                file_size=row['file_size'],
                status=row['status'],
                error_message=row['error_message'],
                created_at=row['created_at']
            )
            for row in rows
        ]
    
    async def get_latest_file_records_for_kb(self, kb_name: str) -> List[FileRecord]:
        """Get the most recent file record for each unique URI in a knowledge base."""
        query = """
            SELECT DISTINCT ON (fr.original_uri) 
                fr.id,
                fr.sync_run_id,
                fr.original_uri,
                fr.rag_uri,
                fr.file_hash,
                fr.uuid_filename,
                fr.upload_time,
                fr.file_size,
                fr.status,
                fr.error_message,
                fr.created_at
            FROM file_record fr
            JOIN sync_run sr ON fr.sync_run_id = sr.id
            JOIN knowledge_base kb ON sr.knowledge_base_id = kb.id
            WHERE kb.name = $1
            ORDER BY fr.original_uri, fr.created_at DESC
        """
        
        rows = await self.db.fetch(query, kb_name)
        
        return [
            FileRecord(
                id=row['id'],
                sync_run_id=row['sync_run_id'],
                original_uri=row['original_uri'],
                rag_uri=row['rag_uri'],
                file_hash=row['file_hash'],
                uuid_filename=row['uuid_filename'],
                upload_time=row['upload_time'],
                file_size=row['file_size'],
                status=row['status'],
                error_message=row['error_message'],
                created_at=row['created_at']
            )
            for row in rows
        ]