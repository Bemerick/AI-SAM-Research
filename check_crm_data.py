"""
Diagnostic script to check if opportunities are in Dynamics CRM
"""
import os
import requests
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, '.')
from backend.app.dynamics_auth import get_access_token

# Get credentials
resource_url = os.getenv('DYNAMICS_RESOURCE_URL', '').rstrip('/')

print(f"🔍 CRM Diagnostics")
print(f"=" * 80)
print(f"Tenant ID: {os.getenv('DYNAMICS_TENANT_ID')}")
print(f"Client ID: {os.getenv('DYNAMICS_CLIENT_ID')}")
print(f"CRM URL: {resource_url}")
print(f"=" * 80)

# Get access token
try:
    access_token = get_access_token()
    print(f"\n✓ Authentication successful\n")

    # Query the most recent opportunities from custom table
    url = f"{resource_url}/api/data/v9.2/new_opportunities?$top=10&$orderby=createdon desc&$select=new_opportunityid,new_name,createdon,statecode,statuscode"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'OData-MaxVersion': '4.0',
        'OData-Version': '4.0',
    }

    print(f"📥 Querying CRM for recent opportunities...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    opportunities = data.get('value', [])

    print(f"\n✓ Found {len(opportunities)} recent opportunities:\n")
    print("=" * 80)

    if len(opportunities) == 0:
        print("⚠️  No opportunities found in CRM!")
        print("\nPossible reasons:")
        print("1. You're looking at the wrong environment")
        print("2. The application user doesn't have permission to read opportunities")
        print("3. The opportunities are in a different business unit")
        print("4. The opportunities haven't been created yet")
    else:
        for i, opp in enumerate(opportunities, 1):
            print(f"{i}. {opp.get('new_name')}")
            print(f"   ID: {opp.get('new_opportunityid')}")
            print(f"   Created: {opp.get('createdon')}")
            print(f"   State: {opp.get('statecode')} | Status: {opp.get('statuscode')}")
            print("-" * 80)

except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("💡 How to find opportunities in Dynamics CRM:")
print("=" * 80)
print("1. Go to https://org56e3ecfe.crm.dynamics.com")
print("2. Click on 'Sales' in the left navigation")
print("3. Click on 'Opportunities'")
print("4. Check the view filter - make sure you're looking at 'All Opportunities' or 'My Open Opportunities'")
print("5. Look for opportunities with names from your SAM data")
print("=" * 80)
