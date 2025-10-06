# Azure Scheduled Delta Sync Deployment Options

This document provides multiple approaches to implement scheduled delta sync execution on Azure infrastructure.

## 🎯 Executive Summary

| Option | Cost | Complexity | Scalability | Best For |
|--------|------|------------|-------------|----------|
| Azure Container Apps | Medium | Low | High | Production workloads |
| Azure DevOps Pipelines | Low | Medium | Medium | CI/CD integrated |
| Azure Functions | Low | Medium | High | Serverless preference |
| Azure Container Instances | Low | Low | Low | Simple scheduled tasks |

## 🚀 Option 1: Azure Container Apps (Recommended)

**Best for:** Production workloads requiring reliability and scalability

### Features:
- **Scheduled Jobs**: Built-in cron scheduling
- **Auto-scaling**: Scale to zero when not running
- **Managed infrastructure**: No server management
- **Container-based**: Uses your existing Docker setup

### Implementation:

```yaml
# azure-container-app.yaml
apiVersion: 2022-03-01
type: Microsoft.App/containerApps
properties:
  configuration:
    scheduledTrigger:
      cronExpression: "0 2 * * *"  # Daily at 2 AM
    secrets:
      - name: sharepoint-tenant-id
        value: "${SHAREPOINT_TENANT_ID}"
      - name: sharepoint-client-id  
        value: "${SHAREPOINT_CLIENT_ID}"
      - name: sharepoint-client-secret
        value: "${SHAREPOINT_CLIENT_SECRET}"
      - name: db-connection-string
        value: "${DATABASE_CONNECTION_STRING}"
  template:
    containers:
      - name: document-loader
        image: your-registry.azurecr.io/document-loader:latest
        command: 
          - "document-loader"
          - "multi-source"
          - "sync-kb"
          - "PremiumRMs-kb"
        env:
          - name: SHAREPOINT_TENANT_ID
            secretRef: sharepoint-tenant-id
          - name: SHAREPOINT_CLIENT_ID
            secretRef: sharepoint-client-id
          - name: SHAREPOINT_CLIENT_SECRET
            secretRef: sharepoint-client-secret
          - name: DOCUMENT_LOADER_DB_CONNECTION_STRING
            secretRef: db-connection-string
```

### Deployment Commands:
```bash
# Create resource group
az group create --name rg-document-loader --location eastus

# Create Container App Environment
az containerapp env create \
  --name document-loader-env \
  --resource-group rg-document-loader \
  --location eastus

# Deploy scheduled sync job
az containerapp job create \
  --name document-loader-sync \
  --resource-group rg-document-loader \
  --environment document-loader-env \
  --trigger-type Schedule \
  --cron-expression "0 2 * * *" \
  --image your-registry.azurecr.io/document-loader:latest \
  --command "document-loader multi-source sync-kb PremiumRMs-kb"
```

## 🔄 Option 2: Azure DevOps Pipelines

**Best for:** Teams already using Azure DevOps with CI/CD integration

### Features:
- **Scheduled triggers**: Cron-based scheduling
- **Pipeline integration**: Part of existing DevOps workflow
- **Approval gates**: Manual approval for production syncs
- **Artifact management**: Version control for configurations

### Implementation:

```yaml
# azure-pipelines.yml
trigger: none  # Only scheduled, not on commits

schedules:
- cron: "0 2 * * *"  # Daily at 2 AM UTC
  displayName: Daily SharePoint Sync
  branches:
    include:
    - main
  always: true

pool:
  vmImage: 'ubuntu-latest'

variables:
- group: document-loader-secrets  # Variable group with secrets
- name: containerRegistry
  value: 'your-registry.azurecr.io'

stages:
- stage: DeltaSync
  displayName: 'Execute Delta Sync'
  jobs:
  - job: SyncSharePoint
    displayName: 'Sync SharePoint Premium RMs'
    steps:
    
    - task: Docker@2
      displayName: 'Pull Document Loader Image'
      inputs:
        command: 'pull'
        arguments: '$(containerRegistry)/document-loader:latest'
    
    - task: Docker@2
      displayName: 'Run Delta Sync'
      inputs:
        command: 'run'
        arguments: |
          --rm \
          -e SHAREPOINT_TENANT_ID="$(SHAREPOINT_TENANT_ID)" \
          -e SHAREPOINT_CLIENT_ID="$(SHAREPOINT_CLIENT_ID)" \
          -e SHAREPOINT_CLIENT_SECRET="$(SHAREPOINT_CLIENT_SECRET)" \
          -e DOCUMENT_LOADER_DB_HOST="$(DB_HOST)" \
          -e DOCUMENT_LOADER_DB_NAME="$(DB_NAME)" \
          -e DOCUMENT_LOADER_DB_USER="$(DB_USER)" \
          -e DOCUMENT_LOADER_DB_PASSWORD="$(DB_PASSWORD)" \
          $(containerRegistry)/document-loader:latest \
          document-loader multi-source sync-kb PremiumRMs-kb
    
    - task: PublishTestResults@2
      displayName: 'Publish Sync Results'
      condition: always()
      inputs:
        testResultsFormat: 'JUnit'
        testResultsFiles: '**/sync-results.xml'
        failTaskOnFailedTests: true
```

