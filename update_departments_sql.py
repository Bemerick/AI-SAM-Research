"""
Script to update department names for existing opportunities in the database using SQL.

This script directly updates the database since the PATCH endpoint doesn't support
department field updates.
"""
import logging
from app.sam_client import SAMClient
from app.config import SAM_API_KEY
from backend.app.database import SessionLocal
from backend.app.models import SAMOpportunity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_departments_sql():
    """Update department names for all existing opportunities using SQL."""

    # Initialize SAM client and database session
    sam_client = SAMClient(api_key=SAM_API_KEY)
    db = SessionLocal()

    try:
        # Get all existing opportunities from database
        logger.info("Fetching existing opportunities from database...")
        opportunities = db.query(SAMOpportunity).all()
        logger.info(f"Found {len(opportunities)} opportunities to update")

        updated_count = 0
        error_count = 0

        for opp in opportunities:
            notice_id = opp.notice_id
            current_dept = opp.department
            opp_id = opp.id

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
                        # Update directly in database
                        opp.department = department
                        opp.standardized_department = department
                        db.commit()

                        logger.info(f"  ✓ Updated: {current_dept} → {department}")
                        updated_count += 1
                    else:
                        logger.info(f"  - No change needed: {department}")
                else:
                    logger.warning(f"  ✗ No data found in SAM.gov for {notice_id}")
                    error_count += 1

            except Exception as e:
                logger.error(f"  ✗ Error processing {notice_id}: {e}")
                db.rollback()
                error_count += 1
                continue

        logger.info("=" * 60)
        logger.info(f"Update complete:")
        logger.info(f"  - Total processed: {len(opportunities)}")
        logger.info(f"  - Successfully updated: {updated_count}")
        logger.info(f"  - Errors: {error_count}")
        logger.info(f"  - No change needed: {len(opportunities) - updated_count - error_count}")

    finally:
        db.close()

if __name__ == "__main__":
    update_departments_sql()
