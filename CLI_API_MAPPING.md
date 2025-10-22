# CLI to API Mapping - Corporate Web Service

This document maps all CLI commands to their corresponding API endpoints for corporate integration.

## Why API over CLI for Corporate Use?

**✅ Corporate Benefits:**
- **Centralized Control**: Single authentication/authorization point
- **Audit Trail**: All operations logged through banking-grade audit system
- **Role-Based Access**: Fine-grained permissions vs broad CLI access
- **Integration Ready**: Easy integration with dashboards, CI/CD, automation
- **Compliance**: Better governance over who can perform schema operations
- **Remote Access**: No need for server access to run operations
- **Standardization**: Consistent API patterns across the organization

## Authentication

All API endpoints require authentication via JWT tokens. In development mode, authentication is bypassed for localhost.

**Production Authentication:**
- Bearer token in Authorization header
- Role-based access control (RBAC)
- Business unit restrictions
- Comprehensive audit logging

## API Base URL

- **Development**: `http://localhost:8080/api/v1`
- **Production**: `https://your-domain.com/api/v1`

## Schema Management

### Create Schema
```bash
# CLI
document-loader create-schema --name "finance-dept" --description "Finance Department Documents"

# API
POST /api/v1/schemas
{
  "name": "finance-dept",
  "description": "Finance Department Documents"
}
```

### List Schemas
```bash
# CLI
document-loader list-schemas

# API
GET /api/v1/schemas
```

### Get Schema Info
```bash
# CLI
document-loader --schema finance-dept schema-info

# API
GET /api/v1/schemas/finance-dept
```

### Drop Schema
```bash
# CLI
document-loader drop-schema --name finance-dept --force

# API
DELETE /api/v1/schemas/finance-dept?force=true
```

### List Knowledge Bases in Schema
```bash
# CLI
document-loader --schema finance-dept list

# API
GET /api/v1/schemas/finance-dept/knowledge-bases
```

## CLI Operations

### Database Connection Test
```bash
# CLI
document-loader check-connection
document-loader --schema finance-dept check-connection

# API
GET /api/v1/cli/health/connection
GET /api/v1/cli/health/connection?schema=finance-dept
```

### Configuration Management
```bash
# CLI
document-loader config upload config.json --overwrite
document-loader --schema finance-dept config upload config.json

# API
POST /api/v1/cli/config/upload?schema=finance-dept
{
  "config_data": {...},
  "overwrite": true
}

# CLI
document-loader config list
document-loader --schema finance-dept config list

# API
GET /api/v1/cli/config/list
GET /api/v1/cli/config/list?schema=finance-dept
```

### Knowledge Base Management
```bash
# CLI
document-loader list
document-loader --schema finance-dept list

# API
GET /api/v1/cli/knowledge-bases/list
GET /api/v1/cli/knowledge-bases/list?schema=finance-dept

# CLI
document-loader multi-source create-multi-kb --name "docs-kb" --source-type "file_system" --rag-type "azure_blob"

# API
POST /api/v1/cli/knowledge-bases/create?schema=finance-dept
{
  "kb_name": "docs-kb",
  "source_type": "file_system",
  "source_config": {...},
  "rag_type": "azure_blob",
  "rag_config": {...}
}
```

### Synchronization Operations
```bash
# CLI
document-loader sync docs-kb --force
document-loader --schema finance-dept sync docs-kb

# API
POST /api/v1/cli/knowledge-bases/docs-kb/sync?schema=finance-dept&force=true

# CLI
document-loader status docs-kb

# API
GET /api/v1/cli/knowledge-bases/docs-kb/status?schema=finance-dept
```

### Knowledge Base Deletion
```bash
# CLI
document-loader delete docs-kb --force

# API
DELETE /api/v1/cli/knowledge-bases/docs-kb?schema=finance-dept&force=true
```

### List Source/RAG Types
```bash
# CLI
document-loader list-source-types
document-loader list-rag-types

# API
GET /api/v1/cli/source-types?schema=finance-dept
GET /api/v1/cli/rag-types?schema=finance-dept
```

## Role-Based Access Control

### Required Roles by Operation

| Operation | Required Roles |
|-----------|---------------|
| Schema Create/Delete | `ADMIN`, `SCHEMA_MANAGER` |
| Schema Read/List | All authenticated users |
| Knowledge Base Create/Delete | `ADMIN`, `KB_MANAGER` |
| Knowledge Base Sync | `ADMIN`, `KB_MANAGER`, `SYNC_OPERATOR` |
| Config Upload/Modify | `ADMIN`, `CONFIG_MANAGER` |
| Connection Testing | All authenticated users |

### User Roles Available

- **SUPER_ADMIN**: All permissions
- **ADMIN**: All schema and KB operations
- **SCHEMA_MANAGER**: Schema create/delete/read
- **CONFIG_MANAGER**: Configuration management
- **KB_MANAGER**: Knowledge base management
- **SYNC_OPERATOR**: Sync operations only
- **READ_ONLY**: Read access only

## Error Handling

All API endpoints return standardized error responses:

```json
{
  "detail": "Error message",
  "status_code": 400/401/403/500
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (authentication required)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)
- `409`: Conflict (resource already exists)
- `500`: Internal Server Error

## Corporate Integration Examples

### CI/CD Pipeline Integration
```bash
# Example Jenkins/GitLab CI pipeline
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "https://your-api.com/api/v1/schemas" \
     -d '{"name": "prod-finance", "description": "Production Finance Schema"}'
```

### Dashboard Integration
```javascript
// Frontend dashboard integration
const response = await fetch('/api/v1/schemas', {
  headers: {
    'Authorization': `Bearer ${userToken}`,
    'Content-Type': 'application/json'
  }
});
const schemas = await response.json();
```

### Automation Scripts
```python
# Python automation script
import requests

headers = {"Authorization": f"Bearer {jwt_token}"}
response = requests.post(
    "https://your-api.com/api/v1/cli/knowledge-bases/create",
    json=kb_config,
    headers=headers
)
```

## Interactive API Documentation

When running in development mode, visit:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

These provide interactive API documentation with try-it-out functionality.

## Security Considerations

1. **JWT Token Management**: Tokens should be securely stored and rotated
2. **HTTPS Only**: Production APIs must use HTTPS
3. **Rate Limiting**: Consider implementing API rate limits
4. **Audit Logging**: All operations are logged for compliance
5. **Schema Isolation**: Each schema provides data isolation between business units
6. **Role Validation**: Operations are validated against user roles and permissions

## Migration Strategy

1. **Phase 1**: Deploy API alongside existing CLI
2. **Phase 2**: Update automation scripts to use API
3. **Phase 3**: Integrate with corporate dashboards
4. **Phase 4**: Restrict direct CLI access in production
5. **Phase 5**: Full API-only operations for corporate governance