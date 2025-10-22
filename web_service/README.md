# Document Loader Banking Web Service Facade

A banking-grade web service facade that provides business-oriented APIs for document synchronization operations with comprehensive audit logging, compliance controls, and enterprise security features.

## 🏦 Banking Features

- **Comprehensive Audit Logging**: SOX, GDPR, PCI compliance
- **Role-Based Access Control**: Granular permissions for banking operations  
- **Business Approval Workflows**: Risk-based approval requirements
- **Multi-Factor Authentication**: Enhanced security for banking environments
- **Business Context**: Operations include business justification and impact analysis
- **Emergency Procedures**: Fast-track operations for critical situations

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (for session management)
- Document Loader CLI (installed at `/opt/document-loader`)

### Development Setup

1. **Clone and setup environment:**
```bash
cd web_service
cp .env.example .env
# Edit .env with your configuration
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start development environment:**
```bash
docker-compose up -d
```

4. **Run the application:**
```bash
python -m app.main
```

The API will be available at `http://localhost:8080`

### Production Deployment

1. **Build production image:**
```bash
docker build -t document-loader-web-service:latest .
```

2. **Deploy with proper environment variables:**
```bash
docker run -d \
  --name document-loader-api \
  -p 8080:8080 \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=your-production-secret-key \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/document_loader \
  document-loader-web-service:latest
```

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Authenticate user
- `POST /api/v1/auth/logout` - Logout user
- `GET /api/v1/auth/me` - Get current user info

### Knowledge Bases (Business-Oriented)
- `GET /api/v1/knowledge-bases/` - List knowledge bases with business context
- `GET /api/v1/knowledge-bases/{kb_name}` - Get KB details and health status
- `POST /api/v1/knowledge-bases/{kb_name}/sync` - Initiate sync with business approval
- `POST /api/v1/knowledge-bases/{kb_name}/emergency-sync` - Emergency sync procedures
- `GET /api/v1/knowledge-bases/operations/{operation_id}` - Track operation status
- `GET /api/v1/knowledge-bases/metrics/business` - Business metrics and KPIs

### Administration
- `GET /api/v1/admin/audit-logs` - Access audit logs (compliance officers only)
- `GET /api/v1/admin/users` - User management (admin only)
- `POST /api/v1/admin/approvals/{approval_id}/approve` - Approve pending operations

## 🔐 Authentication & Authorization

### Role-Based Access Control

The system implements banking-grade RBAC with these roles:

- **Super Admin**: Full system access
- **IT Admin**: Technical operations and system configuration
- **Business Admin**: Business operations and KB management
- **Data Steward**: Data management and sync operations
- **Business Analyst**: Read access and sync requests
- **Compliance Officer**: Audit access and compliance reporting
- **Auditor**: Read-only audit and compliance access

### Permissions

Granular permissions control access to specific operations:

- `kb:create`, `kb:read`, `kb:update`, `kb:delete`, `kb:sync`
- `config:create`, `config:read`, `config:update`, `config:delete`
- `admin:users`, `admin:system`, `admin:audit`
- `emergency:sync`, `emergency:override`

### Example Authentication

```python
import httpx

# Login
response = httpx.post("http://localhost:8080/api/v1/auth/login", json={
    "username": "john.doe",
    "password": "secure_password"
})
token = response.json()["access_token"]

# Use token for API calls
headers = {"Authorization": f"Bearer {token}"}
response = httpx.get("http://localhost:8080/api/v1/knowledge-bases/", headers=headers)
```

## 📋 Business Operations

### Sync Request with Business Context

```python
import httpx

sync_request = {
    "business_justification": "Monthly compliance report generation requires updated documents",
    "business_unit": "compliance",
    "priority": "high",
    "config_name": "compliance-documents",
    "sync_mode": "parallel",
    "data_classification": "confidential"
}

response = httpx.post(
    "http://localhost:8080/api/v1/knowledge-bases/compliance-kb/sync",
    json=sync_request,
    headers={"Authorization": f"Bearer {token}"}
)

operation = response.json()
print(f"Operation ID: {operation['operation_id']}")
print(f"Status: {operation['status']}")
print(f"Approval Required: {operation['approval_required']}")
```

### Emergency Procedures

```python
emergency_request = {
    "config_name": "customer-documents",
    "incident_number": "INC-2024-001234", 
    "emergency_justification": "Customer complaint - missing loan documents affecting regulatory compliance",
    "approver_id": "manager.compliance",
    "business_impact": "Potential regulatory violation and customer service impact"
}

response = httpx.post(
    "http://localhost:8080/api/v1/knowledge-bases/customer-kb/emergency-sync",
    json=emergency_request,
    headers={"Authorization": f"Bearer {token}"}
)
```

