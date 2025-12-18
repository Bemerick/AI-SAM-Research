#!/usr/bin/env python
"""
Test script to create and verify a CRM opportunity.
This will help diagnose why opportunities aren't appearing in CRM.

Usage:
  From repository root: python backend/test_crm_opportunity.py
  From backend directory: python test_crm_opportunity.py
"""
import sys
import os
from dotenv import load_dotenv
from datetime import datetime

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
from app.dynamics_client import DynamicsClient, map_sam_opportunity_to_crm


def test_create_opportunity():
    """Test creating an opportunity and verify it exists."""
    config = DynamicsAuthConfig()

    print("=" * 80)
    print("DYNAMICS CRM OPPORTUNITY CREATION TEST")
    print("=" * 80)

    # Check configuration
    if not config.is_configured():
        print(f"\n❌ Configuration incomplete. Missing: {', '.join(config.get_missing_config())}")
        return

    print("\n✓ Configuration complete")

    # Get access token
    try:
        print("\nAcquiring access token...")
        access_token = get_access_token()
        print("✓ Successfully acquired access token")
    except Exception as e:
        print(f"❌ Failed to acquire access token: {str(e)}")
        return

    # Initialize CRM client
    client = DynamicsClient(resource_url=config.resource_url, access_token=access_token)

    # Create test opportunity data
    test_opportunity = {
        'title': f'TEST OPPORTUNITY - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        'notice_id': 'TEST-12345',
        'department': 'Test Department',
        'solicitation_number': 'TEST-SOL-001',
        'naics_code': '541512',
        'response_deadline': '2025-03-15',
        'posted_date': '2025-01-15',
        'fit_score': 8,
        'assigned_practice_area': 'IT Services',
        'justification': 'This is a test opportunity created for diagnostic purposes.',
        'summary_description': 'Test opportunity to verify CRM integration.',
        'sam_link': 'https://sam.gov/test',
        'set_aside': 'Small Business',
        'ptype': 'Combined Synopsis/Solicitation'
    }

    print("\n" + "=" * 80)
    print("CREATING TEST OPPORTUNITY")
    print("=" * 80)

    try:
        # Map SAM data to CRM format
        crm_data = map_sam_opportunity_to_crm(test_opportunity)

        print("\nMapped CRM Data:")
        for key, value in crm_data.items():
            print(f"  {key}: {value if len(str(value)) < 100 else str(value)[:100] + '...'}")

        # Create opportunity in CRM
        print("\nSending to CRM...")
        result = client.create_opportunity(crm_data)

        print("\n✓ Opportunity created successfully!")
        print(f"\nCRM Response:")
        print(f"  CRM ID: {result.get('crm_id')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Message: {result.get('message')}")

        crm_id = result.get('crm_id')

        if crm_id and crm_id != 'mock-crm-id-12345':
            # Try to retrieve the opportunity to verify it exists
            print("\n" + "=" * 80)
            print("VERIFYING OPPORTUNITY IN CRM")
            print("=" * 80)

            try:
                print(f"\nRetrieving opportunity {crm_id}...")
                retrieved_opp = client.get_opportunity(crm_id)

                print("\n✓ Opportunity verified in CRM!")
                print(f"\nRetrieved Data:")
                print(f"  Name: {retrieved_opp.get('name')}")
                print(f"  Opportunity ID: {retrieved_opp.get('opportunityid')}")
                print(f"  Status: {retrieved_opp.get('statecode')} / {retrieved_opp.get('statuscode')}")
                print(f"  Owner ID: {retrieved_opp.get('_ownerid_value')}")
                print(f"  Customer ID: {retrieved_opp.get('_customerid_value', 'NOT SET')}")
                print(f"  Created On: {retrieved_opp.get('createdon')}")

                # Check if customer is set
                if not retrieved_opp.get('_customerid_value'):
                    print("\n⚠️  WARNING: No customer (Account/Contact) is set!")
                    print("   This may cause the opportunity to be hidden in some views.")
                    print("   Consider adding a customer relationship.")

                # Provide direct link
                print(f"\n🔗 Direct CRM Link:")
                print(f"   {config.resource_url}/main.aspx?etn=opportunity&id={crm_id}&pagetype=entityrecord")

            except Exception as e:
                print(f"\n⚠️  Could not retrieve opportunity: {str(e)}")
                print("   The opportunity may have been created but there might be a permission issue.")

        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("\n1. Check the direct CRM link above")
        print("2. In Dynamics 365, go to Sales > Opportunities")
        print("3. Try these view filters:")
        print("   - 'All Opportunities' view")
        print("   - 'My Open Opportunities' view")
        print("   - Check if you need to change the view owner")
        print("4. Check the 'Owner' field - the opportunity might be assigned to a service account")
        print("5. Verify the opportunity has a 'Potential Customer' (Account/Contact) set")

    except Exception as e:
        print(f"\n❌ Error creating opportunity: {str(e)}")
        import traceback
        traceback.print_exc()


def list_recent_opportunities():
    """List recent opportunities to verify creation."""
    config = DynamicsAuthConfig()

    if not config.is_configured():
        print("Configuration not complete")
        return

    try:
        access_token = get_access_token()
        client = DynamicsClient(resource_url=config.resource_url, access_token=access_token)

        print("\n" + "=" * 80)
        print("RECENT OPPORTUNITIES IN CRM")
        print("=" * 80)

        # Search for recent opportunities (last 7 days)
        filters = {
            '$select': 'opportunityid,name,createdon,_ownerid_value,_customerid_value,statecode',
            '$orderby': 'createdon desc',
            '$top': 10
        }

        opportunities = client.search_opportunities(filters)

        print(f"\nFound {len(opportunities)} recent opportunities:\n")

        for opp in opportunities:
            print(f"Name: {opp.get('name')}")
            print(f"  ID: {opp.get('opportunityid')}")
            print(f"  Created: {opp.get('createdon')}")
            print(f"  Customer: {opp.get('_customerid_value', 'NOT SET')}")
            print(f"  Owner: {opp.get('_ownerid_value')}")
            print()

    except Exception as e:
        print(f"Error listing opportunities: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nDynamics CRM Opportunity Test")
    print("This script will create a test opportunity and verify it in CRM.\n")

    test_create_opportunity()

    print("\n" + "=" * 80)
    print("Would you like to list recent opportunities? (This may help find your records)")
    print("=" * 80)

    list_recent_opportunities()

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
