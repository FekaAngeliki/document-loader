import hashlib
import uuid
from typing import Tuple, Optional
import aiofiles

class FileProcessor:
    """Handles file processing operations."""
    
    async def calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    async def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def generate_uuid_filename(self, original_filename: str, existing_uuid: Optional[str] = None) -> str:
        """Generate a UUID-based filename or use existing UUID."""
        file_extension = ""
        if '.' in original_filename:
            file_extension = '.' + original_filename.split('.')[-1]
        
        # If we have an existing UUID, preserve it
        if existing_uuid:
            # Extract just the UUID part if it includes extension
            if '.' in existing_uuid:
                uuid_part = existing_uuid.split('.')[0]
            else:
                uuid_part = existing_uuid
            return f"{uuid_part}{file_extension}"
        
        # Generate new UUID only if none exists
        return f"{uuid.uuid4()}{file_extension}"
    
    def generate_rag_uri(self, kb_name: str, uuid_filename: str) -> str:
        """Generate the URI for the RAG system."""
        return f"/{kb_name}/{uuid_filename}"
    
    async def process_file(self, content: bytes, original_filename: str, kb_name: str, 
                          existing_uuid: Optional[str] = None) -> Tuple[str, str, str]:
        """Process a file and return hash, UUID filename, and RAG URI."""
        file_hash = await self.calculate_hash(content)
        uuid_filename = self.generate_uuid_filename(original_filename, existing_uuid)
        rag_uri = self.generate_rag_uri(kb_name, uuid_filename)
        
        return file_hash, uuid_filename, rag_uri