## 🔍 Monitoring & Observability

### Health Checks

- `GET /health` - Basic health check
- `GET /ready` - Readiness check (includes database connectivity)

### Metrics

Prometheus metrics available at `/metrics`:

- `document_loader_sync_operations_total` - Total sync operations by business unit
- `document_loader_sync_duration_seconds` - Sync duration metrics
- `document_loader_api_requests_total` - API request metrics
- `document_loader_auth_requests_total` - Authentication metrics

### Audit Logging

All operations are automatically audited with:

- **User context**: User ID, business unit, session info
- **Business context**: Justification, impact, data classification
- **Technical details**: Resource IDs, operation results, errors
- **Compliance**: Applicable frameworks (SOX, GDPR, PCI)

## 🏗️ Integration with Control-M

### HTTP API Trigger

Control-M can trigger sync operations via HTTP:

```bash
# Control-M script
curl -X POST "https://documentloader-api.bank.com/api/v1/knowledge-bases/production-kb/sync" \
  -H "Authorization: Bearer $CONTROLM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_justification": "Scheduled daily document refresh for customer service systems",
    "business_unit": "technology",
    "priority": "medium",
    "config_name": "production-config",
    "sync_mode": "parallel"
  }'
```

### Monitoring Integration

Control-M can monitor operation status:

```bash
# Check operation status
OPERATION_ID=$(echo $SYNC_RESPONSE | jq -r '.operation_id')
curl "https://documentloader-api.bank.com/api/v1/knowledge-bases/operations/$OPERATION_ID" \
  -H "Authorization: Bearer $CONTROLM_TOKEN"
```

## 🔧 Configuration

### Environment Variables

Key configuration settings:

- `SECRET_KEY`: JWT signing key (min 32 characters)
- `DATABASE_URL`: PostgreSQL connection string
- `REQUIRE_MFA`: Enable multi-factor authentication
- `AUDIT_LOG_RETENTION_DAYS`: Audit log retention (default: 7 years)
- `COMPLIANCE_MODE`: Compliance framework (SOX, GDPR, PCI)

### Banking Security Requirements

For production banking environments:

1. **Enable MFA**: `REQUIRE_MFA=true`
2. **Short sessions**: `SESSION_TIMEOUT_MINUTES=15`
3. **Strong passwords**: `PASSWORD_MIN_LENGTH=12`
4. **Audit retention**: `AUDIT_LOG_RETENTION_DAYS=2555` (7 years)
5. **HTTPS only**: Configure TLS certificates
6. **Network security**: Restrict CORS origins and allowed hosts

## 📚 Business Use Cases

### 1. Scheduled Document Refresh

Business analysts can request scheduled document synchronization:

- **Business justification required**
- **Automatic risk assessment**
- **Approval workflow for high-risk operations**
- **Business impact tracking**

### 2. Compliance Reporting

Compliance officers can:

- **Access audit logs and compliance reports**
- **Track data processing activities**
- **Monitor sync operations affecting regulated data**
- **Generate compliance dashboards**

### 3. Emergency Response

For critical business situations:

- **Fast-track emergency sync procedures**
- **Enhanced audit trail for emergency operations**
- **Escalation to business stakeholders**
- **Post-incident reporting**

## 🆘 Support

### Error Handling

The API provides business-appropriate error messages:

```json
{
  "error_code": "KB_SYNC_FAILED",
  "error_category": "system_error", 
  "business_message": "Document synchronization temporarily unavailable",
  "business_impact": "Customer document updates delayed",
  "estimated_resolution_time": "30 minutes",
  "support_contact": "IT Support: ext-4357",
  "technical_reference": "op-12345-67890"
}
```

### Troubleshooting

Common issues and solutions:

1. **Authentication failures**: Check user roles and permissions
2. **Sync timeouts**: Review business justification and approval status
3. **Permission denied**: Verify user has required business unit access
4. **Database connectivity**: Check PostgreSQL connection and credentials

### Contact Information

- **Technical Support**: IT Support (ext-4357)
- **Business Support**: Data Stewards (data-team@bank.com)
- **Compliance Questions**: Compliance Office (compliance@bank.com)
- **Emergency Escalation**: Emergency Ops (ext-911)

---

*This web service facade transforms the technical document-loader CLI into a banking-appropriate business service with comprehensive governance, security, and compliance features.*