### Setup Commands:
```bash
# Create variable group with secrets
az pipelines variable-group create \
  --name document-loader-secrets \
  --variables \
    SHAREPOINT_TENANT_ID="your-tenant-id" \
    SHAREPOINT_CLIENT_ID="your-client-id" \
    DB_HOST="your-db-host" \
    DB_NAME="premium_rms_document_loader"

# Create pipeline
az pipelines create \
  --name document-loader-scheduled-sync \
  --repository https://github.com/your-org/document-loader \
  --branch main \
  --yml-path azure-pipelines.yml
```

## ⚡ Option 3: Azure Functions (Serverless)

**Best for:** Event-driven architectures and cost optimization

### Features:
- **Timer trigger**: Cron-based scheduling
- **Serverless**: Pay only for execution time
- **Integration**: Easy integration with other Azure services
- **Monitoring**: Built-in Application Insights

### Implementation:

```python
# function_app.py
import azure.functions as func
import subprocess
import logging
import os
from datetime import datetime

app = func.FunctionApp()

@app.timer_trigger(schedule="0 2 * * *", arg_name="timer", run_on_startup=False)
def scheduled_sharepoint_sync(timer: func.TimerRequest) -> None:
    """
    Azure Function to execute scheduled SharePoint delta sync
    Runs daily at 2 AM UTC
    """
    
    logging.info('Starting scheduled SharePoint delta sync')
    
    # Set environment variables
    env_vars = {
        'SHAREPOINT_TENANT_ID': os.environ.get('SHAREPOINT_TENANT_ID'),
        'SHAREPOINT_CLIENT_ID': os.environ.get('SHAREPOINT_CLIENT_ID'), 
        'SHAREPOINT_CLIENT_SECRET': os.environ.get('SHAREPOINT_CLIENT_SECRET'),
        'DOCUMENT_LOADER_DB_HOST': os.environ.get('DOCUMENT_LOADER_DB_HOST'),
        'DOCUMENT_LOADER_DB_NAME': os.environ.get('DOCUMENT_LOADER_DB_NAME'),
        'DOCUMENT_LOADER_DB_USER': os.environ.get('DOCUMENT_LOADER_DB_USER'),
        'DOCUMENT_LOADER_DB_PASSWORD': os.environ.get('DOCUMENT_LOADER_DB_PASSWORD')
    }
    
    try:
        # Execute document loader sync
        result = subprocess.run([
            'document-loader', 
            'multi-source', 
            'sync-kb', 
            'PremiumRMs-kb'
        ], 
        env={**os.environ, **env_vars},
        capture_output=True, 
        text=True, 
        timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logging.info(f'Sync completed successfully: {result.stdout}')
        else:
            logging.error(f'Sync failed with return code {result.returncode}: {result.stderr}')
            
    except subprocess.TimeoutExpired:
        logging.error('Sync timed out after 1 hour')
    except Exception as e:
        logging.error(f'Sync failed with exception: {str(e)}')
    
    logging.info('Scheduled sync execution completed')
```

```json
// host.json
{
  "version": "2.0",
  "functionTimeout": "01:00:00",
  "extensions": {
    "durableTask": {
      "hubName": "DocumentLoaderHub"
    }
  },
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true
      }
    }
  }
}
```

### Deployment:
```bash
# Create Function App
az functionapp create \
  --resource-group rg-document-loader \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name document-loader-sync-func \
  --storage-account documentloaderstorage

# Deploy function
func azure functionapp publish document-loader-sync-func
```

## 🗂️ Option 4: Azure Container Instances (Simple)

**Best for:** Simple, lightweight scheduled tasks

### Features:
- **Container Groups**: Run containers on schedule
- **Cost-effective**: Pay per second
- **Simple setup**: Minimal configuration required

### Implementation:

```yaml
# aci-scheduled-sync.yaml
apiVersion: 2021-09-01
location: eastus
type: Microsoft.ContainerInstance/containerGroups
properties:
  containers:
  - name: document-loader-sync
    properties:
      image: your-registry.azurecr.io/document-loader:latest
      command:
        - document-loader
        - multi-source 
        - sync-kb
        - PremiumRMs-kb
      environmentVariables:
        - name: SHAREPOINT_TENANT_ID
          secureValue: "${SHAREPOINT_TENANT_ID}"
        - name: SHAREPOINT_CLIENT_ID
          secureValue: "${SHAREPOINT_CLIENT_ID}"
        - name: SHAREPOINT_CLIENT_SECRET
          secureValue: "${SHAREPOINT_CLIENT_SECRET}"
      resources:
        requests:
          cpu: 1
          memoryInGb: 2
  osType: Linux
  restartPolicy: Never
```

