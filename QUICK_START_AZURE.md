# Quick Start: Azure Budget Deployment

This guide walks you through deploying your SAM.gov & GovWin application to Azure for **~$30-60/month** with a nightly workflow job.

## 🎯 What You'll Get

✅ **Web Application** - Accessible from your browser at a public URL
✅ **Backend API** - FastAPI serving your data
✅ **Database** - Azure SQL Database for storing opportunities
✅ **Nightly Job** - Automatically runs workflow at 2 AM UTC
✅ **Total Cost** - ~$30-60/month

---

## 📋 Prerequisites

### 1. Install Azure CLI

```bash
# macOS
brew install azure-cli

# Windows (run in PowerShell as Administrator)
# Download from: https://aka.ms/installazurecliwindows

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installation
az --version
```

### 2. Have Your API Keys Ready

- **SAM.gov API Key**: [Get it here](https://open.gsa.gov/api/get-opportunities-public-api/)
- **GovWin API Key**: From your GovWin subscription
- **OpenAI API Key**: [Get it here](https://platform.openai.com/api-keys)

### 3. Azure Subscription

- Free trial: [https://azure.microsoft.com/free](https://azure.microsoft.com/free)
- Or use existing subscription

---

## 🚀 Deployment Steps

### Step 1: Log into Azure

```bash
az login
```

This opens your browser for authentication. If you have multiple subscriptions:

```bash
# List subscriptions
az account list --output table

# Set the one you want to use
az account set --subscription "Your-Subscription-Name"
```

### Step 2: Build the Frontend

The frontend needs to be built before deployment:

```bash
cd frontend
npm install
npm run build
cd ..
```

### Step 3: Run the Deployment Script

```bash
chmod +x deploy_azure_simple.sh
./deploy_azure_simple.sh
```

**The script will prompt you for:**
1. SAM.gov API Key
2. GovWin API Key
3. OpenAI API Key
4. SQL Server Password (must be complex: 8+ chars, uppercase, lowercase, number, special char)

Example password: `MyP@ssw0rd2024!`

**Deployment takes 5-10 minutes** and creates:
- Resource Group
- SQL Server + Database
- App Service Plan + Web App
- Storage Account
- Azure Function App

### Step 4: Note Your Application URL

At the end, you'll see:

```
Application URL: https://sam-govwin-app-XXXXXX.azurewebsites.net
```

**Save this URL!** You'll use it to access your application.

---

## 📦 Deploy Your Code

After infrastructure is created, deploy your application code:

### Option A: Using Azure CLI (Recommended)

```bash
# Install pyodbc for Azure SQL
pip install pyodbc

# Create deployment package
cd /Users/bob.emerick/dev/AI-projects/AI-SAM-Research

# Create a startup script
cat > startup.sh <<'EOF'
#!/bin/bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyodbc

# Run database initialization
python -c "
from backend.app.database import Base, engine
print('Creating database tables...')
Base.metadata.create_all(bind=engine)
print('Database initialized!')
"

# Start the application
gunicorn --bind=0.0.0.0:8000 --workers=1 --timeout=600 backend.app.main:app
EOF

chmod +x startup.sh

# Deploy code (replace <your-app-name> with your Web App name from Step 3)
export WEB_APP_NAME="sam-govwin-app-XXXXXX"  # Replace with your actual name

# Create zip for deployment
zip -r deploy.zip . -x "*.git*" -x "*node_modules*" -x "frontend/*" -x "*.pyc" -x "__pycache__/*"

# Deploy to Azure
az webapp deployment source config-zip \
    --resource-group sam-govwin-rg \
    --name $WEB_APP_NAME \
    --src deploy.zip

# Configure startup command
az webapp config set \
    --resource-group sam-govwin-rg \
    --name $WEB_APP_NAME \
    --startup-file "startup.sh"
```

### Option B: Using Git Deploy (Alternative)

```bash
# Get Git credentials
az webapp deployment user set \
    --user-name <choose-username> \
    --password <choose-password>

# Get Git URL
GIT_URL=$(az webapp deployment source config-local-git \
    --name $WEB_APP_NAME \
    --resource-group sam-govwin-rg \
    --query url -o tsv)

# Add remote and push
git remote add azure $GIT_URL
git add .
git commit -m "Deploy to Azure"
git push azure main
```

---

## 🔧 Deploy Nightly Workflow Function

Create an Azure Function for the nightly job:

```bash
# Create function directory
mkdir -p azure_function
cd azure_function

# Create function configuration
cat > host.json <<'EOF'
{
  "version": "2.0",
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
EOF

# Create function code
mkdir WorkflowTimer
cat > WorkflowTimer/function.json <<'EOF'
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "mytimer",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "0 0 2 * * *"
    }
  ]
}
EOF

# Create the Python function
cat > WorkflowTimer/__init__.py <<'EOF'
import logging
import os
import sys
from datetime import datetime
import azure.functions as func

# Add parent directory to path to import workflow
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main(mytimer: func.TimerRequest) -> None:
    logging.info(f'Workflow timer trigger function started at {datetime.utcnow()}')

    try:
        # Import and run the workflow
        from run_end_to_end_workflow import main as run_workflow

        # Run for today's date
        logging.info("Starting SAM.gov workflow for today")
        run_workflow()

        logging.info('Workflow completed successfully')
    except Exception as e:
        logging.error(f'Workflow failed: {str(e)}')
        raise
EOF

# Copy necessary files
cp ../run_end_to_end_workflow.py .
cp -r ../app .
cp -r ../backend .
cp ../requirements.txt .

# Add Azure Functions requirements
cat >> requirements.txt <<'EOF'
azure-functions
pyodbc
EOF

# Deploy function
export FUNCTION_APP_NAME="sam-workflow-func-XXXXXX"  # Replace with your Function App name

func azure functionapp publish $FUNCTION_APP_NAME
```

---

## ✅ Test Your Deployment

### 1. Test Backend API

```bash
# Replace with your actual URL
export APP_URL="https://sam-govwin-app-XXXXXX.azurewebsites.net"

# Test health endpoint
curl $APP_URL/health

# Should return: {"status":"healthy"}
```

### 2. Test Database Connection

```bash
curl $APP_URL/api/sam-opportunities/

# Should return: [] (empty array initially)
```

### 3. Run End-to-End Test

Manually trigger the workflow to test:

```bash
# SSH into your Web App
az webapp ssh --resource-group sam-govwin-rg --name $WEB_APP_NAME

# Inside the SSH session:
python run_end_to_end_workflow.py

# This will:
# 1. Fetch today's SAM.gov opportunities
# 2. Analyze them with AI
# 3. Match with GovWin
# 4. Store in database
```

### 4. Access Frontend

Open your browser and navigate to:

```
https://sam-govwin-app-XXXXXX.azurewebsites.net
```

You should see the frontend interface!

### 5. Test Nightly Job

```bash
# Manually trigger the function to test
az functionapp function invoke \
    --resource-group sam-govwin-rg \
    --name $FUNCTION_APP_NAME \
    --function-name WorkflowTimer

# Check logs
az functionapp logs tail \
    --resource-group sam-govwin-rg \
    --name $FUNCTION_APP_NAME
```

---

## 📊 Monitor Your Application

### View Logs

```bash
# Web App logs (real-time)
az webapp log tail \
    --resource-group sam-govwin-rg \
    --name $WEB_APP_NAME

# Function App logs
az functionapp logs tail \
    --resource-group sam-govwin-rg \
    --name $FUNCTION_APP_NAME
```

### Check Database

```bash
# Connect to SQL Database
sqlcmd -S ${SQL_SERVER}.database.windows.net -d sam_govwin -U samadmin -P "$SQL_PASSWORD"

# Run query
SELECT COUNT(*) FROM sam_opportunities;
GO
```

### View Metrics in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Resource Group: `sam-govwin-rg`
3. Click on your Web App
4. View metrics: CPU, Memory, Requests, Response Times

---

## 🔄 Update Your Application

When you make code changes:

```bash
# Option 1: Quick update (code only)
zip -r deploy.zip . -x "*.git*" -x "*node_modules*" -x "frontend/*"
az webapp deployment source config-zip \
    --resource-group sam-govwin-rg \
    --name $WEB_APP_NAME \
    --src deploy.zip

# Option 2: Git push (if using Git deploy)
git add .
git commit -m "Update application"
git push azure main

# Restart the app
az webapp restart \
    --resource-group sam-govwin-rg \
    --name $WEB_APP_NAME
```

---

## 💰 Cost Management

### View Current Costs

```bash
# Check current month's costs
az consumption usage list \
    --start-date $(date -v-30d +%Y-%m-%d) \
    --end-date $(date +%Y-%m-%d) \
    --query "[?contains(instanceName,'sam')].{Name:instanceName,Cost:pretaxCost}" \
    --output table
```

### Set Budget Alert

```bash
# Set $50/month budget alert
az consumption budget create \
    --resource-group sam-govwin-rg \
    --budget-name "MonthlyBudget" \
    --amount 50 \
    --time-period Month \
    --start-date $(date +%Y-%m-01) \
    --end-date $(date -v+1y +%Y-%m-01)
```

---

## 🧹 Cleanup (Delete Everything)

If you want to remove everything:

```bash
# This deletes EVERYTHING - cannot be undone!
az group delete --name sam-govwin-rg --yes --no-wait
```

---

## 🐛 Troubleshooting

### App Won't Start

```bash
# Check logs
az webapp log tail --resource-group sam-govwin-rg --name $WEB_APP_NAME

# Check startup command
az webapp config show --resource-group sam-govwin-rg --name $WEB_APP_NAME
```

### Database Connection Issues

```bash
# Test connection string
az webapp config connection-string list \
    --resource-group sam-govwin-rg \
    --name $WEB_APP_NAME
```

### Function Not Running

```bash
# Check function status
az functionapp function show \
    --resource-group sam-govwin-rg \
    --name $FUNCTION_APP_NAME \
    --function-name WorkflowTimer

# Check schedule
cat azure_function/WorkflowTimer/function.json
```

---

## 📚 Additional Resources

- [Azure App Service Docs](https://learn.microsoft.com/en-us/azure/app-service/)
- [Azure Functions Docs](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Azure SQL Database Docs](https://learn.microsoft.com/en-us/azure/azure-sql/)

---

## ✅ Success Checklist

- [ ] Azure CLI installed and logged in
- [ ] Deployment script ran successfully
- [ ] Application URL is accessible
- [ ] Backend API `/health` endpoint returns `{"status":"healthy"}`
- [ ] Database is initialized
- [ ] End-to-end workflow runs successfully
- [ ] Frontend loads in browser
- [ ] Nightly function is scheduled and working
- [ ] Costs are being monitored

**Congratulations! Your application is deployed!** 🎉
