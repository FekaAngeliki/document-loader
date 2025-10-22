#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import asyncpg

async def hard_delete():
    try:
        # Use the same environment variables as the CLI
        connection = await asyncpg.connect(
            host=os.getenv('DOCUMENT_LOADER_DB_HOST', 'localhost'),
            port=int(os.getenv('DOCUMENT_LOADER_DB_PORT', 5432)),
            user=os.getenv('DOCUMENT_LOADER_DB_USER'),
            password=os.getenv('DOCUMENT_LOADER_DB_PASSWORD'),
            database=os.getenv('DOCUMENT_LOADER_DB_NAME')
        )
        
        result = await connection.execute("DELETE FROM config_assets WHERE name = $1", 'premium-rms-kb-config')
        print(f'✅ Hard deleted config record')
        print(f'Query result: {result}')
        
        await connection.close()
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    asyncio.run(hard_delete())
