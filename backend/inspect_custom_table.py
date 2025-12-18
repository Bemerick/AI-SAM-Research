#!/usr/bin/env python
"""Inspect the custom opportunity table schema."""
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

# Try different table name variations
table_names = ['new_opportunity', 'new_opportuntiy', 'new_opportunities']
table_name = None

print("Finding correct table name...")
print("=" * 80)

# First find which table name works
for tn in table_names:
    test_endpoint = f"{client.base_api_url}/{tn}"
    test_response = requests.get(test_endpoint, headers=client._get_headers(), params={'$top': 1}, timeout=30)
    print(f"Testing {tn}: {test_response.status_code}")
    if test_response.status_code == 200:
        table_name = tn
        print(f"✓ Found table: {table_name}\n")
        break

if not table_name:
    print("\nCouldn't find the table. Please check DYNAMICS_OPPORTUNITY_TABLE setting.")
    exit(1)

# Now get the metadata using the singular form
# Handle "opportunities" -> "opportunity" (ies -> y)
if table_name.endswith('ies'):
    metadata_table_name = table_name[:-3] + 'y'
else:
    metadata_table_name = table_name.rstrip('s')

print(f"Inspecting schema for: {table_name} (metadata name: {metadata_table_name})")
print("=" * 80)

# Get entity metadata
endpoint = f"{client.base_api_url}/EntityDefinitions(LogicalName='{metadata_table_name}')"
params = {
    '$select': 'LogicalName,DisplayName',
    '$expand': 'Attributes($select=LogicalName,DisplayName,AttributeType,RequiredLevel)'
}

response = requests.get(endpoint, headers=client._get_headers(), params=params, timeout=30)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
    exit(1)

metadata = response.json()
attributes = metadata.get('Attributes', [])

print(f"\nTotal fields: {len(attributes)}")

# Look for customer/account related fields
print("\n" + "=" * 80)
print("CUSTOMER/ACCOUNT RELATED FIELDS:")
print("=" * 80)

customer_fields = [a for a in attributes if 'customer' in a.get('LogicalName', '').lower() or 'account' in a.get('LogicalName', '').lower()]

if customer_fields:
    for attr in customer_fields:
        logical_name = attr.get('LogicalName', '')
        display_label = attr.get('DisplayName')
        if display_label and display_label.get('UserLocalizedLabel'):
            display_name = display_label.get('UserLocalizedLabel').get('Label', 'N/A')
        else:
            display_name = 'N/A'
        attr_type = attr.get('AttributeType', 'N/A')
        required_level = attr.get('RequiredLevel')
        required = required_level.get('Value', 'None') if required_level else 'None'
        print(f"\nField: {logical_name}")
        print(f"  Display Name: {display_name}")
        print(f"  Type: {attr_type}")
        print(f"  Required: {required}")
else:
    print("\nNo customer/account fields found.")

# Look for lookup fields (which could be the customer reference)
print("\n" + "=" * 80)
print("ALL LOOKUP FIELDS (Potential Customer Fields):")
print("=" * 80)

lookup_fields = [a for a in attributes if a.get('AttributeType') == 'Lookup']

for attr in lookup_fields[:20]:  # Show first 20
    logical_name = attr.get('LogicalName', '')
    display_label = attr.get('DisplayName')
    if display_label and display_label.get('UserLocalizedLabel'):
        display_name = display_label.get('UserLocalizedLabel').get('Label', 'N/A')
    else:
        display_name = 'N/A'
    print(f"\nField: {logical_name}")
    print(f"  Display Name: {display_name}")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)

if customer_fields:
    print("\nLikely customer field(s):")
    for attr in customer_fields:
        print(f"  - {attr.get('LogicalName')}")
else:
    print("\nNo obvious customer field found.")
    print("Check the lookup fields above for a field that references Account.")
    print("\nTo associate with an account, you may need to:")
    print("1. Create a lookup field to the Account table in your custom opportunity")
    print("2. Or remove the customer assignment from the code if not needed")
