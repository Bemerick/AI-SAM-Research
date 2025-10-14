"""
Script to update department names for existing opportunities in the database.

This script re-fetches opportunities from SAM.gov and updates the department field
for all existing records.
"""
import requests
import logging
from app.sam_client import SAMClient
from app.config import SAM_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_API_URL = "http://localhost:8000/api"

def update_departments():
    """Update department names for all existing opportunities."""

    # Initialize SAM client
    sam_client = SAMClient(api_key=SAM_API_KEY)

    # Get all existing opportunities from database
    logger.info("Fetching existing opportunities from database...")
    response = requests.get(f"{BACKEND_API_URL}/sam-opportunities/")

    if response.status_code != 200:
        logger.error(f"Failed to fetch opportunities: {response.status_code}")
        return

    opportunities = response.json()
    logger.info(f"Found {len(opportunities)} opportunities to update")

    updated_count = 0
    error_count = 0

    for opp in opportunities:
        notice_id = opp.get('notice_id')
        current_dept = opp.get('department', 'N/A')
        opp_id = opp.get('id')

        logger.info(f"Processing {notice_id} (ID: {opp_id}) - Current dept: {current_dept}")

        try:
            # Fetch fresh data from SAM.gov
            result = sam_client.get_opportunity_by_id(notice_id, include_description=False)

            if result.get('opportunitiesData'):
                sam_opp = result['opportunitiesData'][0]

                # Extract department from fullParentPathName
                full_path = sam_opp.get('fullParentPathName', '')
                if full_path:
                    dept_path = full_path.split('.')
                    if dept_path:
                        department = dept_path[0].strip().upper()
                    else:
                        department = 'N/A'
                else:
                    department = 'N/A'

                # Only update if department changed
                if department != current_dept:
                    # Update via API
                    update_payload = {
                        "department": department,
                        "standardized_department": department
                    }

                    update_response = requests.patch(
                        f"{BACKEND_API_URL}/sam-opportunities/{opp_id}",
                        json=update_payload,
                        headers={"Content-Type": "application/json"}
                    )

                    if update_response.status_code == 200:
                        logger.info(f"  ✓ Updated: {current_dept} → {department}")
                        updated_count += 1
                    else:
                        logger.error(f"  ✗ Failed to update: {update_response.status_code}")
                        error_count += 1
                else:
                    logger.info(f"  - No change needed: {department}")
            else:
                logger.warning(f"  ✗ No data found in SAM.gov for {notice_id}")
                error_count += 1

        except Exception as e:
            logger.error(f"  ✗ Error processing {notice_id}: {e}")
            error_count += 1
            continue

    logger.info("=" * 60)
    logger.info(f"Update complete:")
    logger.info(f"  - Total processed: {len(opportunities)}")
    logger.info(f"  - Successfully updated: {updated_count}")
    logger.info(f"  - Errors: {error_count}")
    logger.info(f"  - No change needed: {len(opportunities) - updated_count - error_count}")

if __name__ == "__main__":
    update_departments()
