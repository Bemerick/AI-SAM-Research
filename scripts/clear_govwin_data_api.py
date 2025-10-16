#!/usr/bin/env python
"""
Clear GovWin matches, opportunities, and contracts via the backend API.
This allows you to rerun the GovWin matcher cron job with fresh data.

Usage:
    python scripts/clear_govwin_data_api.py --confirm
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:8000')

def clear_govwin_data(skip_confirmation=False):
    """Clear all GovWin-related data via the backend API."""
    print(f"Using backend: {BACKEND_API_URL}")

    try:
        # Get all GovWin opportunities
        print("Fetching GovWin opportunities...")
        response = requests.get(f"{BACKEND_API_URL}/api/govwin-opportunities/?limit=1000", timeout=30)
        response.raise_for_status()
        govwin_opps = response.json()

        print(f"Found {len(govwin_opps)} GovWin opportunities")

        if len(govwin_opps) == 0:
            print("No GovWin data to clear!")
            return

        # Confirm deletion
        if not skip_confirmation:
            try:
                response_text = input("\nAre you sure you want to delete all GovWin opportunities, matches, and contracts? (yes/no): ")
                if response_text.lower() != 'yes':
                    print("Cancelled.")
                    return
            except EOFError:
                print("\nError: Cannot get user input. Use --confirm flag to skip confirmation.")
                return
        else:
            print("\nSkipping confirmation (--confirm flag provided)")

        # Delete each GovWin opportunity (cascade will delete related matches and contracts)
        print("\nDeleting GovWin opportunities (and related matches/contracts)...")
        deleted_count = 0

        for opp in govwin_opps:
            opp_id = opp.get('id')
            govwin_id = opp.get('govwin_id')

            try:
                response = requests.delete(
                    f"{BACKEND_API_URL}/api/govwin-opportunities/{opp_id}",
                    timeout=30
                )

                if response.status_code == 204:
                    deleted_count += 1
                    print(f"✓ Deleted GovWin opportunity {govwin_id} (ID: {opp_id})")
                else:
                    print(f"✗ Failed to delete {govwin_id}: {response.status_code}")

            except Exception as e:
                print(f"✗ Error deleting {govwin_id}: {e}")

        print(f"\n✅ Successfully deleted {deleted_count}/{len(govwin_opps)} GovWin opportunities!")
        print("Related matches and contracts were automatically deleted due to cascade rules.")
        print("\nYou can now rerun the GovWin matcher cron job.")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error fetching data from backend: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

if __name__ == "__main__":
    # Check for --confirm flag
    skip_confirmation = '--confirm' in sys.argv
    clear_govwin_data(skip_confirmation=skip_confirmation)
