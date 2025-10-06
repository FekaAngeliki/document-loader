#!/bin/bash

# Deployment script for Document Loader to Azure
set -e

# Configuration
ENVIRONMENT="${1:-dev}"
RESOURCE_GROUP="rg-docloader-${ENVIRONMENT}"
LOCATION="${2:-eastus}"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"

echo "Deploying Document Loader to Azure..."
echo "Environment: ${ENVIRONMENT}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Location: ${LOCATION}"

# Check if Azure CLI is installed and logged in
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged into Azure
if ! az account show &> /dev/null; then
    echo "Please log in to Azure CLI first: az login"
    exit 1
fi

# Set subscription if provided
if [ -n "$SUBSCRIPTION_ID" ]; then
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# Create resource group if it doesn't exist
echo "Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Generate a secure password for PostgreSQL
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Deploy infrastructure using Bicep
echo "Deploying infrastructure..."
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file deployment/infrastructure.bicep \
    --parameters environmentName="$ENVIRONMENT" \
                location="$LOCATION" \
                postgresAdminPassword="$POSTGRES_PASSWORD" \
    --query 'properties.outputs' \
    --output json)

# Extract outputs
CONTAINER_REGISTRY=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.containerRegistryLoginServer.value')
POSTGRES_FQDN=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.postgresServerFqdn.value')
STORAGE_ACCOUNT=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.storageAccountName.value')
KEY_VAULT=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.keyVaultName.value')

echo "Infrastructure deployed successfully!"
echo "Container Registry: $CONTAINER_REGISTRY"
echo "PostgreSQL Server: $POSTGRES_FQDN"
echo "Storage Account: $STORAGE_ACCOUNT"
echo "Key Vault: $KEY_VAULT"

# Store secrets in Key Vault
echo "Storing secrets in Key Vault..."
az keyvault secret set --vault-name "$KEY_VAULT" --name "DB-HOST" --value "$POSTGRES_FQDN"
az keyvault secret set --vault-name "$KEY_VAULT" --name "DB-PORT" --value "5432"
az keyvault secret set --vault-name "$KEY_VAULT" --name "DB-NAME" --value "document_loader"
az keyvault secret set --vault-name "$KEY_VAULT" --name "DB-USER" --value "dbadmin"
az keyvault secret set --vault-name "$KEY_VAULT" --name "DB-PASSWORD" --value "$POSTGRES_PASSWORD"

# Build and push Docker image
echo "Building and pushing Docker image..."
az acr login --name "${CONTAINER_REGISTRY%.*}"
docker build -t "$CONTAINER_REGISTRY/document-loader:latest" .
docker push "$CONTAINER_REGISTRY/document-loader:latest"

echo "Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Set up Azure DevOps pipeline using azure-pipelines.yml"
echo "2. Configure pipeline variables with the following values:"
echo "   - dockerRegistryServiceConnection: Connection to $CONTAINER_REGISTRY"
echo "   - containerRegistry: $CONTAINER_REGISTRY"
echo "3. Set up environment approvals in Azure DevOps for production deployments"
echo "4. Run database initialization: az containerapp exec --name docloader-${ENVIRONMENT}-app --resource-group $RESOURCE_GROUP --command 'document-loader init-db'"