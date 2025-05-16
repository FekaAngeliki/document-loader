from typing import List, Optional
from .repository import Repository
from .models import SyncRun

class ExtendedRepository(Repository):
    """Extended repository with additional queries."""
    
    async def get_sync_runs_for_kb(self, knowledge_base_id: int, limit: int = 10) -> List[SyncRun]:
        """Get sync runs for a knowledge base."""
        query = """
            SELECT id, knowledge_base_id, start_time, end_time, status,
                   total_files, new_files, modified_files, deleted_files,
                   error_message, created_at
            FROM sync_run
            WHERE knowledge_base_id = $1
            ORDER BY start_time DESC
            LIMIT $2
        """
        
        rows = await self.db.fetch(query, knowledge_base_id, limit)
        return [
            SyncRun(
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
            for row in rows
        ]
    
    async def get_last_sync_run(self, knowledge_base_id: int) -> Optional[SyncRun]:
        """Get the last sync run for a knowledge base."""
        runs = await self.get_sync_runs_for_kb(knowledge_base_id, limit=1)
        return runs[0] if runs else None