# Azure Deployment Guide

This guide provides step-by-step instructions for deploying the SAM.gov & GovWin opportunity management system to Microsoft Azure.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Initial Deployment](#initial-deployment)
4. [Updating the Application](#updating-the-application)
5. [Managing the Nightly Workflow](#managing-the-nightly-workflow)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
7. [Cost Optimization](#cost-optimization)
8. [Security Best Practices](#security-best-practices)

## Architecture Overview

The application is deployed using the following Azure services:

- **Azure Container Registry (ACR)**: Stores Docker images for backend, frontend, and workflow
- **Azure Container Apps**: Hosts the backend API and frontend web application
- **Azure Database for PostgreSQL**: Managed database service
- **Azure Container Apps Jobs**: Scheduled nightly workflow execution

```
┌─────────────────────────────────────────────────────────────┐
│                       Azure Cloud                            │
│                                                               │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │   Frontend      │◄────────┤  Azure Container │          │
│  │  Container App  │         │   Apps Environment│          │
│  └────────┬────────┘         └──────────────────┘          │
│           │                            ▲                     │
│           │                            │                     │
│           ▼                            │                     │
│  ┌─────────────────┐                  │                     │
│  │    Backend      │                  │                     │
│  │  Container App  │──────────────────┘                     │
│  └────────┬────────┘                                        │
│           │                                                  │
│           │                   ┌──────────────────┐          │
│           ├───────────────────►  PostgreSQL      │          │
│           │                   │   Database       │          │
│           │                   └──────────────────┘          │
│           │                                                  │
│  ┌────────▼────────┐                                        │
│  │  Workflow Job   │                                        │
│  │  (Nightly Run)  │                                        │
│  └─────────────────┘                                        │
│                                                               │
│  ┌─────────────────┐                                        │
│  │ Container       │                                        │
│  │  Registry (ACR) │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required Tools

1. **Azure CLI** (version 2.50+)
   ```bash
   # Install Azure CLI
   # macOS:
   brew install azure-cli

   # Windows:
   # Download from https://aka.ms/installazurecliwindows

   # Linux:
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   ```

2. **Docker** (for local testing)
   ```bash
   # Verify Docker installation
   docker --version
   ```

3. **Git**
   ```bash
   git --version
   ```

### Required API Keys

Prepare the following API keys before deployment:

- **SAM.gov API Key**: Get from [SAM.gov API Console](https://open.gsa.gov/api/get-opportunities-public-api/)
- **GovWin API Key**: Get from your GovWin IQ subscription
- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Microsoft Dynamics 365 CRM credentials** (if using CRM integration)

### Azure Subscription

- Active Azure subscription with sufficient permissions to create resources
- Recommended: Owner or Contributor role on the subscription

## Initial Deployment

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd AI-SAM-Research
```

### Step 2: Log in to Azure

```bash
az login
```

This will open a browser window for authentication.

### Step 3: Set Your Subscription (if you have multiple)

```bash
# List available subscriptions
az account list --output table

# Set the desired subscription
az account set --subscription "<subscription-id-or-name>"
```

### Step 4: Run the Deployment Script

```bash
./deploy_azure.sh
```

The script will:
1. Create a resource group
2. Set up Azure Container Registry
3. Build and push Docker images
4. Create PostgreSQL database
5. Deploy backend and frontend Container Apps
6. Create the nightly workflow job

### Step 5: Provide Configuration During Deployment

The script will prompt you for:
- PostgreSQL admin password (choose a strong password)
- SAM_API_KEY
- GOVWIN_API_KEY
- OPENAI_API_KEY

**Important**: Save these credentials securely. You'll need them for updates and troubleshooting.

### Step 6: Verify Deployment

Once deployment completes, the script will display:
- Frontend URL
- Backend URL
- Database connection string

Test the deployment:

```bash
# Check backend health
curl https://<backend-url>/health

# Visit frontend in browser
open https://<frontend-url>
```

## Updating the Application

### Update Code and Redeploy

After making changes to your code:

```bash
# Rebuild and redeploy all containers
./update_azure.sh
```

This script will:
1. Build new Docker images with your latest code
2. Push images to Azure Container Registry
3. Update all Container Apps with new images
4. Restart services automatically

### Update Individual Components

To update only specific components:

```bash
# Update backend only
az containerapp update \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --image samgovwinacr.azurecr.io/sam-backend:latest

# Update frontend only
az containerapp update \
    --name sam-frontend \
    --resource-group sam-govwin-rg \
    --image samgovwinacr.azurecr.io/sam-frontend:latest

# Update workflow job
az containerapp job update \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg \
    --image samgovwinacr.azurecr.io/sam-workflow:latest
```

### Update Environment Variables

```bash
# Update backend environment variables
az containerapp update \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --set-env-vars \
        SAM_API_KEY="<new-key>" \
        GOVWIN_API_KEY="<new-key>"
```

## Managing the Nightly Workflow

### Default Schedule

The workflow job runs nightly at **2:00 AM UTC** (equivalent to 9:00 PM EST / 6:00 PM PST).

### View Job Executions

```bash
# List recent job executions
az containerapp job execution list \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg \
    --output table
```

### View Job Logs

```bash
# Get logs from latest execution
az containerapp job logs show \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg
```

### Manually Trigger the Job

```bash
# Run the job immediately (without waiting for schedule)
az containerapp job start \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg
```

### Update Schedule

To change the nightly schedule:

```bash
# Update cron expression
# Format: "minute hour day month day-of-week"
# Example: "0 3 * * *" = 3:00 AM UTC

az containerapp job update \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg \
    --cron-expression "0 3 * * *"
```

Common schedules:
- `0 2 * * *` - 2:00 AM UTC daily
- `0 */6 * * *` - Every 6 hours
- `0 2 * * 1-5` - 2:00 AM UTC Monday-Friday only

### Disable Nightly Job

```bash
# Stop the scheduled job
az containerapp job stop \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg
```

### Re-enable Nightly Job

```bash
# Restart the scheduled job
az containerapp job start \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg
```

## Monitoring and Troubleshooting

### View Application Logs

```bash
# Backend logs
az containerapp logs show \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --follow

# Frontend logs
az containerapp logs show \
    --name sam-frontend \
    --resource-group sam-govwin-rg \
    --follow
```

### Check Application Status

```bash
# Backend status
az containerapp show \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --query "properties.runningStatus"

# Frontend status
az containerapp show \
    --name sam-frontend \
    --resource-group sam-govwin-rg \
    --query "properties.runningStatus"
```

### View Metrics

```bash
# CPU and memory usage
az monitor metrics list \
    --resource <resource-id> \
    --metric "CpuPercentage" "MemoryPercentage" \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z
```

### Common Issues

#### Issue: Backend can't connect to database

**Solution**: Check firewall rules and connection string

```bash
# Verify PostgreSQL firewall rules
az postgres flexible-server firewall-rule list \
    --resource-group sam-govwin-rg \
    --server-name sam-govwin-db

# Test database connection
psql "postgresql://samadmin:<password>@sam-govwin-db.postgres.database.azure.com:5432/sam_govwin?sslmode=require"
```

#### Issue: Frontend can't reach backend

**Solution**: Verify CORS settings and backend URL

```bash
# Check backend ingress
az containerapp show \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --query "properties.configuration.ingress"
```

#### Issue: Workflow job fails

**Solution**: Check job logs and environment variables

```bash
# View failed execution logs
az containerapp job execution list \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg \
    --output table

# Get specific execution logs
az containerapp job logs show \
    --name sam-workflow-job \
    --resource-group sam-govwin-rg \
    --execution <execution-name>
```

## Cost Optimization

### Estimated Monthly Costs

- **Container Apps (Backend)**: ~$50-100/month (1 vCPU, 2GB RAM, always running)
- **Container Apps (Frontend)**: ~$25-50/month (0.5 vCPU, 1GB RAM, always running)
- **PostgreSQL Database**: ~$30-60/month (Burstable B1ms tier, 32GB storage)
- **Container Registry**: ~$5/month (Standard tier)
- **Container Apps Jobs**: ~$5-10/month (runs for ~1-2 hours/day)

**Total: ~$115-225/month**

### Cost Reduction Tips

1. **Scale Down Non-Production Environments**
   ```bash
   # Reduce replicas to 0 during non-business hours
   az containerapp update \
       --name sam-backend \
       --resource-group sam-govwin-rg \
       --min-replicas 0 \
       --max-replicas 1
   ```

2. **Use Consumption-Based Pricing**
   - Container Apps automatically scale to zero when not in use
   - You only pay for actual compute time

3. **Optimize Database Tier**
   ```bash
   # Scale down database during development
   az postgres flexible-server update \
       --resource-group sam-govwin-rg \
       --name sam-govwin-db \
       --tier Burstable \
       --sku-name Standard_B1ms
   ```

4. **Delete Test/Dev Resources When Not Needed**
   ```bash
   # Delete entire resource group
   az group delete --name sam-govwin-rg-dev
   ```

## Security Best Practices

### 1. Use Azure Key Vault for Secrets

Store sensitive configuration in Azure Key Vault instead of environment variables:

```bash
# Create Key Vault
az keyvault create \
    --name sam-govwin-kv \
    --resource-group sam-govwin-rg \
    --location eastus

# Add secrets
az keyvault secret set \
    --vault-name sam-govwin-kv \
    --name SAM-API-KEY \
    --value "<your-api-key>"

# Grant Container App access to Key Vault
az containerapp identity assign \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --system-assigned
```

### 2. Enable HTTPS Only

Ensure all ingress is HTTPS-only:

```bash
az containerapp ingress update \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --allow-insecure false
```

### 3. Configure Database Firewall

Restrict database access to Container Apps only:

```bash
# Remove public access
az postgres flexible-server firewall-rule delete \
    --resource-group sam-govwin-rg \
    --server-name sam-govwin-db \
    --name AllowAll

# Add Container Apps subnet
az postgres flexible-server firewall-rule create \
    --resource-group sam-govwin-rg \
    --server-name sam-govwin-db \
    --name AllowContainerApps \
    --start-ip-address <container-app-outbound-ip> \
    --end-ip-address <container-app-outbound-ip>
```

### 4. Enable Diagnostic Logging

```bash
# Enable logging to Log Analytics
az containerapp logs enable \
    --name sam-backend \
    --resource-group sam-govwin-rg \
    --workspace <log-analytics-workspace-id>
```

### 5. Regular Security Updates

```bash
# Check for base image updates weekly
./update_azure.sh
```

## Cleanup

To completely remove all Azure resources:

```bash
# Delete the entire resource group
az group delete --name sam-govwin-rg --yes --no-wait
```

**Warning**: This will permanently delete all data, including the database.

## Support

For issues or questions:
1. Check logs using the monitoring commands above
2. Review the [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Consult [Azure Container Apps documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
4. Open an issue in the project repository

## Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/)
- [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure Cost Management](https://learn.microsoft.com/en-us/azure/cost-management-billing/)
