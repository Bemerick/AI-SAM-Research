#!/usr/bin/env python
"""
Script to find custom opportunity tables in Dynamics CRM.
This helps identify if you're using a custom table instead of standard 'opportunities'.

Usage:
  From repository root: python backend/find_custom_opportunity_table.py
  From backend directory: python find_custom_opportunity_table.py
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
    sys.path.insert(0, current_dir)
else:
    sys.path.insert(0, os.path.join(current_dir, 'backend'))

from app.dynamics_auth import get_access_token, DynamicsAuthConfig
from app.dynamics_client import DynamicsClient


def find_opportunity_tables():
    """Find all opportunity-related tables in CRM."""
    config = DynamicsAuthConfig()

    print("=" * 80)
    print("FIND CUSTOM OPPORTUNITY TABLES IN DYNAMICS CRM")
    print("=" * 80)

    if not config.is_configured():
        print(f"\n❌ Configuration incomplete. Missing: {', '.join(config.get_missing_config())}")
        return None

    try:
        access_token = get_access_token()
        client = DynamicsClient(resource_url=config.resource_url, access_token=access_token)

        print("\n1. CHECKING STANDARD OPPORTUNITIES TABLE")
        print("=" * 80)

        # Check standard opportunities table
        endpoint = f"{client.base_api_url}/opportunities"
        params = {
            '$top': 1,
            '$select': 'opportunityid,name'
        }

        response = requests.get(
            endpoint,
            headers=client._get_headers(),
            params=params,
            timeout=30
        )

        if response.status_code == 200:
            opportunities = response.json().get('value', [])
            print(f"✓ Standard 'opportunities' table exists")
            print(f"  Found {len(opportunities)} opportunity (showing 1)")
            if opportunities:
                print(f"  Sample ID: {opportunities[0].get('opportunityid')}")
        else:
            print(f"⚠ Standard 'opportunities' table: Status {response.status_code}")

        print("\n2. SEARCHING FOR CUSTOM TABLES")
        print("=" * 80)

        # Get all entity definitions
        metadata_endpoint = f"{client.base_api_url}/EntityDefinitions"
        params = {
            '$select': 'LogicalName,DisplayName,TableType,IsCustomEntity',
            '$filter': "contains(LogicalName,'opportunity') or contains(LogicalName,'opp')"
        }

        response = requests.get(
            metadata_endpoint,
            headers=client._get_headers(),
            params=params,
            timeout=30
        )

        if response.status_code == 200:
            entities = response.json().get('value', [])
            print(f"\nFound {len(entities)} opportunity-related tables:\n")

            for entity in entities:
                logical_name = entity.get('LogicalName')
                display_name = entity.get('DisplayName', {}).get('UserLocalizedLabel', {}).get('Label', 'N/A')
                is_custom = entity.get('IsCustomEntity', False)
                table_type = entity.get('TableType', 'N/A')

                print(f"Table: {logical_name}")
                print(f"  Display Name: {display_name}")
                print(f"  Is Custom: {is_custom}")
                print(f"  Type: {table_type}")
                print()

        print("\n3. CHECKING SPECIFIC OPPORTUNITY ID")
        print("=" * 80)

        # Check if the specific opportunity exists in standard table
        opportunity_id = "f381f6cf-24dc-f011-8543-7c1e527f11f9"
        print(f"\nLooking for opportunity: {opportunity_id}")

        # Try standard table
        print("\nChecking standard 'opportunities' table...")
        endpoint = f"{client.base_api_url}/opportunities({opportunity_id})"
        response = requests.get(endpoint, headers=client._get_headers(), timeout=30)

        if response.status_code == 200:
            opp = response.json()
            print(f"✓ FOUND in standard 'opportunities' table!")
            print(f"  Name: {opp.get('name')}")
            print(f"  Created: {opp.get('createdon')}")
            print(f"  Owner ID: {opp.get('_ownerid_value')}")
            print(f"  Customer ID: {opp.get('_customerid_value', 'NOT SET')}")
            return 'opportunities'
        else:
            print(f"✗ Not found in standard table (Status: {response.status_code})")

        # Try common custom table patterns
        print("\n4. TRYING COMMON CUSTOM TABLE PATTERNS")
        print("=" * 80)

        custom_patterns = [
            'cr7f3_opportunity',
            'cr7f3_opportunities',
            'new_opportunity',
            'new_opportunities',
            'opportunities_extended',
            'custom_opportunity',
        ]

        for table_name in custom_patterns:
            print(f"\nTrying: {table_name}...")
            endpoint = f"{client.base_api_url}/{table_name}({opportunity_id})"
            response = requests.get(endpoint, headers=client._get_headers(), timeout=30)

            if response.status_code == 200:
                opp = response.json()
                print(f"✓✓✓ FOUND in custom table '{table_name}'! ✓✓✓")
                # Try different name field patterns
                name_field = table_name.rstrip('s') + 'name'
                record_name = opp.get('name') or opp.get(name_field) or 'N/A'
                print(f"  Name: {record_name}")
                print(f"  Created: {opp.get('createdon')}")
                print("\n" + "=" * 80)
                print(f"YOUR CUSTOM TABLE IS: {table_name}")
                print("=" * 80)
                return table_name
            else:
                print(f"  Not found (Status: {response.status_code})")

        print("\n5. RECOMMENDATION")
        print("=" * 80)
        print("\nCouldn't automatically find the custom table.")
        print("\nTo find it manually:")
        print("1. In Dynamics 365, go to Settings → Customizations")
        print("2. Look for your custom Opportunity table")
        print("3. Check the 'Name' field (not Display Name)")
        print("4. It will be something like 'cr7f3_opportunity' or 'new_opportunity'")
        print("\nOnce you find it, we'll update the code to use that table name.")

        return None

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\nDynamics CRM Custom Opportunity Table Finder")
    print("This script will help identify your custom opportunity table.\n")

    custom_table = find_opportunity_tables()

    if custom_table and custom_table != 'opportunities':
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print(f"\n1. Add this to your environment variables:")
        print(f"   DYNAMICS_OPPORTUNITY_TABLE={custom_table}")
        print("\n2. The code will be updated to use this custom table name.")
        print("\n3. Test creating an opportunity again.")

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
