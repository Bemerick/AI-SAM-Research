#!/usr/bin/env python
"""Quick script to test which opportunity table name is correct."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.dynamics_auth import get_access_token, DynamicsAuthConfig
from app.dynamics_client import DynamicsClient
import requests

config = DynamicsAuthConfig()
access_token = get_access_token()
client = DynamicsClient(resource_url=config.resource_url, access_token=access_token)

print("Testing table names...")
for table_name in ['new_Opportunity', 'new_opportunity', 'new_Opportunities', 'new_opportunities']:
    endpoint = f'{client.base_api_url}/{table_name}'
    response = requests.get(endpoint, headers=client._get_headers(), params={'$top': 1}, timeout=30)
    print(f'{table_name}: Status {response.status_code}')
    if response.status_code == 200:
        print(f'\n✓✓✓ CORRECT TABLE NAME: {table_name} ✓✓✓\n')
        print(f'Set this in Render environment:')
        print(f'DYNAMICS_OPPORTUNITY_TABLE={table_name}')
        break
