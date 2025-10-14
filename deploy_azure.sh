#!/bin/bash

# Azure Deployment Script for SAM.gov & GovWin Application
# This script deploys the application to Azure Container Apps

set -e

# Configuration Variables
RESOURCE_GROUP="sam-govwin-rg"
LOCATION="eastus"
ACR_NAME="samgovwinacr"
CONTAINER_ENV="sam-govwin-env"
POSTGRES_SERVER="sam-govwin-db"
POSTGRES_DB="sam_govwin"
BACKEND_APP="sam-backend"
FRONTEND_APP="sam-frontend"
WORKFLOW_JOB="sam-workflow-job"

# Color codes for output
RED='\033[0:31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== SAM.gov & GovWin Azure Deployment ===${NC}"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
echo -e "${YELLOW}Checking Azure login status...${NC}"
az account show > /dev/null 2>&1 || {
    echo -e "${RED}Not logged in to Azure. Please run: az login${NC}"
    exit 1
}

echo -e "${GREEN}✓ Azure login verified${NC}"
echo ""

# Create Resource Group
echo -e "${YELLOW}Creating resource group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output table

echo -e "${GREEN}✓ Resource group created${NC}"
echo ""

# Create Azure Container Registry
echo -e "${YELLOW}Creating Azure Container Registry...${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Standard \
    --admin-enabled true \
    --output table

echo -e "${GREEN}✓ Container Registry created${NC}"
echo ""

# Get ACR credentials
echo -e "${YELLOW}Retrieving ACR credentials...${NC}"
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

echo -e "${GREEN}✓ ACR credentials retrieved${NC}"
echo ""

# Build and push Docker images
echo -e "${YELLOW}Building and pushing Docker images...${NC}"

echo "Building backend image..."
az acr build \
    --registry $ACR_NAME \
    --image sam-backend:latest \
    --file Dockerfile.backend \
    .

echo "Building frontend image..."
az acr build \
    --registry $ACR_NAME \
    --image sam-frontend:latest \
    --file Dockerfile.frontend \
    .

echo "Building workflow image..."
az acr build \
    --registry $ACR_NAME \
    --image sam-workflow:latest \
    --file Dockerfile.workflow \
    .

echo -e "${GREEN}✓ Docker images built and pushed${NC}"
echo ""

# Create PostgreSQL Database
echo -e "${YELLOW}Creating PostgreSQL database...${NC}"
echo "Please enter a secure admin password for PostgreSQL:"
read -s POSTGRES_ADMIN_PASSWORD

az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_SERVER \
    --location $LOCATION \
    --admin-user samadmin \
    --admin-password "$POSTGRES_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --version 14 \
    --storage-size 32 \
    --public-access 0.0.0.0-255.255.255.255 \
    --output table

# Create database
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $POSTGRES_SERVER \
    --database-name $POSTGRES_DB \
    --output table

echo -e "${GREEN}✓ PostgreSQL database created${NC}"
echo ""

# Create Container Apps Environment
echo -e "${YELLOW}Creating Container Apps environment...${NC}"
az containerapp env create \
    --name $CONTAINER_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --output table

echo -e "${GREEN}✓ Container Apps environment created${NC}"
echo ""

# Construct database URL
DB_HOST="${POSTGRES_SERVER}.postgres.database.azure.com"
DATABASE_URL="postgresql://samadmin:${POSTGRES_ADMIN_PASSWORD}@${DB_HOST}:5432/${POSTGRES_DB}?sslmode=require"

# Deploy Backend Container App
echo -e "${YELLOW}Deploying backend container app...${NC}"
echo "Please provide the following environment variables:"
echo -n "SAM_API_KEY: "
read SAM_API_KEY
echo -n "GOVWIN_API_KEY: "
read GOVWIN_API_KEY
echo -n "OPENAI_API_KEY: "
read OPENAI_API_KEY

az containerapp create \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_ENV \
    --image "${ACR_LOGIN_SERVER}/sam-backend:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password "$ACR_PASSWORD" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 1.0 \
    --memory 2.0Gi \
    --env-vars \
        DATABASE_URL="$DATABASE_URL" \
        SAM_API_KEY="$SAM_API_KEY" \
        GOVWIN_API_KEY="$GOVWIN_API_KEY" \
        OPENAI_API_KEY="$OPENAI_API_KEY" \
    --output table

BACKEND_URL=$(az containerapp show \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

echo -e "${GREEN}✓ Backend deployed at: https://${BACKEND_URL}${NC}"
echo ""

# Deploy Frontend Container App
echo -e "${YELLOW}Deploying frontend container app...${NC}"
az containerapp create \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_ENV \
    --image "${ACR_LOGIN_SERVER}/sam-frontend:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password "$ACR_PASSWORD" \
    --target-port 80 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 2 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --env-vars \
        VITE_API_BASE_URL="https://${BACKEND_URL}/api" \
    --output table

FRONTEND_URL=$(az containerapp show \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

echo -e "${GREEN}✓ Frontend deployed at: https://${FRONTEND_URL}${NC}"
echo ""

# Create scheduled workflow job (nightly)
echo -e "${YELLOW}Creating nightly workflow job...${NC}"
az containerapp job create \
    --name $WORKFLOW_JOB \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_ENV \
    --trigger-type Schedule \
    --replica-timeout 7200 \
    --replica-retry-limit 1 \
    --replica-completion-count 1 \
    --parallelism 1 \
    --image "${ACR_LOGIN_SERVER}/sam-workflow:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password "$ACR_PASSWORD" \
    --cpu 1.0 \
    --memory 2.0Gi \
    --cron-expression "0 2 * * *" \
    --env-vars \
        DATABASE_URL="$DATABASE_URL" \
        SAM_API_KEY="$SAM_API_KEY" \
        GOVWIN_API_KEY="$GOVWIN_API_KEY" \
        OPENAI_API_KEY="$OPENAI_API_KEY" \
    --output table

echo -e "${GREEN}✓ Nightly workflow job created (runs at 2 AM UTC)${NC}"
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Frontend URL: https://${FRONTEND_URL}"
echo "Backend URL: https://${BACKEND_URL}"
echo "Database: ${DB_HOST}"
echo ""
echo "Nightly Job: ${WORKFLOW_JOB} (runs at 2 AM UTC)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Navigate to the frontend URL to access the application"
echo "2. Verify the backend health endpoint: https://${BACKEND_URL}/health"
echo "3. Check workflow job execution: az containerapp job execution list --name $WORKFLOW_JOB --resource-group $RESOURCE_GROUP"
echo ""
echo -e "${YELLOW}To update the application:${NC}"
echo "Run ./update_azure.sh to rebuild and redeploy containers"
echo ""
