#!/usr/bin/env python
"""
AI Analyzer Cron Job - Runs on Render as a scheduled job
Analyzes unscored SAM opportunities and assigns practice areas
"""
import os
import sys
import requests
import logging
import time
from datetime import datetime

# Add parent directory to Python path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.openai_analyzer import OpportunityAnalyzer
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BATCH_SIZE = 3  # Process 3 opportunities at a time (reduced to save tokens and processing time)

# Retry configuration for backend API
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 5  # seconds
MAX_RETRY_DELAY = 60  # seconds


def wait_for_backend_ready(max_wait_seconds: int = 300) -> bool:
    """
    Wait for the backend API to become available.

    Args:
        max_wait_seconds: Maximum time to wait in seconds (default 5 minutes)

    Returns:
        True if backend is ready, False if timeout
    """
    start_time = time.time()
    retry_delay = INITIAL_RETRY_DELAY

    logger.info(f"Checking if backend API is ready at {BACKEND_API_URL}...")

    while time.time() - start_time < max_wait_seconds:
        try:
            # Try to connect to the health endpoint or root
            response = requests.get(f"{BACKEND_API_URL}/health", timeout=10)
            if response.status_code == 200:
                logger.info("Backend API is ready!")
                return True
        except requests.exceptions.RequestException:
            # Try root endpoint as fallback
            try:
                response = requests.get(f"{BACKEND_API_URL}/", timeout=10)
                if response.status_code in [200, 404]:  # 404 is ok, means server is up
                    logger.info("Backend API is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass

        elapsed = int(time.time() - start_time)
        remaining = int(max_wait_seconds - elapsed)
        logger.info(f"Backend not ready yet. Waiting {retry_delay}s... ({elapsed}s elapsed, {remaining}s remaining)")
        time.sleep(retry_delay)

        # Exponential backoff with cap
        retry_delay = min(retry_delay * 1.5, MAX_RETRY_DELAY)

    logger.error(f"Backend API did not become ready within {max_wait_seconds}s")
    return False


def make_api_request(method: str, url: str, **kwargs) -> requests.Response:
    """
    Make an API request with retry logic for connection errors.

    Args:
        method: HTTP method ('GET', 'POST', etc.)
        url: Full URL to request
        **kwargs: Additional arguments to pass to requests (json, timeout, etc.)

    Returns:
        Response object

    Raises:
        requests.exceptions.RequestException: If all retries fail
    """
    retry_delay = INITIAL_RETRY_DELAY
    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30

            response = requests.request(method, url, **kwargs)
            return response

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout) as e:
            last_exception = e

            if attempt < MAX_RETRIES - 1:
                logger.warning(f"API request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                logger.info(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, MAX_RETRY_DELAY)
            else:
                logger.error(f"API request failed after {MAX_RETRIES} attempts: {e}")
                raise
        except requests.exceptions.RequestException as e:
            # For other HTTP errors (4xx, 5xx), don't retry
            raise

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def transform_opportunity_for_analyzer(opp):
    """
    Transform API response format to the format expected by the analyzer.
    The analyzer expects SAM.gov API format (camelCase), but our API returns snake_case.
    Note: _standardize_opportunity does opportunity.copy() which preserves original fields,
    so we need to provide the camelCase SAM.gov format here.
    """
    return {
        # SAM.gov API format (camelCase) - required by the analyzer
        'noticeId': opp.get('notice_id'),  # Critical: used for ID matching
        'title': opp.get('title'),
        'fullParentPathName': opp.get('full_parent_path', ''),
        'type': opp.get('type', ''),
        'naicsCode': opp.get('naics_code', ''),
        'typeOfSetAsideDescription': opp.get('set_aside', ''),
        'setAside': opp.get('set_aside', ''),
        'responseDeadLine': opp.get('response_deadline', ''),
        'postedDate': opp.get('posted_date', ''),
        'solicitationNumber': opp.get('solicitation_number', ''),
        'classificationCode': opp.get('classification_code', ''),
        'descriptionText': opp.get('description', ''),
        'description': opp.get('description', ''),
        'uiLink': opp.get('sam_link', '') if opp.get('sam_link') else 'N/A',
        # Keep our database ID for mapping results back
        '_db_id': opp.get('id'),
        '_db_notice_id': opp.get('notice_id')
    }


def analyze_batch(analyzer, batch):
    """Analyze a batch of opportunities using OpenAI"""
    try:
        # Transform opportunities to expected format
        transformed_batch = [transform_opportunity_for_analyzer(opp) for opp in batch]

        # Create mapping of notice_id to db_id for later
        notice_id_to_db_id = {
            opp['_db_notice_id']: opp['_db_id']
            for opp in transformed_batch
            if opp.get('_db_notice_id') and opp.get('_db_id')
        }

        logger.info(f"Analyzing batch of {len(transformed_batch)} opportunities...")

        # Analyze the batch with timeout protection
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Batch analysis timed out after 6 minutes")

        # Set a 6-minute timeout (slightly longer than OpenAI's 5-minute timeout)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(360)  # 6 minutes

        try:
            result = analyzer.analyze_opportunities(transformed_batch, output_format="json")
        finally:
            signal.alarm(0)  # Cancel the alarm

        # Extract and map results back to database IDs
        analyses = {}
        ranked_opps = result.get('ranked_opportunities', [])

        for analyzed in ranked_opps:
            notice_id = analyzed.get('notice_id')
            if notice_id and notice_id in notice_id_to_db_id:
                db_id = notice_id_to_db_id[notice_id]
                analyses[db_id] = {
                    'fit_score': analyzed.get('fit_score', 0),
                    'assigned_practice_area': analyzed.get('assigned_practice_area'),
                    'justification': analyzed.get('justification'),
                    'summary_description': analyzed.get('summary_description', analyzed.get('description', ''))
                }
                logger.info(f"Analyzed {notice_id} (DB ID: {db_id}): score={analyzed.get('fit_score')}, area={analyzed.get('assigned_practice_area')}")
            else:
                logger.warning(f"Could not map analyzed opportunity with notice_id={notice_id} back to database")

        # Check for unranked opportunities
        unranked = result.get('unranked_opportunities', [])
        if unranked:
            logger.info(f"{len(unranked)} opportunities were marked as unrankable")
            for unranked_opp in unranked:
                logger.debug(f"Unranked: {unranked_opp.get('notice_id')} - {unranked_opp.get('title', 'Unknown')[:50]}")

        return analyses

    except TimeoutError as e:
        logger.error(f"Batch analysis timed out: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error analyzing batch: {e}", exc_info=True)
        return {}


def update_opportunity(opp_id, analysis_data):
    """Update opportunity via backend API with retry logic"""
    try:
        response = make_api_request(
            'PATCH',
            f"{BACKEND_API_URL}/api/sam-opportunities/{opp_id}/",
            json=analysis_data
        )

        if response.status_code == 500:
            # Log server error details
            logger.error(f"500 Server Error updating opportunity {opp_id}: {response.text[:200]}")
            return False

        response.raise_for_status()
        logger.info(f"Updated opportunity {opp_id} with analysis")
        return True

    except Exception as e:
        logger.error(f"Error updating opportunity {opp_id}: {e}")
        return False


def main():
    logger.info("=" * 80)
    logger.info(f"AI Analyzer Cron Job started at {datetime.now()}")
    logger.info("=" * 80)

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set, cannot analyze opportunities")
        return

    # Wait for backend API to be ready (important for cron jobs where web service may still be starting)
    if not wait_for_backend_ready(max_wait_seconds=300):
        logger.error("Backend API is not available. Exiting.")
        return

    try:
        # Initialize analyzer
        analyzer = OpportunityAnalyzer(openai_api_key=OPENAI_API_KEY)

        # Fetch unscored opportunities (fit_score = 0 or NULL)
        logger.info("Fetching unscored opportunities from backend...")
        try:
            response = make_api_request(
                'GET',
                f"{BACKEND_API_URL}/api/sam-opportunities/unscored?limit=100",
                timeout=90
            )
            response.raise_for_status()
            opportunities = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch opportunities from backend: {e}")
            return

        logger.info(f"Found {len(opportunities)} unscored opportunities (fit_score = 0 or NULL)")

        if not opportunities:
            logger.info("No opportunities to analyze")
            return

        analyzed_count = 0
        updated_count = 0

        # Process in batches
        for i in range(0, len(opportunities), BATCH_SIZE):
            batch = opportunities[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(opportunities) + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"\n{'='*60}")
            logger.info(f"Processing batch {batch_num}/{total_batches}")
            logger.info(f"{'='*60}")

            # Analyze the batch
            analyses = analyze_batch(analyzer, batch)

            # Update each opportunity with its analysis
            for db_id, analysis in analyses.items():
                if analysis:
                    analyzed_count += 1
                    if update_opportunity(db_id, analysis):
                        updated_count += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzed {analyzed_count} opportunities")
        logger.info(f"Updated {updated_count} opportunities")
        logger.info(f"{'='*60}")

    except Exception as e:
        logger.error(f"Error in AI analyzer: {e}", exc_info=True)
        raise

    logger.info("=" * 80)
    logger.info(f"AI Analyzer completed at {datetime.now()}")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
