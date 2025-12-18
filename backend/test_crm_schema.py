#!/usr/bin/env python
"""
Test script to inspect Dynamics CRM opportunity entity schema.
This will help identify the correct field names for mapping.
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from dynamics_auth import get_access_token, DynamicsAuthConfig
from dynamics_client import DynamicsClient


def get_opportunity_metadata():
    """Retrieve opportunity entity metadata from Dynamics CRM."""
    config = DynamicsAuthConfig()

    print("=" * 80)
    print("DYNAMICS CRM CONFIGURATION CHECK")
    print("=" * 80)

    # Check configuration
    print(f"\nConfiguration Status:")
    print(f"  Tenant ID:     {'✓ Set' if config.tenant_id else '✗ Missing'}")
    print(f"  Client ID:     {'✓ Set' if config.client_id else '✗ Missing'}")
    print(f"  Client Secret: {'✓ Set' if config.client_secret else '✗ Missing'}")
    print(f"  Resource URL:  {config.resource_url or '✗ Missing'}")

    if not config.is_configured():
        print(f"\n❌ Configuration incomplete. Missing: {', '.join(config.get_missing_config())}")
        print("\nPlease set the following environment variables:")
        for var in config.get_missing_config():
            print(f"  {var}")
        return

    print(f"\n✓ Configuration complete")

    # Try to get access token
    print("\n" + "=" * 80)
    print("TESTING AUTHENTICATION")
    print("=" * 80)

    try:
        print("\nAttempting to acquire access token...")
        access_token = get_access_token()
        print("✓ Successfully acquired access token")
        print(f"  Token length: {len(access_token)} characters")
        print(f"  Token preview: {access_token[:50]}...")
    except Exception as e:
        print(f"❌ Failed to acquire access token: {str(e)}")
        return

    # Initialize CRM client
    print("\n" + "=" * 80)
    print("QUERYING OPPORTUNITY ENTITY METADATA")
    print("=" * 80)

    try:
        client = DynamicsClient(resource_url=config.resource_url, access_token=access_token)

        # Get entity metadata (simplified query without MaxLength)
        endpoint = f"{client.base_api_url}/EntityDefinitions(LogicalName='opportunity')"
        params = {
            '$select': 'LogicalName,DisplayName',
            '$expand': 'Attributes($select=LogicalName,DisplayName,AttributeType,RequiredLevel)'
        }

        print(f"\nFetching metadata from: {endpoint}")

        import requests
        response = requests.get(
            endpoint,
            headers=client._get_headers(),
            params=params,
            timeout=30
        )

        response.raise_for_status()
        metadata = response.json()

        print(f"\n✓ Successfully retrieved opportunity entity metadata")

        # Display entity info
        print(f"\nEntity: {metadata.get('LogicalName')}")
        print(f"Display Name: {metadata.get('DisplayName', {}).get('UserLocalizedLabel', {}).get('Label', 'N/A')}")

        # Get attributes
        attributes = metadata.get('Attributes', [])
        print(f"\nTotal Fields: {len(attributes)}")

        # Filter and display relevant fields
        print("\n" + "=" * 80)
        print("STANDARD OPPORTUNITY FIELDS")
        print("=" * 80)

        standard_fields = [
            'name', 'description', 'estimatedclosedate', 'closeprobability',
            'opportunityid', 'createdon', 'modifiedon', 'statecode', 'statuscode',
            'actualvalue', 'estimatedvalue', 'budgetamount', 'currentsituation',
            'customerneed', 'proposedsolution', 'pursuedecision', 'ownerid'
        ]

        print("\nKey Standard Fields:")
        for attr in sorted(attributes, key=lambda x: x.get('LogicalName', '')):
            logical_name = attr.get('LogicalName', '')
            if logical_name in standard_fields:
                display_name = attr.get('DisplayName', {}).get('UserLocalizedLabel', {}).get('Label', 'N/A')
                attr_type = attr.get('AttributeType', 'N/A')
                required = attr.get('RequiredLevel', {}).get('Value', 'None')
                max_length = attr.get('MaxLength', '')

                print(f"  {logical_name:30} | {display_name:30} | {attr_type:20} | Required: {required}")

        # Display custom fields
        print("\n" + "=" * 80)
        print("CUSTOM FIELDS (new_* prefix)")
        print("=" * 80)

        custom_fields = [attr for attr in attributes if attr.get('LogicalName', '').startswith('new_')]

        if custom_fields:
            print(f"\nFound {len(custom_fields)} custom fields:")
            for attr in sorted(custom_fields, key=lambda x: x.get('LogicalName', '')):
                logical_name = attr.get('LogicalName', '')
                display_name = attr.get('DisplayName', {}).get('UserLocalizedLabel', {}).get('Label', 'N/A')
                attr_type = attr.get('AttributeType', 'N/A')

                print(f"  {logical_name:40} | {display_name:30} | {attr_type}")
        else:
            print("\n⚠ No custom fields found with 'new_' prefix")
            print("  You may need to create custom fields in Dynamics CRM or use a different prefix")

        # Show recommendation
        print("\n" + "=" * 80)
        print("RECOMMENDED FIELD MAPPINGS")
        print("=" * 80)
        print("\nBased on your CRM schema, update map_sam_opportunity_to_crm() with:")
        print("\nStandard fields (always available):")
        print("  - name")
        print("  - description")
        print("  - estimatedclosedate")
        print("  - closeprobability")

        if custom_fields:
            print("\nYour custom fields:")
            for attr in sorted(custom_fields, key=lambda x: x.get('LogicalName', ''))[:10]:
                print(f"  - {attr.get('LogicalName', '')}")

    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        if e.response is not None:
            print(f"  Status Code: {e.response.status_code}")
            print(f"  Response: {e.response.text[:500]}")
    except Exception as e:
        print(f"\n❌ Error querying metadata: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nDynamics CRM Schema Inspector")
    print("This script will check your CRM configuration and list available opportunity fields.\n")

    get_opportunity_metadata()

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
