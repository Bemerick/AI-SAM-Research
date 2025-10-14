# Microsoft Dynamics CRM Integration Setup Guide

This guide will help you configure authentication for Microsoft Dynamics CRM integration.

## Prerequisites

1. Access to Microsoft Azure Portal
2. Access to your Dynamics CRM instance
3. Admin privileges to create app registrations in Azure AD

## Step 1: Install Required Python Package

The MSAL (Microsoft Authentication Library) package is required for OAuth authentication.

```bash
pip install msal
```

## Step 2: Create Azure AD App Registration

1. **Go to Azure Portal** (https://portal.azure.com)

2. **Navigate to Azure Active Directory** (or Microsoft Entra ID)
   - Click on "App registrations"
   - Click "New registration"

3. **Register Your Application**
   - Name: `SAM-Opportunity-Manager` (or your preferred name)
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: Not needed for service principal (leave blank)
   - Click "Register"

4. **Note Your Application IDs**
   - After registration, you'll see the **Overview** page
   - Copy the following values:
     - **Application (client) ID** - You'll use this as `DYNAMICS_CLIENT_ID`
     - **Directory (tenant) ID** - You'll use this as `DYNAMICS_TENANT_ID`

5. **Create a Client Secret**
   - In the left menu, click "Certificates & secrets"
   - Click "New client secret"
   - Description: `CRM Integration Secret`
   - Expires: Choose appropriate expiration (e.g., 24 months)
   - Click "Add"
   - **IMPORTANT**: Copy the secret **Value** immediately - you'll use this as `DYNAMICS_CLIENT_SECRET`
   - You won't be able to see it again!

## Step 3: Grant API Permissions

1. **Add Dynamics CRM Permission**
   - In your app registration, click "API permissions"
   - Click "Add a permission"
   - Click "Dynamics CRM" (or "Dataverse")
   - Select "Delegated permissions" OR "Application permissions" (recommended)
   - Check `user_impersonation` (for delegated) or appropriate app permission
   - Click "Add permissions"

2. **Grant Admin Consent**
   - Click "Grant admin consent for [Your Organization]"
   - Click "Yes" to confirm
   - All permissions should now show a green checkmark

## Step 4: Create Application User in Dynamics CRM

Your service principal needs to be added as an application user in Dynamics CRM.

### Option A: Using Power Platform Admin Center (Recommended)

1. Go to https://admin.powerplatform.microsoft.com/
2. Select your environment
3. Go to "Settings" → "Users + permissions" → "Application users"
4. Click "+ New app user"
5. Click "+ Add an app"
6. Select your Azure AD app (SAM-Opportunity-Manager)
7. Select a Business Unit
8. Assign appropriate security roles (e.g., "System Administrator" or custom role)
9. Click "Create"

### Option B: Using Dynamics CRM (Classic)

1. Go to **Settings** → **Security** → **Users**
2. Change view to "Application Users"
3. Click **New**
4. Fill in:
   - Application ID: Your `DYNAMICS_CLIENT_ID`
   - Full Name: SAM Opportunity Manager
   - Primary Email: your-email@company.com
5. Save
6. Assign security roles

## Step 5: Configure Environment Variables

Add these variables to your `.env` file:

```bash
# Microsoft Dynamics CRM Configuration
DYNAMICS_TENANT_ID=your-tenant-id-here
DYNAMICS_CLIENT_ID=your-client-id-here
DYNAMICS_CLIENT_SECRET=your-client-secret-here
DYNAMICS_RESOURCE_URL=https://yourorg.crm.dynamics.com
```

### How to find your Dynamics URL:

1. Log into your Dynamics CRM
2. Copy the URL from your browser
3. It should look like: `https://yourorg.crm.dynamics.com` or `https://yourorg.crm4.dynamics.com`
4. Use just the base URL (without any path after .com)

## Step 6: Customize Field Mapping

Edit `backend/app/dynamics_client.py` in the `map_sam_opportunity_to_crm()` function to match your CRM schema:

```python
def map_sam_opportunity_to_crm(sam_opportunity: Dict[str, Any]) -> Dict[str, Any]:
    crm_data = {
        'name': sam_opportunity.get('title', 'Untitled Opportunity'),
        'description': sam_opportunity.get('summary_description', ''),
        # Add your custom fields here based on your CRM schema
        # Example: 'new_customfield': sam_opportunity.get('field_name')
    }
    return crm_data
```

### Finding Your CRM Field Names:

1. Go to **Settings** → **Customizations** → **Customize the System**
2. Expand **Entities** → **Opportunity**
3. Click **Fields**
4. Note the "Schema Name" (starts with `new_` for custom fields)
5. Use these schema names in your field mapping

## Step 7: Test the Integration

1. **Restart your backend server** to load the new environment variables

2. **Test via the frontend**:
   - Navigate to an opportunity detail page
   - Click "Send to CRM"
   - Check for success message

3. **Verify in CRM**:
   - Go to your Dynamics CRM
   - Navigate to Sales → Opportunities
   - Look for the newly created opportunity

## Troubleshooting

### Error: "AADSTS7000215: Invalid client secret provided"
- Your client secret is incorrect or has expired
- Create a new client secret in Azure AD

### Error: "AADSTS50105: The signed in user is not assigned to a role"
- The application user hasn't been properly created in Dynamics
- Follow Step 4 again

### Error: "Principal user is missing prvRead privilege"
- The application user doesn't have proper security roles
- Assign appropriate security roles in Dynamics

### Authentication works but opportunity creation fails
- Check the field mapping - you may have invalid field names
- Check application user has permissions to create opportunities
- Check the logs for detailed error messages

## Security Best Practices

1. **Never commit secrets to git**
   - Always use `.env` file
   - Ensure `.env` is in `.gitignore`

2. **Use separate credentials for dev/prod**
   - Create separate app registrations for each environment

3. **Rotate secrets regularly**
   - Set expiration dates on client secrets
   - Update `.env` before expiration

4. **Principle of Least Privilege**
   - Only grant necessary permissions to the application user
   - Create a custom security role if needed

## Additional Resources

- [Microsoft Dataverse Web API Reference](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview)
- [Azure AD App Registration Guide](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
