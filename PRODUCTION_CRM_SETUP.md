# Production CRM Setup Guide (Render)

Quick guide for setting up CRM integration on Render deployment.

## Problem

You're getting confirmation that CRM records are created, but they don't appear in your Dynamics 365 Opportunities view.

## Root Cause

Dynamics 365 Opportunities require a "Potential Customer" (Account) to be visible in standard views.

## Solution (5 Steps)

### Step 1: Access Render Shell

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Select your backend service (`sam-govwin-api`)
3. Click the **Shell** tab

### Step 2: Run Default Account Script

In the Render shell, run:

```bash
python backend/get_default_account.py
```

**Expected Output:**
```
================================================================================
FIND OR CREATE DEFAULT ACCOUNT FOR SAM OPPORTUNITIES
================================================================================

Searching for account: 'SAM.gov Opportunities'...

✓ Created new account!
  Account ID: 12345678-1234-1234-1234-123456789abc
  Name: SAM.gov Opportunities

================================================================================
CONFIGURATION
================================================================================

Add this to your .env file (or Render environment variables):
DYNAMICS_DEFAULT_ACCOUNT_ID=12345678-1234-1234-1234-123456789abc
```

**Copy the Account ID** (the long GUID that looks like `12345678-1234-1234-1234-123456789abc`)

### Step 3: Add Environment Variable

1. In Render Dashboard, go to your backend service
2. Click the **Environment** tab
3. Click **Add Environment Variable**
4. Enter:
   - **Key**: `DYNAMICS_DEFAULT_ACCOUNT_ID`
   - **Value**: `12345678-1234-1234-1234-123456789abc` (paste your actual GUID)
5. Click **Save Changes**

### Step 4: Redeploy

Render will automatically redeploy when you add/change environment variables. Wait for deployment to complete (usually 2-3 minutes).

### Step 5: Test

1. Go to your production application
2. Find any SAM opportunity
3. Click "Send to CRM"
4. You should get a success message
5. Go to Dynamics 365 → Sales → Opportunities → **All Opportunities**
6. Look for the opportunity - it should now appear!
7. Check the "Potential Customer" field - it should show "SAM.gov Opportunities"

## Verification

To verify an opportunity was created and check its details:

**In Render Shell:**
```bash
python backend/test_crm_opportunity.py
```

This will:
- Create a test opportunity
- Retrieve it from CRM
- Show all key fields including Owner and Customer
- Provide a direct link to view it in CRM

## Troubleshooting

### "Configuration incomplete" Error

**Problem:** Script says environment variables are missing.

**Solution:** Check that all of these are set in Render Environment tab:
- `DYNAMICS_TENANT_ID`
- `DYNAMICS_CLIENT_ID`
- `DYNAMICS_CLIENT_SECRET`
- `DYNAMICS_RESOURCE_URL`

### "Failed to acquire access token" Error

**Problem:** Can't authenticate to Dynamics.

**Solution:**
1. Verify Azure AD app registration is correct
2. Check client secret hasn't expired
3. Ensure app has correct API permissions
4. See [CRM_SETUP_GUIDE.md](CRM_SETUP_GUIDE.md) for detailed Azure setup

### Account Created But Opportunities Still Not Visible

**Possible Causes:**

1. **Didn't redeploy** after adding environment variable
   - Solution: Manually trigger redeploy in Render

2. **Account ownership issue**
   - Solution: In CRM, check who owns the opportunities (might be the app user)
   - Change view to "All Opportunities" instead of "My Open Opportunities"

3. **View filters**
   - Solution: Try different views in CRM (All Opportunities, Recently Created, etc.)

4. **Permissions**
   - Solution: Ensure the application user in CRM has "Salesperson" or "Sales Manager" role

See [CRM_TROUBLESHOOTING.md](CRM_TROUBLESHOOTING.md) for more detailed troubleshooting.

## Quick Reference

| Task | Command |
|------|---------|
| Create default account | `python backend/get_default_account.py` |
| Test CRM opportunity | `python backend/test_crm_opportunity.py` |
| Check CRM schema | `python backend/test_crm_schema.py` |

## Environment Variables Checklist

For CRM integration to work, you need these set in Render Dashboard → Environment:

- [ ] `DYNAMICS_TENANT_ID`
- [ ] `DYNAMICS_CLIENT_ID`
- [ ] `DYNAMICS_CLIENT_SECRET`
- [ ] `DYNAMICS_RESOURCE_URL`
- [ ] `DYNAMICS_DEFAULT_ACCOUNT_ID` ← You get this from the script

## After Setup

Once `DYNAMICS_DEFAULT_ACCOUNT_ID` is configured, all future opportunities sent to CRM will:
- ✅ Automatically link to "SAM.gov Opportunities" account
- ✅ Appear in standard CRM opportunity views
- ✅ Be searchable and filterable
- ✅ Follow your CRM workflows and business processes

## Need Help?

If you've followed these steps and opportunities still aren't appearing:

1. Check Render logs for error messages
2. Run `python backend/test_crm_opportunity.py` and share output
3. Verify in CRM: Sales → Opportunities → All Opportunities (not "My Open Opportunities")
4. Check the direct CRM link format:
   ```
   https://yourorg.crm.dynamics.com/main.aspx?etn=opportunity&id={GUID}
   ```
5. See [CRM_TROUBLESHOOTING.md](CRM_TROUBLESHOOTING.md) for comprehensive troubleshooting

## Additional Resources

- [CRM_SETUP_GUIDE.md](CRM_SETUP_GUIDE.md) - Complete Azure AD and CRM setup
- [CRM_TROUBLESHOOTING.md](CRM_TROUBLESHOOTING.md) - Detailed troubleshooting guide
- [README.md](README.md) - Full application documentation
