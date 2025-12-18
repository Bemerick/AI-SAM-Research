#!/usr/bin/env python
"""Show ALL fields in new_opportunities table."""
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

metadata_table_name = 'new_opportunity'

print(f"All fields in {metadata_table_name}:")
print("=" * 80)

# Get entity metadata
endpoint = f"{client.base_api_url}/EntityDefinitions(LogicalName='{metadata_table_name}')"
params = {
    '$select': 'LogicalName,DisplayName,PrimaryNameAttribute',
    '$expand': 'Attributes($select=LogicalName,DisplayName,AttributeType,RequiredLevel)'
}

response = requests.get(endpoint, headers=client._get_headers(), params=params, timeout=30)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
    exit(1)

metadata = response.json()

print(f"\nPrimary Name Attribute: {metadata.get('PrimaryNameAttribute')}")
print("\nAll fields (filtered for likely opportunity fields):\n")

attributes = metadata.get('Attributes', [])

# Filter for fields that might be dates, probabilities, or other opportunity-related
keywords = ['date', 'close', 'probability', 'percent', 'value', 'amount', 'deadline', 'estimate']

for attr in sorted(attributes, key=lambda x: x.get('LogicalName', '')):
    logical_name = attr.get('LogicalName', '')

    # Skip system fields
    if logical_name.startswith('createdon') or logical_name.startswith('modifiedon') or logical_name.startswith('ownerid') or logical_name.startswith('owningbusinessunit') or logical_name.startswith('owningteam') or logical_name.startswith('owninguser'):
        continue

    # Show fields that match keywords
    if any(kw in logical_name.lower() for kw in keywords):
        display_label = attr.get('DisplayName')
        if display_label and display_label.get('UserLocalizedLabel'):
            display_name = display_label.get('UserLocalizedLabel').get('Label', 'N/A')
        else:
            display_name = 'N/A'
        attr_type = attr.get('AttributeType', 'N/A')
        required_level = attr.get('RequiredLevel')
        required = required_level.get('Value', 'None') if required_level else 'None'

        print(f"{logical_name:50} | {attr_type:15} | {display_name:30}")