### Automation Script:
```bash
#!/bin/bash
# schedule-aci-sync.sh

# This script can be run from Azure Automation or Logic Apps

az container create \
  --resource-group rg-document-loader \
  --name document-loader-sync-$(date +%Y%m%d%H%M) \
  --image your-registry.azurecr.io/document-loader:latest \
  --restart-policy Never \
  --environment-variables \
    SHAREPOINT_TENANT_ID="$SHAREPOINT_TENANT_ID" \
    SHAREPOINT_CLIENT_ID="$SHAREPOINT_CLIENT_ID" \
    SHAREPOINT_CLIENT_SECRET="$SHAREPOINT_CLIENT_SECRET" \
  --command-line "document-loader multi-source sync-kb PremiumRMs-kb"
```

## 📊 Monitoring & Alerting

### Application Insights Integration:
```python
# monitoring.py
from applicationinsights import TelemetryClient
import logging

def setup_monitoring():
    # Application Insights integration
    tc = TelemetryClient(os.environ.get('APPINSIGHTS_INSTRUMENTATION_KEY'))
    
    # Custom telemetry for sync events
    tc.track_event('SharePointSyncStarted', {
        'knowledge_base': 'PremiumRMs-kb',
        'sync_type': 'delta',
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return tc

def track_sync_metrics(tc, files_processed, files_new, files_modified, duration):
    tc.track_metric('FilesProcessed', files_processed)
    tc.track_metric('FilesNew', files_new) 
    tc.track_metric('FilesModified', files_modified)
    tc.track_metric('SyncDurationSeconds', duration)
```

### Azure Monitor Alerts:
```json
{
  "type": "Microsoft.Insights/metricAlerts",
  "apiVersion": "2018-03-01",
  "name": "DocumentLoaderSyncFailure",
  "properties": {
    "description": "Alert when document loader sync fails",
    "severity": 2,
    "enabled": true,
    "scopes": [
      "/subscriptions/{subscription-id}/resourceGroups/rg-document-loader"
    ],
    "criteria": {
      "odata.type": "Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria",
      "allOf": [
        {
          "name": "SyncFailures",
          "metricName": "SyncFailures",
          "operator": "GreaterThan",
          "threshold": 0,
          "timeAggregation": "Total"
        }
      ]
    },
    "actions": [
      {
        "actionGroupId": "/subscriptions/{subscription-id}/resourceGroups/rg-document-loader/providers/Microsoft.Insights/actionGroups/EmailAlert"
      }
    ]
  }
}
```

## 🔒 Security Considerations

### Key Vault Integration:
```bash
# Store secrets in Azure Key Vault
az keyvault create \
  --name document-loader-kv \
  --resource-group rg-document-loader \
  --location eastus

# Add secrets
az keyvault secret set \
  --vault-name document-loader-kv \
  --name sharepoint-tenant-id \
  --value "your-tenant-id"

az keyvault secret set \
  --vault-name document-loader-kv \
  --name sharepoint-client-secret \
  --value "your-client-secret"
```

### Managed Identity:
```bash
# Assign managed identity to Container App
az containerapp identity assign \
  --name document-loader-sync \
  --resource-group rg-document-loader \
  --system-assigned

# Grant Key Vault access
az keyvault set-policy \
  --name document-loader-kv \
  --object-id $(az containerapp identity show --name document-loader-sync --resource-group rg-document-loader --query principalId -o tsv) \
  --secret-permissions get list
```

## 💰 Cost Comparison

| Option | Monthly Cost (Estimate) | Execution Time | Scaling |
|--------|------------------------|----------------|---------|
| Container Apps | $20-50 | 5-15 minutes | Auto |
| DevOps Pipelines | $10-30 | 5-15 minutes | Fixed |
| Azure Functions | $5-15 | 5-15 minutes | Auto |
| Container Instances | $15-35 | 5-15 minutes | Manual |

*Estimates based on daily execution, 10-minute runtime, East US region*

## 🎯 Recommendations

### For Production (NBG):
**Use Azure Container Apps** for:
- ✅ Enterprise-grade reliability
- ✅ Built-in monitoring and logging
- ✅ Auto-scaling capabilities
- ✅ Easy scheduling with cron expressions
- ✅ Integration with Azure services

### For Development/Testing:
**Use Azure DevOps Pipelines** for:
- ✅ Integration with existing CI/CD
- ✅ Manual approval workflows
- ✅ Version control integration
- ✅ Cost-effective for testing

### Next Steps:
1. Choose deployment option based on requirements
2. Set up Azure Key Vault for secrets management
3. Configure monitoring and alerting
4. Test with development environment
5. Deploy to production with proper governance