import os
import json
from src.implementations.onedrive_source import OneDriveSource
from dotenv import load_dotenv

# Load OneDrive credentials from .env.onedrive
load_dotenv(dotenv_path=".env.onedrive")

CONFIG_PATH = "configs/onedrive_test.json"

def main():
    with open(CONFIG_PATH, "r") as f:
        configs = json.load(f)
    for cfg in configs:
        if cfg.get("type") == "onedrive":
            print(f"Processing OneDrive for user: {cfg['user_id']} (account_type: {cfg.get('account_type', 'business')})")
            source = OneDriveSource(cfg)
            files = source.list_files()
            print(f"Found {len(files)} files:")
            for file in files:
                if hasattr(file, 'uri'):
                    print(f"- {getattr(file, 'uri', file)}")
                else:
                    print(f"- {file}")

if __name__ == "__main__":
    main()
