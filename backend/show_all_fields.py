#!/usr/bin/env python
"""Show all fields in new_opportunities table."""
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
    '$expand': 'Attributes($select=LogicalName,DisplayName,AttributeType,RequiredLevel;$filter=AttributeType eq Microsoft.Dynamics.CRM.AttributeTypeCode\'String\' or AttributeType eq Microsoft.Dynamics.CRM.AttributeTypeCode\'Memo\')'
}

response = requests.get(endpoint, headers=client._get_headers(), params=params, timeout=30)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
    exit(1)

metadata = response.json()

print(f"\nPrimary Name Attribute: {metadata.get('PrimaryNameAttribute')}")
print("\nAll String/Memo fields:\n")

attributes = metadata.get('Attributes', [])
for attr in sorted(attributes, key=lambda x: x.get('LogicalName', '')):
    logical_name = attr.get('LogicalName', '')
    display_label = attr.get('DisplayName')
    if display_label and display_label.get('UserLocalizedLabel'):
        display_name = display_label.get('UserLocalizedLabel').get('Label', 'N/A')
    else:
        display_name = 'N/A'
    attr_type = attr.get('AttributeType', 'N/A')
    required_level = attr.get('RequiredLevel')
    required = required_level.get('Value', 'None') if required_level else 'None'

    if 'name' in logical_name.lower() or 'title' in logical_name.lower():
        marker = " <<<< LIKELY NAME FIELD"
    else:
        marker = ""

    print(f"{logical_name:50} | {attr_type:10} | {display_name:30}{marker}")
