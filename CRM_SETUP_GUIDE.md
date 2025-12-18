# Microsoft Dynamics 365 CRM Integration Setup Guide

This guide explains how to configure the SAM Opportunity System to integrate with Microsoft Dynamics 365 CRM.

## Overview

The system can automatically send SAM.gov opportunities to your Dynamics 365 CRM as opportunity records. This requires OAuth 2.0 authentication using Azure AD (Microsoft Entra ID).

## Prerequisites

1. Microsoft Dynamics 365 subscription
2. Azure AD (Entra ID) tenant with admin access
3. Dynamics 365 environment URL (e.g., `https://yourorg.crm.dynamics.com`)

## Setup Steps

### 1. Register an Application in Azure AD

1. Go to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Configure the app:
   - **Name**: `SAM Opportunity System` (or your preferred name)
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: Leave blank (not needed for service principal authentication)
5. Click **Register**

### 2. Get Application Credentials

After registration, note the following values (you'll need them later):

1. **Application (client) ID**: Found on the app's Overview page
2. **Directory (tenant) ID**: Found on the app's Overview page
3. **Client Secret**: 
   - Go to **Certificates & secrets**
   - Click **New client secret**
   - Add a description and choose expiration
   - **IMPORTANT**: Copy the secret **value** immediately (you won't be able to see it again)

### 3. Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission**
3. Select **Dynamics CRM** (or **Common Data Service**)
4. Choose **Application permissions**
5. Select `user_impersonation` permission
6. Click **Add permissions**
7. Click **Grant admin consent** (requires admin rights)

### 4. Create an Application User in Dynamics 365

1. Log in to [Power Platform Admin Center](https://admin.powerplatform.microsoft.com)
2. Select your environment
3. Go to **Settings** > **Users + permissions** > **Application users**
4. Click **New app user**
5. Select the Azure AD app you created
6. Assign security roles (e.g., **Sales Manager** or a custom role with opportunity create/update permissions)
7. Save

### 5. Configure Environment Variables

Add the following environment variables to your backend `.env` file or deployment configuration:

```bash
# Microsoft Dynamics CRM Configuration
DYNAMICS_TENANT_ID=your-tenant-id-here
DYNAMICS_CLIENT_ID=your-client-id-here
DYNAMICS_CLIENT_SECRET=your-client-secret-here
DYNAMICS_RESOURCE_URL=https://yourorg.crm.dynamics.com
```

**Replace the values:**
- `DYNAMICS_TENANT_ID`: Directory (tenant) ID from step 2
- `DYNAMICS_CLIENT_ID`: Application (client) ID from step 2
- `DYNAMICS_CLIENT_SECRET`: Client secret value from step 2
- `DYNAMICS_RESOURCE_URL`: Your Dynamics 365 environment URL (without trailing slash)

### 6. Restart Backend Service

After adding the environment variables, restart your backend service:

```bash
# If running locally
uvicorn app.main:app --reload

# If using Docker
docker-compose restart backend
```

### 7. Test the Integration

1. Open the SAM Opportunity System frontend
2. Navigate to an opportunity detail page
3. Click the **Send to CRM** button
4. You should see a success message with a CRM ID
5. Verify the opportunity appears in your Dynamics 365 CRM

## Customizing Field Mappings

The default field mappings are defined in `backend/app/dynamics_client.py` in the `map_sam_opportunity_to_crm()` function.

### Standard Fields Mapped:
- `name` ← Opportunity title
- `description` ← Summary and fit analysis
- `estimatedclosedate` ← Response deadline
- `closeprobability` ← Fit score (converted to percentage)

### Custom Fields (with `new_` prefix):
- `new_samnoticeid` ← SAM notice ID
- `new_solicitationnumber` ← Solicitation number
- `new_naicscode` ← NAICS code
- `new_department` ← Government department
- `new_samlink` ← Link to SAM.gov
- `new_practicearea` ← Assigned practice area
- `new_setaside` ← Set-aside type
- `new_procurementtype` ← Procurement type

**To customize:** Edit the `map_sam_opportunity_to_crm()` function to match your CRM schema.

## Troubleshooting

### Mock Mode Message

If you see "Mock Mode: Opportunity would be sent to CRM (authentication not configured)", one or more environment variables are missing. Check:

```bash
# Verify all required variables are set
echo $DYNAMICS_TENANT_ID
echo $DYNAMICS_CLIENT_ID  
echo $DYNAMICS_CLIENT_SECRET
echo $DYNAMICS_RESOURCE_URL
```

### Authentication Errors

**Error**: `AADSTS700016: Application not found`
- **Solution**: Double-check the `DYNAMICS_CLIENT_ID` matches your Azure AD app

**Error**: `AADSTS7000215: Invalid client secret`
- **Solution**: Regenerate the client secret in Azure AD and update the environment variable

**Error**: `401 Unauthorized`
- **Solution**: Verify the application user exists in Dynamics 365 and has proper permissions

### Permission Errors

**Error**: `Principal user is missing prvCreateOpportunity privilege`
- **Solution**: Assign appropriate security role to the application user in Dynamics 365

## Security Best Practices

1. **Rotate secrets regularly**: Set client secret expiration and rotate before expiry
2. **Use key vault**: Store secrets in Azure Key Vault or similar service
3. **Limit permissions**: Only grant minimum required CRM permissions
4. **Monitor access**: Review application user activity logs in Dynamics 365
5. **Environment variables**: Never commit secrets to source control

## Additional Resources

- [Microsoft Dynamics 365 Web API Documentation](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview)
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Dataverse Service Principal Authentication](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/use-multi-tenant-server-server-authentication)
