#!/bin/bash

# Azure Update Script for SAM.gov & GovWin Application
# This script rebuilds and redeploys containers to Azure

set -e

# Configuration Variables (must match deploy_azure.sh)
RESOURCE_GROUP="sam-govwin-rg"
ACR_NAME="samgovwinacr"
BACKEND_APP="sam-backend"
FRONTEND_APP="sam-frontend"
WORKFLOW_JOB="sam-workflow-job"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Updating SAM.gov & GovWin Application ===${NC}"
echo ""

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Build and push new images
echo -e "${YELLOW}Building and pushing updated Docker images...${NC}"

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

echo -e "${GREEN}✓ Docker images rebuilt${NC}"
echo ""

# Update backend
echo -e "${YELLOW}Updating backend container app...${NC}"
az containerapp update \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --image "${ACR_LOGIN_SERVER}/sam-backend:latest" \
    --output table

echo -e "${GREEN}✓ Backend updated${NC}"
echo ""

# Update frontend
echo -e "${YELLOW}Updating frontend container app...${NC}"
az containerapp update \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --image "${ACR_LOGIN_SERVER}/sam-frontend:latest" \
    --output table

echo -e "${GREEN}✓ Frontend updated${NC}"
echo ""

# Update workflow job
echo -e "${YELLOW}Updating workflow job...${NC}"
az containerapp job update \
    --name $WORKFLOW_JOB \
    --resource-group $RESOURCE_GROUP \
    --image "${ACR_LOGIN_SERVER}/sam-workflow:latest" \
    --output table

echo -e "${GREEN}✓ Workflow job updated${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Update Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "All services have been updated with the latest code."
echo ""
