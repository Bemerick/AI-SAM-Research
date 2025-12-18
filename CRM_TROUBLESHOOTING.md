# Dynamics CRM Troubleshooting Guide

## Problem: Opportunities Created But Not Visible in CRM

If you're receiving confirmation that records are created in Dynamics CRM but you can't see them in the Opportunities view, here are the most common causes and solutions.

## Common Causes

### 1. Missing Customer (Account/Contact) Relationship ⭐ MOST COMMON

**Problem:** Dynamics 365 Opportunities typically require a "Potential Customer" (Account or Contact) to be visible in standard views. If this field is empty, the opportunity may be hidden.

**Solution:**

#### Step 1: Create a Default Account

Run the helper script to find or create a default account:

**Local Development:**
```bash
cd backend
python get_default_account.py
```

**Production (Render Shell):**
```bash
# SSH into your Render service or use the Shell tab in Render dashboard
python backend/get_default_account.py
```

This will:
- Search for an existing "SAM.gov Opportunities" account
- Create one if it doesn't exist
- Return the Account ID (GUID)

#### Step 2: Add Account ID to Environment

Add the account ID to your environment variables:

**Local Development (.env file):**
```bash
DYNAMICS_DEFAULT_ACCOUNT_ID=your-account-guid-here
```

**Production (Render Dashboard):**
1. Go to your Render service dashboard
2. Navigate to Environment tab
3. Add new variable:
   - Key: `DYNAMICS_DEFAULT_ACCOUNT_ID`
   - Value: `your-account-guid-here`
4. Save and redeploy

#### Step 3: Test

Create a new opportunity. It should now appear in your CRM with "SAM.gov Opportunities" as the Potential Customer.

---

### 2. View Filters and Permissions

**Problem:** The CRM view you're looking at has filters that exclude your opportunities.

**Solution:**

Try these different views in Dynamics 365:
1. **All Opportunities** - Should show all opportunities you have access to
2. **My Open Opportunities** - Only shows opportunities owned by you
3. **System Views** - Check various system-defined views

To check:
1. Go to Sales → Opportunities
2. Click the view dropdown (usually says "My Open Opportunities")
3. Try "All Opportunities" or other views
4. Look for recently created dates

---

### 3. Owner Assignment

**Problem:** Opportunities are being assigned to the service account or application user, not to you.

**Solution:**

Check who owns the opportunities:

1. Run the diagnostic script:
```bash
cd backend
python test_crm_opportunity.py
```

This will show the owner ID of created opportunities.

2. In CRM, use Advanced Find:
   - Entity: Opportunities
   - Filter: Created On = Last 7 Days
   - Add column: Owner
   - Check if opportunities are assigned to the application user

3. If needed, you can set a default owner in the code or reassign in CRM.

---

### 4. Business Process Flow Requirements

**Problem:** Your CRM has a Business Process Flow that requires certain fields to be filled before the opportunity is visible.

**Solution:**

1. Check your CRM customizations for required fields
2. Run the schema inspector to see required fields:
```bash
cd backend
python test_crm_schema.py
```

3. Update `dynamics_client.py` to include any additional required fields in the mapping function.

---

### 5. Security Roles and Permissions

**Problem:** The application user doesn't have proper permissions to create visible opportunities.

**Solution:**

Verify the application user has the correct security role:

1. In Dynamics 365, go to Settings → Security → Users
2. Find your application user (Application Users view)
3. Check assigned security roles
4. Ensure it has at least "Salesperson" or "Sales Manager" role
5. Verify permissions include:
   - Create Opportunity
   - Read Opportunity
   - Append To Account

---

## Diagnostic Tools

### Tool 1: Test CRM Schema
```bash
cd backend
python test_crm_schema.py
```

Shows:
- Available fields in your CRM
- Required fields
- Custom fields
- Field types and constraints

### Tool 2: Test Opportunity Creation

**Local Development:**
```bash
cd backend
python test_crm_opportunity.py
```

**Production (Render):**
```bash
python backend/test_crm_opportunity.py
```

Shows:
- Creates a test opportunity
- Retrieves it back from CRM
- Lists recent opportunities
- Shows owner, customer, and other key fields
- Provides direct link to the opportunity

### Tool 3: Get Default Account

**Local Development:**
```bash
cd backend
python get_default_account.py
```

**Production (Render):**
```bash
python backend/get_default_account.py
```

