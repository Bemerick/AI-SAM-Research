#!/usr/bin/env python
"""
SAM Fetcher Cron Job - Runs on Render as a scheduled job
Fetches SAM.gov opportunities and stores them in the database
"""
import os
import sys
import requests
import logging
from datetime import datetime

# Add parent directory to Python path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sam_client import SAMClient
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
SAM_API_KEY = os.getenv('SAM_API_KEY')
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
GOVWIN_USERNAME = os.getenv('GOVWIN_USERNAME')
GOVWIN_PASSWORD = os.getenv('GOVWIN_PASSWORD')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# NAICS codes to search
NAICS_CODES = [
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
    "541513",  # Computer Facilities Management Services
    "541519",  # Other Computer Related Services
    "541611",  # Administrative Management Consulting
    "541618",  # Other Management Consulting Services
]


def fetch_sam_opportunities(naics_code: str):
    """Fetch opportunities from SAM.gov for a specific NAICS code"""
    try:
        from datetime import timedelta

        client = SAMClient(api_key=SAM_API_KEY)

        # Only fetch opportunities posted in the last 2 days to avoid duplicates
        # Using 2 days instead of 1 to account for timezone differences
        posted_from = datetime.now() - timedelta(days=2)
        posted_to = datetime.now()

        result = client.search_opportunities(
            naics_code=naics_code,
            posted_from=posted_from,
            posted_to=posted_to,
            limit=100,
            include_description=True
        )
        opportunities = result.get('opportunitiesData', [])
        logger.info(f"Fetched {len(opportunities)} opportunities for NAICS {naics_code}")
        return opportunities
    except Exception as e:
        logger.error(f"Error fetching SAM.gov opportunities for NAICS {naics_code}: {e}")
        return []


def store_opportunity(opp):
    """Store opportunity in database via backend API"""
    try:
        # Extract nested fields with null safety
        place_of_performance = opp.get("placeOfPerformance") or {}
        city_data = place_of_performance.get("city") or {}
        state_data = place_of_performance.get("state") or {}
        point_of_contact = opp.get("pointOfContact") or []
        primary_contact = point_of_contact[0] if point_of_contact else {}

        # Prepare opportunity data
        opportunity_data = {
            "notice_id": opp.get("noticeId"),
            "title": opp.get("title"),
            "department": opp.get("fullParentPathName"),
            "standardized_department": opp.get("fullParentPathName"),
            "naics_code": opp.get("naicsCode"),
            "full_parent_path": opp.get("fullParentPathName"),
            "fit_score": 0.0,  # Unscored initially
            "posted_date": opp.get("postedDate"),
            "response_deadline": opp.get("responseDeadLine"),
            "solicitation_number": opp.get("solicitationNumber"),
            "description": opp.get("descriptionText") or opp.get("description", ""),
            "summary_description": "",
            "type": opp.get("type"),
            "ptype": opp.get("type"),
            "classification_code": opp.get("classificationCode"),
            "set_aside": opp.get("typeOfSetAsideDescription") or opp.get("typeOfSetAside"),
            "place_of_performance_city": city_data.get("name") if isinstance(city_data, dict) else None,
            "place_of_performance_state": state_data.get("code") if isinstance(state_data, dict) else None,
            "place_of_performance_zip": place_of_performance.get("zip"),
            "point_of_contact_email": primary_contact.get("email"),
            "point_of_contact_name": primary_contact.get("fullName"),
            "sam_link": opp.get("uiLink"),
            "assigned_practice_area": None,
            "justification": None,
        }

        # POST to backend API
        response = requests.post(
            f"{BACKEND_API_URL}/api/sam-opportunities/",
            json=opportunity_data,
            timeout=30
        )

        if response.status_code == 400:
            # Log the validation error details
            try:
                error_detail = response.json()
                logger.error(f"Validation error for {opportunity_data['notice_id']}: {error_detail}")
            except:
                logger.error(f"400 error for {opportunity_data['notice_id']}: {response.text}")

        response.raise_for_status()
        logger.info(f"Stored opportunity: {opportunity_data['notice_id']}")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            # Duplicate - this is expected, not an error
            logger.debug(f"Opportunity {opp.get('noticeId')} already exists (duplicate)")
            return True
        logger.error(f"Error storing opportunity {opp.get('noticeId')}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error storing opportunity {opp.get('noticeId')}: {e}")
        return False


def main():
    """Main function to run SAM fetcher cron job"""
    logger.info("=" * 80)
    logger.info(f"SAM Fetcher Cron Job started at {datetime.now()}")
    logger.info("=" * 80)

    total_opportunities = 0
    total_stored = 0

    for naics_code in NAICS_CODES:
        logger.info(f"\nProcessing NAICS code: {naics_code}")
        opportunities = fetch_sam_opportunities(naics_code)
        total_opportunities += len(opportunities)

        for opp in opportunities:
            if opp.get("noticeId"):
                if store_opportunity(opp):
                    total_stored += 1

    logger.info("=" * 80)
    logger.info(f"SAM Fetcher Cron Job completed at {datetime.now()}")
    logger.info(f"Total opportunities fetched: {total_opportunities}")
    logger.info(f"Total opportunities stored: {total_stored}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
