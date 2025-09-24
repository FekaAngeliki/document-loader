#!/usr/bin/env python3
"""
Test config file loading directly like the CLI does.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and load dotenv
from dotenv import load_dotenv
load_dotenv()

from src.utils.config_utils import load_config_with_env_expansion
from src.data.multi_source_models import create_multi_source_kb_from_config


def test_config_loading():
    """Test config loading exactly like the CLI does."""
    
    print("🔍 Testing Config File Loading (Like CLI)")
    print("=" * 60)
    
    config_file = "configs/internal-audit-kb-config.json"
    
    # Step 1: Check file exists
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_file}")
        return
    else:
        print(f"✅ Config file found: {config_file}")
    
    # Step 2: Load raw file content
    print(f"\n📄 Raw config file content:")
    with open(config_file, 'r') as f:
        raw_content = f.read()
    
    # Show tenant_id line specifically
    lines = raw_content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'tenant_id' in line:
            print(f"   Line {i}: {line.strip()}")
        if 'client_id' in line:
            print(f"   Line {i}: {line.strip()}")
        if 'client_secret' in line:
            print(f"   Line {i}: {line.strip()}")
    
    # Step 3: Load with environment expansion (like CLI does)
    print(f"\n🔄 Loading with environment expansion...")
    try:
        config = load_config_with_env_expansion(str(config_path))
        print(f"   ✅ Config loaded successfully")
        
        # Check the actual values
        source_config = config['sources'][0]['source_config']
        print(f"\n📋 Expanded values:")
        print(f"   tenant_id: {source_config.get('tenant_id')}")
        print(f"   client_id: {source_config.get('client_id')}")
        print(f"   client_secret: {source_config.get('client_secret')[:10]}..." if source_config.get('client_secret') else 'NOT SET')
        
        # Check for remaining placeholders
        config_str = str(source_config)
        if '${' in config_str:
            print(f"\n❌ Still contains placeholders:")
            for key, value in source_config.items():
                if isinstance(value, str) and '${' in value:
                    print(f"   {key}: {value}")
        else:
            print(f"\n✅ No placeholders remain")
        
    except Exception as e:
        print(f"   ❌ Config loading failed: {e}")
        return
    
    # Step 4: Create multi-source KB (like CLI does)
    print(f"\n🏗️  Creating multi-source KB object...")
    try:
        multi_kb = create_multi_source_kb_from_config(config)
        print(f"   ✅ Multi-KB created: {multi_kb.name}")
        
        # Check the source values in the created object
        source = multi_kb.sources[0]
        print(f"\n📋 Values in created KB:")
        source_config = source.source_config
        print(f"   tenant_id: {source_config.get('tenant_id')}")
        print(f"   client_id: {source_config.get('client_id')}")  
        print(f"   client_secret: {source_config.get('client_secret')[:10]}..." if source_config.get('client_secret') else 'NOT SET')
        
    except Exception as e:
        print(f"   ❌ Multi-KB creation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_config_loading()