#!/bin/bash

# Budget-Friendly Azure Deployment Script
# Estimated cost: ~$25-50/month (vs $115-225/month for full solution)
#
# Cost savings achieved through:
# - Azure Container Instances (pay-per-second, vs always-on Container Apps)
# - Cosmos DB Free Tier or Azure SQL Basic (vs PostgreSQL Flexible Server)
# - Single container for backend+frontend (vs separate containers)
# - Azure Functions for scheduled job (vs Container Apps Job)

set -e

RESOURCE_GROUP="sam-govwin-budget-rg"
LOCATION="eastus"
ACR_NAME="samgovwinbudgetacr"
STORAGE_ACCOUNT="samgovwinstorage$(date +%s | tail -c 6)"
COSMOS_ACCOUNT="sam-govwin-cosmos"
FUNCTION_APP="sam-workflow-func"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Budget-Friendly Azure Deployment ===${NC}"
echo -e "${YELLOW}Estimated monthly cost: \$25-50${NC}"
echo ""

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    exit 1
fi

# Check login
az account show > /dev/null 2>&1 || {
    echo -e "${RED}Not logged in. Please run: az login${NC}"
    exit 1
}

# Create Resource Group
echo -e "${YELLOW}Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION --output table

# Create Storage Account (for Azure Functions and file storage)
echo -e "${YELLOW}Creating storage account...${NC}"
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2 \
    --output table

# Create Cosmos DB account (Free tier - first 1000 RU/s free)
echo -e "${YELLOW}Creating Cosmos DB account (Free tier)...${NC}"
az cosmosdb create \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --locations regionName=$LOCATION failoverPriority=0 \
    --enable-free-tier true \
    --default-consistency-level Session \
    --output table

# Create SQL API database
az cosmosdb sql database create \
    --account-name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --name sam_govwin \
    --output table

# Create containers (collections)
az cosmosdb sql container create \
    --account-name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --database-name sam_govwin \
    --name opportunities \
    --partition-key-path "/notice_id" \
    --throughput 400 \
    --output table

# Get Cosmos DB connection string
COSMOS_CONN=$(az cosmosdb keys list \
    --name $COSMOS_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --type connection-strings \
    --query "connectionStrings[0].connectionString" -o tsv)

# Create Container Registry (Basic tier - cheapest)
echo -e "${YELLOW}Creating Container Registry (Basic tier)...${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true \
    --output table

ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Build combined backend+frontend image
echo -e "${YELLOW}Building combined application image...${NC}"
cat > Dockerfile.combined <<EOF
# Combined backend + frontend container
FROM python:3.11-slim

WORKDIR /app

# Install nginx and system dependencies
RUN apt-get update && apt-get install -y \\
    nginx \\
    gcc \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY app/ ./app/
COPY run_end_to_end_workflow.py .

# Copy frontend build
COPY frontend/dist/ /usr/share/nginx/html/

# Copy nginx config
COPY nginx.conf /etc/nginx/sites-available/default

# Startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80

CMD ["/start.sh"]
EOF

# Create startup script
cat > start.sh <<'EOF'
#!/bin/bash
# Start nginx in background
nginx

# Start backend
cd /app
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
EOF

az acr build \
    --registry $ACR_NAME \
    --image sam-combined:latest \
    --file Dockerfile.combined \
    .

echo -e "${GREEN}✓ Images built${NC}"

# Get API keys
echo -e "${YELLOW}Please provide API keys:${NC}"
echo -n "SAM_API_KEY: "
read SAM_API_KEY
echo -n "GOVWIN_API_KEY: "
read GOVWIN_API_KEY
echo -n "OPENAI_API_KEY: "
read OPENAI_API_KEY

# Deploy Container Instance (pay-per-second billing)
echo -e "${YELLOW}Deploying application container...${NC}"
az container create \
    --resource-group $RESOURCE_GROUP \
    --name sam-app \
    --image "${ACR_LOGIN_SERVER}/sam-combined:latest" \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password "$ACR_PASSWORD" \
    --dns-name-label "sam-govwin-app-$(date +%s | tail -c 6)" \
    --ports 80 \
    --cpu 1 \
    --memory 2 \
    --environment-variables \
        DATABASE_URL="$COSMOS_CONN" \
        SAM_API_KEY="$SAM_API_KEY" \
        GOVWIN_API_KEY="$GOVWIN_API_KEY" \
        OPENAI_API_KEY="$OPENAI_API_KEY" \
    --output table

APP_FQDN=$(az container show \
    --resource-group $RESOURCE_GROUP \
    --name sam-app \
    --query ipAddress.fqdn -o tsv)

# Create Azure Function for scheduled workflow
echo -e "${YELLOW}Creating Azure Function for nightly job...${NC}"
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP \
    --storage-account $STORAGE_ACCOUNT \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version 3.11 \
    --functions-version 4 \
    --os-type Linux \
    --output table

# Configure Function App settings
az functionapp config appsettings set \
    --name $FUNCTION_APP \
    --resource-group $RESOURCE_GROUP \
    --settings \
        DATABASE_URL="$COSMOS_CONN" \
        SAM_API_KEY="$SAM_API_KEY" \
        GOVWIN_API_KEY="$GOVWIN_API_KEY" \
        OPENAI_API_KEY="$OPENAI_API_KEY" \
    --output table

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Budget Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Application URL: http://${APP_FQDN}"
echo "Function App: $FUNCTION_APP"
echo ""
echo -e "${YELLOW}Estimated Monthly Costs:${NC}"
echo "  Container Instance: ~\$10-15 (1 vCPU, 2GB RAM, ~50% uptime)"
echo "  Cosmos DB: \$0 (Free tier, 1000 RU/s included)"
echo "  Azure Functions: ~\$5-10 (Consumption plan, ~1-2 hours/day)"
echo "  Container Registry: ~\$5 (Basic tier)"
echo "  Storage Account: ~\$2-5 (minimal usage)"
echo "  ------------------------"
echo "  Total: ~\$25-50/month"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Deploy the Azure Function code for nightly workflow"
echo "2. Configure the timer trigger (see AZURE_DEPLOYMENT_BUDGET.md)"
echo ""
