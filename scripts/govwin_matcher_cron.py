#!/usr/bin/env python
"""
GovWin Matcher Cron Job - Runs on Render as a scheduled job
Matches scored SAM opportunities with GovWin data

Search & Matching Strategy:
1. Fetch high-scoring SAM opportunities (fit_score >= 7)
2. For each SAM opportunity:
   - Search GovWin by title keywords (words > 4 chars)
   - Pre-filter results using:
     * Solicitation number matching (regex pattern)
     * Title similarity (60%+ threshold)
     * Keyword overlap (2+ matching words)
   - Fetch full GovWin details (with description) for matches passing pre-filter
3. AI evaluation (OpenAI):
   - Compare SAM vs GovWin using titles, descriptions, agencies, NAICS, dates
   - Score 0-100 with confidence level
   - Only record matches with score >= 70 and medium/high confidence
4. For confirmed matches:
   - Create GovWin opportunity record in database
   - Fetch and store related contracts
   - Create match record linking SAM <-> GovWin
"""
import os
import sys
import requests
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

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

# Pre-filter thresholds
TITLE_SIMILARITY_THRESHOLD = 0.6  # 60% similarity to pass pre-filter
MIN_KEYWORD_MATCHES = 2  # Minimum matching keywords (>4 chars)


def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity ratio between two titles (0.0 to 1.0)."""
    if not title1 or not title2:
        return 0.0
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def extract_solicitation_number(text: str) -> Optional[str]:
    """Extract solicitation/contract number patterns from text."""
    if not text:
        return None
    # Common patterns: alphanumeric with dashes/underscores
    # e.g., "FA8732-24-R-0001", "HSHQDC-24-Q-00123"
    pattern = r'\b[A-Z0-9]{2,}[-_][0-9]{2,}[-_][A-Z0-9][-_][0-9]+\b'
    match = re.search(pattern, text.upper())
    return match.group(0) if match else None


def prefilter_govwin_match(sam_opp: Dict[str, Any], govwin_opp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-filter GovWin opportunities to determine if they're worth sending to AI evaluation.

    Returns:
        Dict with 'pass' (bool), 'score' (0-100), and 'reasons' (list of str)
    """
    reasons = []
    score = 0

    sam_title = sam_opp.get('title', '').lower()
    govwin_title = govwin_opp.get('title', '').lower()
    sam_solicitation = sam_opp.get('solicitation_number', '')

    # Check 1: Solicitation number exact match (strong signal)
    if sam_solicitation:
        govwin_sol = extract_solicitation_number(govwin_title)
        if govwin_sol and sam_solicitation.upper() in govwin_sol.upper():
            score += 50
            reasons.append(f"Solicitation number match: {sam_solicitation}")

    # Check 2: Title similarity
    title_sim = calculate_title_similarity(sam_title, govwin_title)
    if title_sim >= TITLE_SIMILARITY_THRESHOLD:
        score += int(title_sim * 30)  # Up to 30 points
        reasons.append(f"Title similarity: {title_sim:.2%}")

    # Check 3: Keyword matching (words > 4 chars)
    sam_keywords = set([w for w in sam_title.split() if len(w) > 4])
    govwin_keywords = set([w for w in govwin_title.split() if len(w) > 4])
    matching_keywords = sam_keywords & govwin_keywords

    if len(matching_keywords) >= MIN_KEYWORD_MATCHES:
        score += min(len(matching_keywords) * 10, 20)  # Up to 20 points
        reasons.append(f"Matching keywords: {', '.join(list(matching_keywords)[:3])}")

    # Pass if score >= 40 (e.g., high title similarity OR solicitation match)
    passed = score >= 40

    return {
        'pass': passed,
        'score': score,
        'reasons': reasons
    }


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

        matches = []

        # Search by title keywords using 'q' parameter
        if title:
            # Extract key words from title (simple approach - words > 4 chars)
            keywords = ' '.join([word for word in title.split() if len(word) > 4])[:100]
            if keywords:
                logger.info(f"Searching GovWin with keywords: {keywords[:50]}...")
                try:
                    results = govwin_client.search_opportunities({
                        'q': keywords,  # Use 'q' not 'keyword'
                        'max': 10       # Use 'max' not 'limit'
                    })
                    # Extract opportunities from response
                    opportunities = results.get('opportunities', []) if isinstance(results, dict) else results
                    if opportunities:
                        logger.info(f"Found {len(opportunities)} opportunities from GovWin search")

                        # Pre-filter each opportunity
                        for opp in opportunities:
                            filter_result = prefilter_govwin_match(sam_opp, opp)

                            if filter_result['pass']:
                                # Fetch full opportunity details with description
                                # Use 'id' (with prefix like FBO4090400) not 'iqOppId' (just number)
                                govwin_id = opp.get('id') or opp.get('iqOppId')
                                try:
                                    full_opp = govwin_client.get_opportunity(govwin_id)
                                    logger.info(f"Pre-filter PASS (score: {filter_result['score']}): {govwin_id} - {filter_result['reasons']}")
                                    matches.append({
                                        'opportunity': full_opp,  # Use full details with description
                                        'search_strategy': 'title_keyword',
                                        'prefilter_score': filter_result['score'],
                                        'prefilter_reasons': filter_result['reasons']
                                    })
                                except Exception as e:
                                    logger.warning(f"Failed to fetch full details for {govwin_id}: {e}")
                                    # Fall back to basic opportunity data
                                    matches.append({
                                        'opportunity': opp,
                                        'search_strategy': 'title_keyword',
                                        'prefilter_score': filter_result['score'],
                                        'prefilter_reasons': filter_result['reasons']
                                    })
                            else:
                                govwin_id = opp.get('id') or opp.get('iqOppId')
                                govwin_title = opp.get('title', 'Unknown')[:50]
                                logger.debug(f"Pre-filter FAIL (score: {filter_result['score']}): {govwin_id} - {govwin_title}...")

                        logger.info(f"{len(matches)} opportunities passed pre-filter")
                except Exception as e:
                    logger.warning(f"Title keyword search failed: {e}")

        return matches

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

        # Extract GovWin description (may be in different fields)
        govwin_desc = ''
        if 'description' in govwin_opp:
            govwin_desc = govwin_opp.get('description', '')
        elif 'descriptionText' in govwin_opp:
            govwin_desc = govwin_opp.get('descriptionText', '')

        user_prompt = f"""Evaluate if these are the same opportunity:

SAM.gov Opportunity:
- Title: {sam_opp.get('title', 'N/A')}
- Notice ID: {sam_opp.get('notice_id', 'N/A')}
- Solicitation #: {sam_opp.get('solicitation_number', 'N/A')}
- Department: {sam_opp.get('department', 'N/A')}
- NAICS: {sam_opp.get('naics_code', 'N/A')}
- Posted: {sam_opp.get('posted_date', 'N/A')}
- Response Deadline: {sam_opp.get('response_deadline', 'N/A')}
- Description: {sam_opp.get('description', '')[:800]}

GovWin Opportunity:
- Title: {govwin_opp.get('title', 'N/A')}
- GovWin ID: {govwin_opp.get('iqOppId', govwin_opp.get('id', 'N/A'))}
- Agency: {govwin_opp.get('govEntity', {}).get('title', 'N/A') if isinstance(govwin_opp.get('govEntity'), dict) else 'N/A'}
- NAICS: {govwin_opp.get('primaryNAICS', {}).get('id', 'N/A') if isinstance(govwin_opp.get('primaryNAICS'), dict) else 'N/A'}
- Status: {govwin_opp.get('status', 'N/A')}
- Value: ${govwin_opp.get('oppValue', 0):,}
- Description: {govwin_desc[:800] if govwin_desc else 'N/A'}
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

                # Extract vendor information (company object in GovWin API)
                company = contract.get('company', {})
                vendor_name = None
                vendor_id = None

                if isinstance(company, dict):
                    vendor_name = company.get('name')
                    vendor_id = company.get('id')
                else:
                    # Fallback to direct fields
                    vendor_name = contract.get('vendorName') or contract.get('vendor_name')
                    vendor_id = contract.get('vendorId') or contract.get('vendor_id')

                # Extract contract value (estimatedValue in GovWin API)
                contract_value = (
                    contract.get('estimatedValue') or
                    contract.get('contractValue') or
                    contract.get('contract_value') or
                    contract.get('value')
                )

                # Extract expiration date
                expiration_date = contract.get('expirationDate') or contract.get('endDate') or contract.get('end_date')

                payload = {
                    "govwin_opportunity_id": govwin_db_id,  # Use database ID (int)
                    "contract_id": str(contract_id) if contract_id else None,
                    "contract_number": str(contract_number) if contract_number else None,
                    "title": contract.get('title'),
                    "vendor_name": vendor_name,
                    "vendor_id": str(vendor_id) if vendor_id else None,
                    "contract_value": contract_value,
                    "award_date": contract.get('awardDate') or contract.get('award_date'),
                    "start_date": contract.get('startDate') or contract.get('start_date'),
                    "end_date": expiration_date,
                    "status": "Incumbent" if contract.get('incumbent') in [True, 'true', '1', 1] else None,
                    "raw_data": json.dumps(contract)  # Store as JSON string
                }

                response = requests.post(
                    f"{BACKEND_API_URL}/api/govwin-contracts/",
                    json=payload,
                    timeout=30
                )

                # Handle validation errors with detailed logging
                if response.status_code == 422:
                    try:
                        error_detail = response.json()
                        logger.error(f"422 Validation error for contract {contract_id or contract_number}:")
                        logger.error(f"Payload sent: {json.dumps(payload, indent=2)}")
                        logger.error(f"Validation errors: {json.dumps(error_detail, indent=2)}")
                    except:
                        logger.error(f"422 Validation error response body: {response.text}")
                    continue  # Skip this contract and move to next

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
        # Use 'id' field with prefix (e.g., 'FBO4114983') for API calls
        # Use 'iqOppId' (numeric) for database storage
        govwin_id_prefixed = govwin_opp.get('id')  # e.g., 'FBO4114983'
        govwin_id_numeric = govwin_opp.get('iqOppId')  # e.g., 4114983

        if not govwin_id_prefixed and not govwin_id_numeric:
            raise ValueError("GovWin opportunity missing ID")

        # Convert numeric ID to string for database (schema expects string)
        govwin_id_str = str(govwin_id_numeric) if govwin_id_numeric else govwin_id_prefixed

        # Check if it already exists
        check_response = requests.get(
            f"{BACKEND_API_URL}/api/govwin-opportunities/govwin-id/{govwin_id_str}",
            timeout=30
        )

        if check_response.status_code == 200:
            logger.info(f"GovWin opportunity {govwin_id_str} already exists")
            existing_record = check_response.json()
            govwin_db_id = existing_record.get('id')

            # Still fetch contracts if requested, even for existing records
            if fetch_contracts and govwin_db_id:
                fetch_and_store_contracts(govwin_client, govwin_id_prefixed, govwin_db_id)

            return existing_record

        # Create new record
        import json
        payload = {
            "govwin_id": govwin_id_str,  # Must be string
            "title": govwin_opp.get('title', 'Unknown'),
            "raw_data": json.dumps(govwin_opp)  # Convert to JSON string
        }

        response = requests.post(
            f"{BACKEND_API_URL}/api/govwin-opportunities/",
            json=payload,
            timeout=30
        )

        # Handle validation errors with detailed logging
        if response.status_code == 422:
            try:
                error_detail = response.json()
                logger.error(f"422 Validation error for GovWin opportunity {govwin_id}:")
                logger.error(f"Payload sent: {json.dumps(payload, indent=2)}")
                logger.error(f"Validation errors: {json.dumps(error_detail, indent=2)}")
            except:
                logger.error(f"422 Validation error response body: {response.text}")
            raise requests.exceptions.HTTPError(f"422 Validation Error: {response.text[:200]}")

        response.raise_for_status()
        new_record = response.json()
        govwin_db_id = new_record.get('id')
        logger.info(f"Created GovWin opportunity record for {govwin_id_str} (DB ID: {govwin_db_id})")

        # Fetch and store related contracts using prefixed ID
        if fetch_contracts and govwin_db_id:
            fetch_and_store_contracts(govwin_client, govwin_id_prefixed, govwin_db_id)

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

        # Handle validation errors with detailed logging
        if response.status_code == 422:
            try:
                import json as json_lib
                error_detail = response.json()
                logger.error(f"422 Validation error creating match record:")
                logger.error(f"Payload sent: {json_lib.dumps(payload, indent=2)}")
                logger.error(f"Validation errors: {json_lib.dumps(error_detail, indent=2)}")
            except:
                logger.error(f"422 Validation error response body: {response.text}")
            return False

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
        try:
            govwin_client = GovWinClient(
                client_id=GOVWIN_CLIENT_ID,
                client_secret=GOVWIN_CLIENT_SECRET,
                username=GOVWIN_USERNAME,
                password=GOVWIN_PASSWORD
            )
        except ValueError as e:
            logger.error(f"GovWin authentication failed: {e}")
            logger.error("Please verify your GovWin credentials in the environment variables:")
            logger.error("  - GOVWIN_USERNAME")
            logger.error("  - GOVWIN_PASSWORD")
            logger.error("  - GOVWIN_CLIENT_ID")
            logger.error("  - GOVWIN_CLIENT_SECRET")
            return
        except Exception as e:
            logger.error(f"Failed to initialize GovWin client: {e}")
            return

        logger.info("Initializing OpenAI client...")
        openai_client = OpenAI(api_key=OPENAI_API_KEY)

        # Fetch high-scoring SAM opportunities (fit_score >= 7 out of 10)
        logger.info("Fetching high-scoring SAM opportunities...")
        response = requests.get(
            f"{BACKEND_API_URL}/api/sam-opportunities/?min_fit_score=7&limit=50",
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
                # Get numeric ID for display and database storage
                govwin_id_numeric = govwin_opp.get('iqOppId')
                govwin_id_prefixed = govwin_opp.get('id')
                govwin_id_for_display = govwin_id_numeric or govwin_id_prefixed

                logger.info(f"Evaluating match: {notice_id} <-> {govwin_id_for_display}")

                # Use AI to evaluate the match
                evaluation = evaluate_match_with_ai(openai_client, sam_opp, govwin_opp)

                if evaluation and evaluation.get('is_match'):
                    logger.info(f"Match found! Score: {evaluation.get('match_score')}, Confidence: {evaluation.get('confidence')}")

                    try:
                        # Create GovWin opportunity record and fetch related contracts
                        create_govwin_opportunity_record(govwin_client, govwin_opp, fetch_contracts=True)

                        # Create match record using string version of numeric ID
                        govwin_id_str = str(govwin_id_numeric) if govwin_id_numeric else govwin_id_prefixed
                        if create_match_record(notice_id, govwin_id_str, evaluation, search_strategy):
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
