"""
Delta Sync Manager for Graph API Delta Queries

Manages delta tokens for efficient incremental sync with Microsoft Graph API.
Only retrieves changed files since last sync instead of listing all files.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DeltaToken:
    """Represents a stored delta token for a drive."""
    source_id: str
    drive_id: str
    token: str
    last_sync_time: datetime

class DeltaSyncManager:
    """Manages delta sync tokens for Graph API delta queries."""
    
    def __init__(self, database):
        self.db = database
    
    async def get_delta_token(self, source_id: str, drive_id: str) -> Optional[str]:
        """Get the stored delta token for a source/drive combination."""
        try:
            query = """
                SELECT delta_token 
                FROM delta_sync_tokens 
                WHERE source_id = $1 AND drive_id = $2
            """
            result = await self.db.fetchval(query, source_id, drive_id)
            
            if result:
                logger.info(f"Found delta token for {source_id}/{drive_id}")
                return result
            else:
                logger.info(f"No delta token found for {source_id}/{drive_id} - will perform full sync")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving delta token: {e}")
            return None
    
    async def save_delta_token(self, source_id: str, source_type: str, drive_id: str, delta_token: str) -> bool:
        """Save or update a delta token."""
        try:
            query = """
                INSERT INTO delta_sync_tokens (source_id, source_type, drive_id, delta_token, last_sync_time)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (source_id, drive_id)
                DO UPDATE SET 
                    delta_token = $4,
                    last_sync_time = NOW(),
                    updated_at = NOW()
            """
            await self.db.execute(query, source_id, source_type, drive_id, delta_token)
            logger.info(f"Saved delta token for {source_id}/{drive_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving delta token: {e}")
            return False
    
    async def clear_delta_token(self, source_id: str, drive_id: str) -> bool:
        """Clear a delta token (forces full sync next time)."""
        try:
            query = """
                DELETE FROM delta_sync_tokens 
                WHERE source_id = $1 AND drive_id = $2
            """
            await self.db.execute(query, source_id, drive_id)
            logger.info(f"Cleared delta token for {source_id}/{drive_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing delta token: {e}")
            return False
    
    async def get_all_tokens_for_source(self, source_id: str) -> Dict[str, DeltaToken]:
        """Get all delta tokens for a source (multiple drives)."""
        try:
            query = """
                SELECT source_id, drive_id, delta_token, last_sync_time
                FROM delta_sync_tokens 
                WHERE source_id = $1
            """
            rows = await self.db.fetch(query, source_id)
            
            tokens = {}
            for row in rows:
                tokens[row['drive_id']] = DeltaToken(
                    source_id=row['source_id'],
                    drive_id=row['drive_id'],
                    token=row['delta_token'],
                    last_sync_time=row['last_sync_time']
                )
            
            logger.info(f"Found {len(tokens)} delta tokens for source {source_id}")
            return tokens
            
        except Exception as e:
            logger.error(f"Error retrieving tokens for source {source_id}: {e}")
            return {}
    
    async def cleanup_old_tokens(self, days_old: int = 30) -> int:
        """Clean up delta tokens older than specified days."""
        try:
            query = """
                DELETE FROM delta_sync_tokens 
                WHERE last_sync_time < NOW() - INTERVAL '%s days'
            """
            result = await self.db.execute(query, days_old)
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Cleaned up {count} old delta tokens (older than {days_old} days)")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old tokens: {e}")
            return 0
    
    def extract_delta_token(self, graph_response: Dict[str, Any]) -> Optional[str]:
        """Extract delta token from Graph API response."""
        try:
            # Delta token is in @odata.deltaLink or @odata.nextLink
            delta_link = graph_response.get('@odata.deltaLink')
            if delta_link:
                logger.debug("Found @odata.deltaLink in response")
                return delta_link
            
            next_link = graph_response.get('@odata.nextLink')
            if next_link:
                logger.debug("Found @odata.nextLink in response")
                return next_link
            
            logger.warning("No delta token found in Graph API response")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting delta token: {e}")
            return None