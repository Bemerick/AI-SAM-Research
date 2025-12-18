#!/usr/bin/env python
"""Test account binding for custom opportunity table."""
import sys
import os
from dotenv import load_dotenv

# Load .env from repo root or backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, '.env')):
    load_dotenv(os.path.join(current_dir, '.env'))
else:
    load_dotenv(os.path.join(current_dir, '..', '.env'))

sys.path.insert(0, current_dir)

from app.dynamics_auth import get_access_token, DynamicsAuthConfig
from app.dynamics_client import DynamicsClient
import requests

config = DynamicsAuthConfig()
access_token = get_access_token()
client = DynamicsClient(resource_url=config.resource_url, access_token=access_token)

account_id = os.getenv('DYNAMICS_DEFAULT_ACCOUNT_ID')

print("=" * 80)
print("TESTING ACCOUNT BINDING FOR CUSTOM TABLE")
print("=" * 80)

print(f"\nAccount ID: {account_id}")

# Test 1: Check if account exists
print("\n1. Checking if account exists...")
endpoint = f"{client.base_api_url}/accounts({account_id})"
response = requests.get(endpoint, headers=client._get_headers(), timeout=30)

if response.status_code == 200:
    account = response.json()
    print(f"✓ Account found: {account.get('name')}")
else:
    print(f"✗ Account not found: Status {response.status_code}")
    print(f"  Response: {response.text[:200]}")
    print("\nThe account ID may be incorrect. Run get_default_account.py to find the correct ID.")
    exit(1)

# Test 2: Try creating a minimal opportunity without account binding
print("\n2. Testing opportunity creation WITHOUT account binding...")
test_data_no_account = {
    'new_name': 'Test Without Account'
}

endpoint = f"{client.base_api_url}/new_opportunities"
response = requests.post(endpoint, json=test_data_no_account, headers=client._get_headers(), timeout=30)

if response.status_code in [200, 201, 204]:
    print("✓ Opportunity created without account binding")
    # Try to get the ID
    if 'OData-EntityId' in response.headers:
        entity_id_url = response.headers['OData-EntityId']
        opp_id = entity_id_url.split('(')[-1].rstrip(')')
        print(f"  Opportunity ID: {opp_id}")
else:
    print(f"✗ Failed: Status {response.status_code}")
    print(f"  Response: {response.text[:500]}")

# Test 3: Try WITH account binding using @odata.bind
print("\n3. Testing opportunity creation WITH account binding (@odata.bind)...")
test_data_with_account = {
    'new_name': 'Test With Account Binding',
    'new_accountname@odata.bind': f"/accounts({account_id})"
}

response = requests.post(endpoint, json=test_data_with_account, headers=client._get_headers(), timeout=30)

if response.status_code in [200, 201, 204]:
    print("✓ Opportunity created WITH account binding")
    if 'OData-EntityId' in response.headers:
        entity_id_url = response.headers['OData-EntityId']
        opp_id = entity_id_url.split('(')[-1].rstrip(')')
        print(f"  Opportunity ID: {opp_id}")
        print(f"  SUCCESS! The account binding works.")
else:
    print(f"✗ Failed: Status {response.status_code}")
    error_text = response.text
    print(f"  Response: {error_text[:500]}")

    # Try alternative: Maybe custom table doesn't support lookup binding
    print("\n4. Testing if lookup fields are read-only...")
    print("   Some custom tables have lookup fields as read-only system fields.")
    print("   If this is the case, you may need to set the account after creation,")
    print("   or the field might not be settable via API at all.")

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print("\nIf test #3 failed, the custom table may not support setting the account")
print("during creation. Options:")
print("1. Create opportunity without account binding (skip customer_id)")
print("2. Set account in a separate UPDATE call after creation")
print("3. Check if new_accountname is a calculated/system field")
