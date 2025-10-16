#!/usr/bin/env python
"""
GovWin Matcher Cron Job - Runs on Render as a scheduled job
Matches scored SAM opportunities with GovWin data
"""
import os
import sys
import requests
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to Python path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.govwin_client import GovWinClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
GOVWIN_USERNAME = os.getenv('GOVWIN_USERNAME')
GOVWIN_PASSWORD = os.getenv('GOVWIN_PASSWORD')
GOVWIN_CLIENT_ID = os.getenv('GOVWIN_CLIENT_ID')
GOVWIN_CLIENT_SECRET = os.getenv('GOVWIN_CLIENT_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def search_govwin_for_opportunity(govwin_client: GovWinClient, sam_opp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Search GovWin for opportunities similar to the given SAM opportunity.

    Args:
        govwin_client: Authenticated GovWin client
        sam_opp: SAM opportunity data

    Returns:
        List of potential GovWin matches
    """
    try:
        # Extract search criteria from SAM opportunity
        title = sam_opp.get('title', '')
        description = sam_opp.get('description', '')
        naics_code = sam_opp.get('naics_code')

        # Try multiple search strategies
        matches = []

        # Strategy 1: Search by title keywords
        if title:
            # Extract key words from title (simple approach)
            keywords = ' '.join([word for word in title.split() if len(word) > 4])[:100]
            if keywords:
                logger.info(f"Searching GovWin with keywords: {keywords[:50]}...")
                try:
                    results = govwin_client.search_opportunities({
                        'keyword': keywords,
                        'limit': 10
                    })
                    if results and 'opportunities' in results:
                        for opp in results['opportunities']:
                            matches.append({
                                'opportunity': opp,
                                'search_strategy': 'title_keyword'
                            })
                except Exception as e:
                    logger.warning(f"Title keyword search failed: {e}")

        # Strategy 2: Search by NAICS code
        if naics_code and naics_code != 'N/A':
            logger.info(f"Searching GovWin by NAICS: {naics_code}")
            try:
                results = govwin_client.search_opportunities({
                    'naics': naics_code,
                    'limit': 10
                })
                if results and 'opportunities' in results:
                    for opp in results['opportunities']:
                        matches.append({
                            'opportunity': opp,
                            'search_strategy': 'naics_code'
                        })
            except Exception as e:
                logger.warning(f"NAICS search failed: {e}")

        # Deduplicate matches by GovWin ID
        unique_matches = {}
        for match in matches:
            opp_id = match['opportunity'].get('iqOppId') or match['opportunity'].get('id')
            if opp_id and opp_id not in unique_matches:
                unique_matches[opp_id] = match

        return list(unique_matches.values())

    except Exception as e:
        logger.error(f"Error searching GovWin: {e}")
        return []


def evaluate_match_with_ai(openai_client: OpenAI, sam_opp: Dict[str, Any], govwin_opp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Use OpenAI to evaluate if a SAM and GovWin opportunity are a match.

    Args:
        openai_client: OpenAI client
        sam_opp: SAM opportunity data
        govwin_opp: GovWin opportunity data

    Returns:
        Match evaluation with score and reasoning, or None if not a match
    """
    try:
        system_prompt = """You are a government contracting expert. Your task is to evaluate whether two opportunities from different sources (SAM.gov and GovWin) represent the same procurement opportunity.

Consider:
- Title similarity
- Description/scope similarity
- Agency/department match
- NAICS code match
- Timeline alignment
- Dollar value alignment

Provide a match score from 0-100:
- 0-30: Not a match
- 31-60: Possible match, needs review
- 61-85: Likely match
- 86-100: Definite match

Respond in JSON format with:
{
    "is_match": true/false,
    "match_score": <0-100>,
    "reasoning": "<brief explanation>",
    "confidence": "<low/medium/high>"
}"""

        user_prompt = f"""Evaluate if these are the same opportunity:

SAM.gov Opportunity:
- Title: {sam_opp.get('title', 'N/A')}
- Notice ID: {sam_opp.get('notice_id', 'N/A')}
- Department: {sam_opp.get('department', 'N/A')}
- NAICS: {sam_opp.get('naics_code', 'N/A')}
- Posted: {sam_opp.get('posted_date', 'N/A')}
- Response Deadline: {sam_opp.get('response_date', 'N/A')}
- Description: {sam_opp.get('description', '')[:500]}

GovWin Opportunity:
- Title: {govwin_opp.get('title', 'N/A')}
- GovWin ID: {govwin_opp.get('iqOppId', govwin_opp.get('id', 'N/A'))}
- Agency: {govwin_opp.get('govEntity', {}).get('title', 'N/A') if isinstance(govwin_opp.get('govEntity'), dict) else 'N/A'}
- NAICS: {govwin_opp.get('primaryNAICS', {}).get('id', 'N/A') if isinstance(govwin_opp.get('primaryNAICS'), dict) else 'N/A'}
- Status: {govwin_opp.get('status', 'N/A')}
- Value: ${govwin_opp.get('oppValue', 0):,}
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        result = response.choices[0].message.content
        import json
        evaluation = json.loads(result)

        # Only return matches with score >= 31 (possible match or better)
        if evaluation.get('match_score', 0) >= 31:
            return evaluation

        return None

    except Exception as e:
        logger.error(f"Error evaluating match with AI: {e}")
        return None


def fetch_and_store_contracts(govwin_client: GovWinClient, govwin_id: str, govwin_db_id: int) -> int:
    """
    Fetch related contracts for a GovWin opportunity and store them.

    Args:
        govwin_client: Authenticated GovWin client
        govwin_id: GovWin opportunity string ID (e.g., 'OPP123456')
        govwin_db_id: Database internal ID for the GovWin opportunity

    Returns:
        Number of contracts created
    """
    try:
        logger.info(f"Fetching contracts for GovWin opportunity {govwin_id}...")
        contracts = govwin_client.get_opportunity_contracts(govwin_id)

        if not contracts:
            logger.info(f"No contracts found for {govwin_id}")
            return 0

        logger.info(f"Found {len(contracts)} contracts for {govwin_id}")
        created_count = 0

        for contract in contracts:
            contract_id = contract.get('id') or contract.get('contractId')
            contract_number = contract.get('contractNumber') or contract.get('contract_number')

            if not contract_id and not contract_number:
                logger.warning(f"Contract missing ID and number, skipping: {contract.get('title', 'Unknown')[:50]}")
                continue

            try:
                # Extract contract fields
                import json
                payload = {
                    "govwin_opportunity_id": govwin_db_id,  # Use database ID
                    "contract_id": contract_id,
                    "contract_number": contract_number,
                    "title": contract.get('title'),
                    "vendor_name": contract.get('vendorName') or contract.get('vendor_name'),
                    "vendor_id": contract.get('vendorId') or contract.get('vendor_id'),
                    "contract_value": contract.get('contractValue') or contract.get('contract_value') or contract.get('value'),
                    "award_date": contract.get('awardDate') or contract.get('award_date'),
                    "start_date": contract.get('startDate') or contract.get('start_date'),
                    "end_date": contract.get('endDate') or contract.get('end_date'),
                    "raw_data": json.dumps(contract)  # Store as JSON string
                }

                response = requests.post(
                    f"{BACKEND_API_URL}/api/govwin-contracts/",
                    json=payload,
                    timeout=30
                )

                if response.status_code == 201:
                    created_count += 1
                    logger.info(f"Created contract record: {contract_id or contract_number}")
                elif response.status_code == 200:
                    logger.info(f"Contract {contract_id or contract_number} already exists")
                else:
                    response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400 and 'already exists' in e.response.text.lower():
                    logger.info(f"Contract {contract_id or contract_number} already exists")
                else:
                    logger.error(f"Error creating contract {contract_id or contract_number}: {e}")
            except Exception as e:
                logger.error(f"Error creating contract {contract_id or contract_number}: {e}")

        logger.info(f"Created {created_count} new contract records for {govwin_id}")
        return created_count

    except Exception as e:
        logger.error(f"Error fetching contracts for {govwin_id}: {e}")
        return 0


def create_govwin_opportunity_record(govwin_client: GovWinClient, govwin_opp: Dict[str, Any], fetch_contracts: bool = True) -> Dict[str, Any]:
    """
    Create a GovWin opportunity record via the backend API.

    Args:
        govwin_client: Authenticated GovWin client
        govwin_opp: GovWin opportunity data
        fetch_contracts: Whether to fetch and store related contracts

    Returns:
        Created opportunity record
    """
    try:
        govwin_id = govwin_opp.get('iqOppId') or govwin_opp.get('id')
        if not govwin_id:
            raise ValueError("GovWin opportunity missing ID")

        # Check if it already exists
        check_response = requests.get(
            f"{BACKEND_API_URL}/api/govwin-opportunities/govwin-id/{govwin_id}",
            timeout=30
        )

        if check_response.status_code == 200:
            logger.info(f"GovWin opportunity {govwin_id} already exists")
            existing_record = check_response.json()
            govwin_db_id = existing_record.get('id')

            # Still fetch contracts if requested, even for existing records
            if fetch_contracts and govwin_db_id:
                fetch_and_store_contracts(govwin_client, govwin_id, govwin_db_id)

            return existing_record

        # Create new record
        import json
        payload = {
            "govwin_id": govwin_id,
            "title": govwin_opp.get('title', 'Unknown'),
            "raw_data": json.dumps(govwin_opp)  # Convert to JSON string
        }

        response = requests.post(
            f"{BACKEND_API_URL}/api/govwin-opportunities/",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        new_record = response.json()
        govwin_db_id = new_record.get('id')
        logger.info(f"Created GovWin opportunity record for {govwin_id} (DB ID: {govwin_db_id})")

        # Fetch and store related contracts
        if fetch_contracts and govwin_db_id:
            fetch_and_store_contracts(govwin_client, govwin_id, govwin_db_id)

        return new_record

    except Exception as e:
        logger.error(f"Error creating GovWin opportunity record: {e}")
        raise


def create_match_record(sam_notice_id: str, govwin_id: str, evaluation: Dict[str, Any], search_strategy: str) -> bool:
    """
    Create a match record via the backend API.

    Args:
        sam_notice_id: SAM opportunity notice ID
        govwin_id: GovWin opportunity ID
        evaluation: AI match evaluation
        search_strategy: How the match was found

    Returns:
        True if successful
    """
    try:
        # Determine status based on match score
        match_score = evaluation.get('match_score', 0)
        if match_score >= 86:
            status = 'confirmed'
        elif match_score >= 61:
            status = 'pending_review'
        else:
            status = 'pending_review'

        payload = {
            "sam_notice_id": sam_notice_id,
            "govwin_id": govwin_id,
            "search_strategy": search_strategy,
            "match_score": match_score,
            "match_notes": evaluation.get('reasoning', ''),
            "status": status
        }

        response = requests.post(
            f"{BACKEND_API_URL}/api/matches/from-external-ids",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        logger.info(f"Created match record: SAM {sam_notice_id} <-> GovWin {govwin_id} (score: {match_score})")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400 and 'already exists' in e.response.text.lower():
            logger.info(f"Match already exists: SAM {sam_notice_id} <-> GovWin {govwin_id}")
            return True
        logger.error(f"Error creating match record: {e}")
        return False
    except Exception as e:
        logger.error(f"Error creating match record: {e}")
        return False


def main():
    logger.info("=" * 80)
    logger.info(f"GovWin Matcher Cron Job started at {datetime.now()}")
    logger.info("=" * 80)

    # Validate credentials
    if not all([GOVWIN_USERNAME, GOVWIN_PASSWORD, GOVWIN_CLIENT_ID, GOVWIN_CLIENT_SECRET]):
        logger.warning("GovWin credentials not configured. Skipping GovWin matcher.")
        logger.warning("To enable, set: GOVWIN_USERNAME, GOVWIN_PASSWORD, GOVWIN_CLIENT_ID, GOVWIN_CLIENT_SECRET")
        logger.info("=" * 80)
        logger.info(f"GovWin Matcher completed (skipped) at {datetime.now()}")
        logger.info("=" * 80)
        return

    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set. Skipping GovWin matcher.")
        logger.info("=" * 80)
        logger.info(f"GovWin Matcher completed (skipped) at {datetime.now()}")
        logger.info("=" * 80)
        return

    try:
        # Initialize clients
        logger.info("Initializing GovWin client...")
        govwin_client = GovWinClient(
            client_id=GOVWIN_CLIENT_ID,
            client_secret=GOVWIN_CLIENT_SECRET,
            username=GOVWIN_USERNAME,
            password=GOVWIN_PASSWORD
        )

        logger.info("Initializing OpenAI client...")
        openai_client = OpenAI(api_key=OPENAI_API_KEY)

        # Fetch high-scoring SAM opportunities without matches
        logger.info("Fetching high-scoring SAM opportunities...")
        response = requests.get(
            f"{BACKEND_API_URL}/api/sam-opportunities/?min_fit_score=70&limit=50",
            timeout=30
        )
        response.raise_for_status()
        opportunities = response.json()

        logger.info(f"Found {len(opportunities)} high-scoring opportunities to process")

        match_count = 0
        govwin_search_count = 0

        # Process each SAM opportunity
        for sam_opp in opportunities:
            notice_id = sam_opp.get('notice_id')
            title = sam_opp.get('title', 'Unknown')

            logger.info(f"\nProcessing SAM opportunity: {notice_id} - {title[:60]}...")

            # Search GovWin for potential matches
            potential_matches = search_govwin_for_opportunity(govwin_client, sam_opp)
            govwin_search_count += 1

            if not potential_matches:
                logger.info(f"No GovWin matches found for {notice_id}")
                continue

            logger.info(f"Found {len(potential_matches)} potential GovWin matches")

            # Evaluate each potential match with AI
            for match_data in potential_matches:
                govwin_opp = match_data['opportunity']
                search_strategy = match_data['search_strategy']
                govwin_id = govwin_opp.get('iqOppId') or govwin_opp.get('id')

                logger.info(f"Evaluating match: {notice_id} <-> {govwin_id}")

                # Use AI to evaluate the match
                evaluation = evaluate_match_with_ai(openai_client, sam_opp, govwin_opp)

                if evaluation and evaluation.get('is_match'):
                    logger.info(f"Match found! Score: {evaluation.get('match_score')}, Confidence: {evaluation.get('confidence')}")

                    try:
                        # Create GovWin opportunity record and fetch related contracts
                        create_govwin_opportunity_record(govwin_client, govwin_opp, fetch_contracts=True)

                        # Create match record
                        if create_match_record(notice_id, govwin_id, evaluation, search_strategy):
                            match_count += 1
                    except Exception as e:
                        logger.error(f"Error recording match: {e}")
                else:
                    logger.info(f"Not a match (score: {evaluation.get('match_score', 0) if evaluation else 0})")

        logger.info(f"\nProcessed {len(opportunities)} SAM opportunities")
        logger.info(f"Performed {govwin_search_count} GovWin searches")
        logger.info(f"Created {match_count} new matches")

    except Exception as e:
        logger.error(f"Error in GovWin matcher: {e}", exc_info=True)
        raise

    logger.info("=" * 80)
    logger.info(f"GovWin Matcher completed at {datetime.now()}")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
