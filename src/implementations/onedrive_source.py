
import os
import requests
from typing import List, Dict, Any
from datetime import datetime

class FileMetadata:
    def __init__(self, uri: str, size: int, created_at: datetime, modified_at: datetime, content_type: str):
        self.uri = uri
        self.size = size
        self.created_at = created_at
        self.modified_at = modified_at
        self.content_type = content_type

class OneDriveSource:
    """OneDrive implementation of a file source."""
    def __init__(self, config: Dict[str, Any]):
        self.user_id = config.get("user_id")
        self.root_folder = config.get("root_folder", "/")
        self.recursive = config.get("recursive", True)
        self.account_type = config.get("account_type", "business")  # "business" or "personal"
        self.access_token = None
        self._initialized = False

    def initialize(self):
        """Authenticate and initialize the OneDrive source."""
        tenant_id = os.getenv("ONEDRIVE_TENANT_ID")
        client_id = os.getenv("ONEDRIVE_CLIENT_ID")
        client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET")
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("Missing OneDrive credentials in environment variables.")

        if self.account_type == "business":
            # Business/organizational OneDrive (client credentials)
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": client_id,
                "scope": "https://graph.microsoft.com/.default",
                "client_secret": client_secret,
                "grant_type": "client_credentials"
            }
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            self._initialized = True
        elif self.account_type == "personal":
            # Personal OneDrive (authorization code flow)
            try:
                from src.utils.onedrive_auth import get_personal_onedrive_token
                self.access_token = get_personal_onedrive_token()
                self._initialized = True
            except Exception as e:
                raise RuntimeError(f"Personal OneDrive authentication failed: {e}")
        else:
            raise ValueError(f"Unknown account_type: {self.account_type}")

    def list_files(self, path: str = None) -> List[FileMetadata]:
        """List all files in the OneDrive source."""
        if not self._initialized:
            self.initialize()
        folder = path if path else self.root_folder
        files = self._list_files_in_folder(folder)
        return files

    def _list_files_in_folder(self, folder_path: str) -> List[FileMetadata]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/root:{folder_path}:/children"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        items = response.json().get("value", [])
        files = []
        for item in items:
            if item.get("folder") and self.recursive:
                subfolder = folder_path + "/" + item["name"]
                files.extend(self._list_files_in_folder(subfolder))
            elif not item.get("folder"):
                metadata = self._get_file_metadata(item)
                files.append(metadata)
        return files

    def _get_file_metadata(self, item: Dict[str, Any]) -> FileMetadata:
        uri = item.get("webUrl")
        size = item.get("size", 0)
        created_at = datetime.strptime(item.get("createdDateTime"), "%Y-%m-%dT%H:%M:%S.%fZ") if item.get("createdDateTime") else None
        modified_at = datetime.strptime(item.get("lastModifiedDateTime"), "%Y-%m-%dT%H:%M:%S.%fZ") if item.get("lastModifiedDateTime") else None
        content_type = item.get("file", {}).get("mimeType", "application/octet-stream")
        return FileMetadata(uri, size, created_at, modified_at, content_type)

    def get_file_content(self, file_id: str) -> bytes:
        """Download file content by file ID."""
        if not self._initialized:
            self.initialize()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/items/{file_id}/content"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content

    def get_file_metadata(self, file_id: str) -> FileMetadata:
        """Get metadata for a file by file ID."""
        if not self._initialized:
            self.initialize()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/items/{file_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        item = response.json()
        return self._get_file_metadata(item)

    def exists(self, file_id: str) -> bool:
        """Check if a file exists by file ID."""
        if not self._initialized:
            self.initialize()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/items/{file_id}"
        response = requests.get(url, headers=headers)
        return response.status_code == 200

    def cleanup(self):
        """Clean up resources (noop for OneDrive)."""
        pass