Shows:
- Finds or creates a default account
- Returns the account GUID
- Provides configuration instructions

---

## Manual Verification Steps

### 1. Check Directly in CRM

Use the direct link format:
```
https://yourorg.crm.dynamics.com/main.aspx?etn=opportunity&id={GUID}&pagetype=entityrecord
```

Replace:
- `yourorg.crm.dynamics.com` with your CRM URL
- `{GUID}` with the opportunity ID returned from creation

### 2. Use Advanced Find

In Dynamics 365:
1. Click the funnel icon (Advanced Find)
2. Look for: Opportunities
3. Add filters:
   - Created On = Last 7 Days
   - Name contains "TEST" (or your opportunity title)
4. Results show the opportunity with all fields

### 3. Check System Jobs

If opportunities are being processed by workflows:
1. Go to Settings → System Jobs
2. Look for recent jobs related to opportunities
3. Check for any failures or warnings

---

## Updated Code Changes

The following changes have been made to address the missing customer issue:

### 1. `dynamics_client.py`

Added `customer_id` parameter to `map_sam_opportunity_to_crm()`:

```python
def map_sam_opportunity_to_crm(sam_opportunity: Dict[str, Any], customer_id: Optional[str] = None) -> Dict[str, Any]:
    # ...
    if customer_id:
        crm_data['customerid_account@odata.bind'] = f"/accounts({customer_id})"
    # ...
```

### 2. `crm_integration.py`

Updated to use default account from environment:

```python
default_account_id = os.getenv('DYNAMICS_DEFAULT_ACCOUNT_ID')
crm_data = map_sam_opportunity_to_crm(opportunity_dict, customer_id=default_account_id)
```

---

## Quick Checklist

- [ ] Run `get_default_account.py` to create default account
- [ ] Add `DYNAMICS_DEFAULT_ACCOUNT_ID` to environment variables
- [ ] Redeploy application (if production)
- [ ] Create a test opportunity
- [ ] Check "All Opportunities" view in CRM
- [ ] Use direct link to verify opportunity exists
- [ ] Verify "Potential Customer" field is populated

---

## Still Not Working?

If you've tried all the above and still can't see opportunities:

1. **Check Application User Permissions:**
   - Ensure application user exists in CRM
   - Verify security roles are assigned
   - Check business unit assignment

2. **Review CRM Audit Logs:**
   - Go to Settings → Auditing
   - Check audit history for opportunity creates
   - Look for any access denied errors

3. **Test with Different User:**
   - Try creating opportunities manually in CRM
   - If manual creation works, it's a permissions issue with the app user

4. **Check API Response:**
   - Look at backend logs for the actual API response
   - Verify the GUID returned is valid
   - Try using the GUID directly in a GET request

5. **Contact CRM Administrator:**
   - There may be organization-specific customizations
   - Business process flows may require additional fields
   - Custom plugins may be interfering with creation

---

## Example: Complete Setup

**Local Development:**
```bash
# 1. Create default account
cd backend
python get_default_account.py

# Output shows:
# Account ID: 12345678-1234-1234-1234-123456789abc

# 2. Add to .env file:
DYNAMICS_DEFAULT_ACCOUNT_ID=12345678-1234-1234-1234-123456789abc

# 3. Test opportunity creation
python test_crm_opportunity.py

# 4. Check CRM
# - Go to Sales → Opportunities → All Opportunities
# - Look for test opportunity
# - Verify "Potential Customer" = "SAM.gov Opportunities"
```

**Production (Render):**
```bash
# 1. Open Shell in Render dashboard for your backend service
# 2. Run the script:
python backend/get_default_account.py

# Output shows:
# Account ID: 12345678-1234-1234-1234-123456789abc

# 3. Go to Render Dashboard → Environment tab
# 4. Add new environment variable:
#    Key: DYNAMICS_DEFAULT_ACCOUNT_ID
#    Value: 12345678-1234-1234-1234-123456789abc

# 5. Redeploy the service

# 6. Test creating an opportunity from your production app
```

---

## Need More Help?

If you're still having issues, gather this information:

1. Output from `test_crm_schema.py`
2. Output from `test_crm_opportunity.py`
3. Backend logs showing the create opportunity request
4. Screenshot of your CRM "All Opportunities" view
5. Your CRM organization URL
6. The GUID of an opportunity you tried to create

This will help diagnose any organization-specific configuration issues.
