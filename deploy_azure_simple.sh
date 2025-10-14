#!/bin/bash

# Simple Azure Budget Deployment
# Cost: ~$30-60/month
# Deploys: App Service + Azure SQL + Azure Function for nightly job

set -e

RESOURCE_GROUP="sam-govwin-rg"
LOCATION="westus2"
APP_SERVICE_PLAN="sam-app-plan"
WEB_APP="sam-govwin-app-$(date +%s | tail -c 6)"
SQL_SERVER="sam-sql-$(date +%s | tail -c 6)"
SQL_DB="sam_govwin"
FUNCTION_APP="sam-workflow-func-$(date +%s | tail -c 6)"
STORAGE_ACCOUNT="samstore$(date +%s | tail -c 8)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Simple Azure Budget Deployment ===${NC}"
echo -e "${YELLOW}Cost: ~\$30-60/month${NC}"
echo ""

# Check prerequisites
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not installed${NC}"
    exit 1
fi

az account show > /dev/null 2>&1 || {
    echo -e "${RED}Not logged in. Run: az login${NC}"
    exit 1
}

# Get configuration
echo -e "${YELLOW}Configuration${NC}"
echo -n "Enter SAM.gov API Key: "
read -s SAM_API_KEY
echo ""
echo -n "Enter GovWin Client ID: "
read -s GOVWIN_CLIENT_ID
echo ""
echo -n "Enter GovWin Client Secret: "
read -s GOVWIN_CLIENT_SECRET
echo ""
echo -n "Enter GovWin Username: "
read -s GOVWIN_USERNAME
echo ""
echo -n "Enter GovWin Password: "
read -s GOVWIN_PASSWORD
echo ""
echo -n "Enter OpenAI API Key: "
read -s OPENAI_API_KEY
echo ""
echo -n "Enter SQL Server Admin Password (8+ chars, uppercase, lowercase, number, special char): "
read -s SQL_PASSWORD
echo ""
echo ""

# Create resource group
echo -e "${YELLOW}Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION --output table

# Create SQL Server
echo -e "${YELLOW}Creating SQL Server...${NC}"
az sql server create \
    --name $SQL_SERVER \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --admin-user samadmin \
    --admin-password "$SQL_PASSWORD" \
    --output table

# Configure SQL Server firewall (allow Azure services and all IPs)
echo -e "${YELLOW}Configuring SQL Server firewall...${NC}"
az sql server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --server $SQL_SERVER \
    --name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    --output table

# Allow all IP addresses (for development/testing - consider restricting in production)
echo -e "${YELLOW}Allowing all IP addresses for database access${NC}"
az sql server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --server $SQL_SERVER \
    --name AllowAllIPs \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 255.255.255.255 \
    --output table

# Create SQL Database
echo -e "${YELLOW}Creating SQL Database...${NC}"
az sql db create \
    --resource-group $RESOURCE_GROUP \
    --server $SQL_SERVER \
    --name $SQL_DB \
    --service-objective Basic \
    --backup-storage-redundancy Local \
    --output table

# Create App Service Plan
echo -e "${YELLOW}Creating App Service Plan...${NC}"
az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku B1 \
    --is-linux \
    --output table

# Create Web App
echo -e "${YELLOW}Creating Web App...${NC}"
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --name $WEB_APP \
    --runtime "PYTHON:3.11" \
    --output table

# Wait for Web App to be fully provisioned
echo -e "${YELLOW}Waiting for Web App to be ready...${NC}"
sleep 10

# Build database connection string
DB_CONNECTION="mssql+pyodbc://samadmin:${SQL_PASSWORD}@${SQL_SERVER}.database.windows.net:1433/${SQL_DB}?driver=ODBC+Driver+18+for+SQL+Server"

# Configure Web App settings
echo -e "${YELLOW}Configuring Web App...${NC}"
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $WEB_APP \
    --settings \
        DATABASE_URL="$DB_CONNECTION" \
        SAM_API_KEY="$SAM_API_KEY" \
        GOVWIN_CLIENT_ID="$GOVWIN_CLIENT_ID" \
        GOVWIN_CLIENT_SECRET="$GOVWIN_CLIENT_SECRET" \
        GOVWIN_USERNAME="$GOVWIN_USERNAME" \
        GOVWIN_PASSWORD="$GOVWIN_PASSWORD" \
        OPENAI_API_KEY="$OPENAI_API_KEY" \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    --output table

# Create Storage Account for Azure Functions
echo -e "${YELLOW}Creating Storage Account...${NC}"
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --output table

# Create Function App for nightly workflow
echo -e "${YELLOW}Creating Function App for nightly workflow...${NC}"
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
        DATABASE_URL="$DB_CONNECTION" \
        SAM_API_KEY="$SAM_API_KEY" \
        GOVWIN_CLIENT_ID="$GOVWIN_CLIENT_ID" \
        GOVWIN_CLIENT_SECRET="$GOVWIN_CLIENT_SECRET" \
        GOVWIN_USERNAME="$GOVWIN_USERNAME" \
        GOVWIN_PASSWORD="$GOVWIN_PASSWORD" \
        OPENAI_API_KEY="$OPENAI_API_KEY" \
    --output table

# Get URLs
WEB_APP_URL=$(az webapp show --resource-group $RESOURCE_GROUP --name $WEB_APP --query defaultHostName -o tsv)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Application URL:${NC} https://${WEB_APP_URL}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Deploy your application code to Azure:"
echo "   See QUICK_START_AZURE.md for instructions"
echo ""
echo "2. Deploy the Azure Function for nightly job:"
echo "   See QUICK_START_AZURE.md for instructions"
echo ""
echo "3. Test the application:"
echo "   Open: https://${WEB_APP_URL}/health"
echo "   Open: https://${WEB_APP_URL}"
echo ""
echo -e "${YELLOW}Credentials saved to: azure_deployment_info.txt${NC}"
echo ""

# Save deployment info
cat > azure_deployment_info.txt <<EOF
Azure Deployment Information
============================
Created: $(date)

Resource Group: $RESOURCE_GROUP
Location: $LOCATION

Web App: $WEB_APP
URL: https://${WEB_APP_URL}

SQL Server: ${SQL_SERVER}.database.windows.net
Database: $SQL_DB
Admin User: samadmin

Function App: $FUNCTION_APP

To clean up:
az group delete --name $RESOURCE_GROUP --yes
EOF

echo -e "${GREEN}Deployment info saved to azure_deployment_info.txt${NC}"
