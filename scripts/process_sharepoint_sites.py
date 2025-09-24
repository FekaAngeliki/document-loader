
import json
import asyncio
import glob
import os
from src.implementations.sharepoint_source import SharePointSource
from dotenv import load_dotenv

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs')
env_path = os.path.join(os.path.dirname(__file__), '..', '.env.sharepoint')
load_dotenv(env_path)

def inject_env_credentials(config):
    # Always inject credentials from environment
    config['tenant_id'] = os.getenv('SHAREPOINT_TENANT_ID')
    config['client_id'] = os.getenv('SHAREPOINT_CLIENT_ID')
    config['client_secret'] = os.getenv('SHAREPOINT_CLIENT_SECRET')
    return config

async def process_site(config):
    config = inject_env_credentials(config)
    source = SharePointSource(config)
    await source.initialize()
    files = await source.list_files()
    print(f"Site: {config['name']}, Files found: {len(files)}")
    # Extend here for sync, download, etc.

async def main():
    config_files = glob.glob(os.path.join(CONFIG_DIR, '*.json'))
    all_configs = []
    for file_path in config_files:
        with open(file_path) as f:
            loaded = json.load(f)
            if isinstance(loaded, list):
                all_configs.extend(loaded)
            else:
                all_configs.append(loaded)
    tasks = [process_site(cfg) for cfg in all_configs]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
