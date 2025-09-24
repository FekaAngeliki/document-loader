#!/usr/bin/env python3
"""
Test script to verify environment variable loading.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the CLI module to trigger dotenv loading
from document_loader import cli

print("🔍 Testing Environment Variable Loading")
print("=" * 50)

# Check if SharePoint environment variables are loaded
sharepoint_vars = [
    'SHAREPOINT_TENANT_ID',
    'SHAREPOINT_CLIENT_ID', 
    'SHAREPOINT_CLIENT_SECRET'
]

print("\n📋 SharePoint Environment Variables:")
for var in sharepoint_vars:
    value = os.getenv(var)
    if value:
        # Mask the secret for security
        if 'SECRET' in var:
            masked_value = f"{value[:10]}..." if len(value) > 10 else "***"
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: Not set")

print("\n📋 Database Environment Variables:")
db_vars = [
    'DOCUMENT_LOADER_DB_HOST',
    'DOCUMENT_LOADER_DB_PORT',
    'DOCUMENT_LOADER_DB_NAME',
    'DOCUMENT_LOADER_DB_USER'
]

for var in db_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: Not set")

print("\n🎯 Result:")
all_sharepoint_set = all(os.getenv(var) for var in sharepoint_vars)
if all_sharepoint_set:
    print("✅ All SharePoint environment variables are loaded!")
    print("✅ The sync should now work properly.")
else:
    print("❌ Some SharePoint environment variables are missing.")
    print("❌ The sync will still fail with authentication errors.")