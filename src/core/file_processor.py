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
    
    def generate_uuid_filename(self, original_filename: str, existing_uuid: Optional[str] = None, 
                              full_path: Optional[str] = None) -> str:
        """Generate a UUID-based filename or use existing UUID.
        
        Args:
            original_filename: The original filename (can be full path)
            existing_uuid: If provided, use this existing UUID
            full_path: The full absolute path, used for deterministic UUID generation
        """
        # Extract the actual filename from path if needed
        from pathlib import Path
        filename_only = Path(original_filename).name
        
        file_extension = ""
        if '.' in filename_only:
            file_extension = '.' + filename_only.split('.')[-1]
        
        # If we have an existing UUID, preserve it
        if existing_uuid:
            # Extract just the UUID part if it includes extension
            if '.' in existing_uuid:
                uuid_part = existing_uuid.split('.')[0]
            else:
                uuid_part = existing_uuid
            return f"{uuid_part}{file_extension}"
        
        # Generate deterministic UUID based on full path
        if full_path:
            # Use the full path to generate a deterministic UUID
            # This ensures the same file always gets the same UUID
            import hashlib
            path_hash = hashlib.sha256(full_path.encode()).hexdigest()
            # Use first 32 chars of hash formatted as UUID
            uuid_part = f"{path_hash[:8]}-{path_hash[8:12]}-{path_hash[12:16]}-{path_hash[16:20]}-{path_hash[20:32]}"
            return f"{uuid_part}{file_extension}"
        
        # Fallback to random UUID only if no path is provided
        return f"{uuid.uuid4()}{file_extension}"
    
    def generate_rag_uri(self, kb_name: str, uuid_filename: str) -> str:
        """Generate the URI for the RAG system."""
        return f"/{kb_name}/{uuid_filename}"
    
    async def process_file(self, content: bytes, original_filename: str, kb_name: str, 
                          existing_uuid: Optional[str] = None) -> Tuple[str, str, str]:
        """Process a file and return hash, UUID filename, and RAG URI.
        
        Args:
            content: File content
            original_filename: Full path of the file
            kb_name: Knowledge base name
            existing_uuid: Existing UUID if available
        """
        file_hash = await self.calculate_hash(content)
        # Pass the full path for deterministic UUID generation
        uuid_filename = self.generate_uuid_filename(original_filename, existing_uuid, full_path=original_filename)
        rag_uri = self.generate_rag_uri(kb_name, uuid_filename)
        
        return file_hash, uuid_filename, rag_uri