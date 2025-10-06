# Azure Deployment Guide

This guide explains how to deploy the Document Loader application to Azure using Azure DevOps as the orchestrator.

## Architecture Overview

The deployment creates the following Azure resources:
- **Azure Container Registry (ACR)** - Stores Docker images
- **Azure Container Apps** - Runs the application with auto-scaling
- **Azure Database for PostgreSQL** - Managed database service
- **Azure Storage Account** - For blob storage and file uploads
- **Azure Key Vault** - Stores secrets and connection strings
- **Application Insights** - Monitoring and logging
- **Log Analytics Workspace** - Centralized logging

## Prerequisites

1. **Azure Subscription** with appropriate permissions
2. **Azure CLI** installed and configured
3. **Docker** installed for building images
4. **Azure DevOps** project with necessary service connections

## Quick Deployment

### 1. Manual Deployment (One-time setup)

```bash
# Clone the repository
git clone <your-repo-url>
cd document-loader

# Run the deployment script
./deployment/deploy.sh dev eastus

# For production
./deployment/deploy.sh prod eastus
```

### 2. Azure DevOps Pipeline Setup

1. **Create Service Connections** in Azure DevOps:
   - Azure Resource Manager connection to your subscription
   - Docker Registry connection to your ACR

2. **Import the pipeline**:
   - Go to Pipelines → Create Pipeline
   - Select your repository
   - Use existing Azure Pipelines YAML file: `deployment/azure-pipelines.yml`

3. **Configure Pipeline Variables**:
   ```yaml
   dockerRegistryServiceConnection: 'your-acr-connection-name'
   containerRegistry: 'yourregistry.azurecr.io'
   ```

4. **Set up Environments**:
   - Create `development` and `production` environments
   - Add approval gates for production deployments

## Infrastructure Details

### Resource Naming Convention
Resources follow the pattern: `{namePrefix}-{environment}-{uniqueSuffix}`

Example for development environment:
- Resource Group: `rg-docloader-dev`
- Container App: `docloader-dev-abc123-app`
- PostgreSQL: `docloader-dev-abc123-postgres`

### Environment Variables

The application requires these environment variables:
```bash
DOCUMENT_LOADER_DB_HOST=your-postgres-server.postgres.database.azure.com
DOCUMENT_LOADER_DB_PORT=5432
DOCUMENT_LOADER_DB_NAME=document_loader
DOCUMENT_LOADER_DB_USER=dbadmin
DOCUMENT_LOADER_DB_PASSWORD=<stored-in-keyvault>
DOCUMENT_LOADER_DB_MIN_POOL_SIZE=10
DOCUMENT_LOADER_DB_MAX_POOL_SIZE=20
APPLICATIONINSIGHTS_CONNECTION_STRING=<from-app-insights>
```

### Security Configuration

1. **Key Vault Access**: The Container App has system-assigned managed identity with Key Vault access
2. **Database Security**: PostgreSQL configured with SSL enforcement and firewall rules
3. **Network Security**: Container Apps Environment with internal networking
4. **Container Registry**: ACR with admin user enabled for pipeline access

## Database Initialization

After deployment, initialize the database:

```bash
# Get container app name
CONTAINER_APP_NAME="docloader-dev-<suffix>-app"
RESOURCE_GROUP="rg-docloader-dev"

# Initialize database
az containerapp exec \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --command "document-loader init-db --create-db"
```

## Monitoring and Logging

### Application Insights
- Application performance monitoring
- Custom telemetry and metrics
- Distributed tracing for multi-component operations

### Log Analytics
- Centralized logging from Container Apps
- Container logs and system metrics
- Custom log queries and alerts

### Monitoring Queries
```kusto
// Application logs
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "docloader-prod-app"
| order by TimeGenerated desc

// Performance metrics
requests
| where cloud_RoleName == "document-loader"
| summarize avg(duration) by bin(timestamp, 5m)
```

## Scaling Configuration

Container Apps auto-scaling rules:
- **Min Replicas**: 1
- **Max Replicas**: 3
- **CPU Scaling**: Scale when CPU > 70%
- **Memory**: 1GB per container
- **CPU**: 0.5 cores per container

## Backup and Recovery

### Database Backups
- Automated backups with 7-day retention
- Point-in-time recovery available
- Geo-redundant backup disabled (can be enabled for production)

### Application State
- Stateless application design
- Configuration stored in Key Vault
- File processing state tracked in PostgreSQL

## Troubleshooting

### Common Issues

1. **Container App won't start**:
   ```bash
   # Check logs
   az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP
   ```

2. **Database connection issues**:
   ```bash
   # Test connectivity
   az containerapp exec --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --command "document-loader check-connection"
   ```

3. **Pipeline failures**:
   - Check service connection permissions
   - Verify container registry access
   - Review pipeline logs in Azure DevOps

### Debugging Commands

```bash
# Get container app details
az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP

# Scale manually
az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --min-replicas 2 --max-replicas 5

# Update environment variables
az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --set-env-vars NEW_VAR=value
```

## Cost Optimization

### Development Environment
- Use Basic tier for ACR
- Burstable PostgreSQL instance (Standard_B1ms)
- Standard_LRS storage
- Minimal Container App scaling

### Production Environment
- Consider Standard tier for ACR
- General Purpose PostgreSQL (Standard_D2s_v3)
- Geo-redundant storage
- Appropriate scaling limits based on usage

## Security Best Practices

1. **Key Vault**: Store all secrets in Key Vault
2. **Managed Identity**: Use system-assigned managed identity for Azure resource access
3. **Network Security**: Configure virtual network integration for production
4. **SSL/TLS**: Enforce SSL for all database connections
5. **RBAC**: Use role-based access control for all resources
6. **Monitoring**: Enable security monitoring and alerts

## Next Steps

1. Set up automated testing in the pipeline
2. Configure alerting rules for production monitoring
3. Implement blue-green deployment strategy
4. Set up disaster recovery procedures
5. Configure backup automation for critical data