import json
import asyncio
import glob
import os
import sys
from src.implementations.sharepoint_source import SharePointSource
from dotenv import load_dotenv

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs')
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.sharepoint'))

def inject_env_credentials(config):
    config['tenant_id'] = os.getenv('SHAREPOINT_TENANT_ID')
    config['client_id'] = os.getenv('SHAREPOINT_CLIENT_ID')
    config['client_secret'] = os.getenv('SHAREPOINT_CLIENT_SECRET')
    return config

async def process_config(config):
    config = inject_env_credentials(config)
    source = SharePointSource(config)
    await source.initialize()
    if config.get('type') == 'library':
        print(f"\nProcessing Document Library: {config.get('name')}")
        files = await source.list_files_in_library(config['path'], config.get('recursive', True))
        print(f"Found {len(files)} files.")
        for f in files:
            print(f"  - {f['name']} ({f['url']})")
    elif config.get('type') == 'site_pages':
        print(f"\nProcessing Site Pages Library: {config.get('name', 'Site Pages')}")
        pages = await source.list_site_pages()
        print(f"Found {len(pages)} pages.")
        for p in pages:
            print(f"  - {p['name']} ({p['url']})")
    elif config.get('type') == 'list':
        print(f"\nProcessing List: {config.get('name')}")
        items = await source.list_items_in_list(config['list_title'])
        print(f"Found {len(items)} items.")
        for item in items:
            print(f"  - {item}")
    else:
        print(f"Unknown type in config: {config}")

async def main():
    # Accept config filename as a command-line argument
    if len(sys.argv) > 1:
        config_files = [os.path.join(CONFIG_DIR, sys.argv[1])]
    else:
        config_files = glob.glob(os.path.join(CONFIG_DIR, '*.json'))
    all_configs = []
    for file_path in config_files:
        with open(file_path) as f:
            loaded = json.load(f)
            if isinstance(loaded, list):
                all_configs.extend(loaded)
            else:
                all_configs.append(loaded)
    for config in all_configs:
        await process_config(config)

if __name__ == "__main__":
    asyncio.run(main())
