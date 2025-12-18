#!/usr/bin/env python
"""
Helper script to find or create a default Account in CRM for SAM opportunities.
Opportunities in Dynamics 365 often require a customer (Account) to be visible in standard views.

Usage:
  From repository root: python backend/get_default_account.py
  From backend directory: python get_default_account.py
"""
import sys
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Determine if we're running from repo root or backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir.endswith('backend'):
    # Running from backend directory
    sys.path.insert(0, current_dir)
else:
    # Running from repo root
    sys.path.insert(0, os.path.join(current_dir, 'backend'))

from app.dynamics_auth import get_access_token, DynamicsAuthConfig
from app.dynamics_client import DynamicsClient


def find_or_create_default_account():
    """Find existing or create a default Account for SAM opportunities."""
    config = DynamicsAuthConfig()

    print("=" * 80)
    print("FIND OR CREATE DEFAULT ACCOUNT FOR SAM OPPORTUNITIES")
    print("=" * 80)

    if not config.is_configured():
        print(f"\n❌ Configuration incomplete. Missing: {', '.join(config.get_missing_config())}")
        return None

    try:
        access_token = get_access_token()
        client = DynamicsClient(resource_url=config.resource_url, access_token=access_token)

        # Search for existing "SAM.gov Opportunities" account
        account_name = "SAM.gov Opportunities"

        print(f"\nSearching for account: '{account_name}'...")

        endpoint = f"{client.base_api_url}/accounts"
        params = {
            '$filter': f"name eq '{account_name}'",
            '$select': 'accountid,name,createdon',
            '$top': 1
        }

        response = requests.get(
            endpoint,
            headers=client._get_headers(),
            params=params,
            timeout=30
        )
        response.raise_for_status()

        accounts = response.json().get('value', [])

        if accounts:
            account = accounts[0]
            account_id = account.get('accountid')
            print(f"\n✓ Found existing account!")
            print(f"  Account ID: {account_id}")
            print(f"  Name: {account.get('name')}")
            print(f"  Created: {account.get('createdon')}")
            return account_id

        # Account doesn't exist, create it
        print(f"\nAccount not found. Creating new account: '{account_name}'...")

        account_data = {
            'name': account_name,
            'description': 'Default account for SAM.gov federal contract opportunities imported from the SAM Opportunity Management System'
        }

        response = requests.post(
            endpoint,
            json=account_data,
            headers=client._get_headers(),
            timeout=30
        )
        response.raise_for_status()

        # Extract account ID
        account_id = None
        if 'OData-EntityId' in response.headers:
            entity_id_url = response.headers['OData-EntityId']
            account_id = entity_id_url.split('(')[-1].rstrip(')')

        print(f"\n✓ Created new account!")
        print(f"  Account ID: {account_id}")
        print(f"  Name: {account_name}")

        print("\n" + "=" * 80)
        print("CONFIGURATION")
        print("=" * 80)
        print("\nAdd this to your .env file (or Render environment variables):")
        print(f"DYNAMICS_DEFAULT_ACCOUNT_ID={account_id}")
        print("\nThis account will be used as the 'Potential Customer' for all SAM opportunities.")

        return account_id

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\nDynamics CRM Default Account Setup")
    print("This script will find or create a default account for SAM opportunities.\n")

    account_id = find_or_create_default_account()

    if account_id:
        print("\n" + "=" * 80)
        print("SUCCESS")
        print("=" * 80)
        print(f"\nAccount ID: {account_id}")
        print("\nNext steps:")
        print("1. Add DYNAMICS_DEFAULT_ACCOUNT_ID to your environment variables")
        print("2. Test creating an opportunity with this account")
        print("3. The opportunity should now appear in your CRM views")
    else:
        print("\n" + "=" * 80)
        print("FAILED")
        print("=" * 80)

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
