"""
End-to-End Workflow for SAM.gov Opportunity Management System

This script orchestrates the complete workflow:
1. Fetch opportunities from SAM.gov posted TODAY or YESTERDAY
2. Searches ALL predefined company NAICS codes (or specified subset)
3. Analyze and score them with AI
4. Store them in the database via API
5. For high-scoring opportunities, search GovWin for matches (optional)
6. Use AI to evaluate and score GovWin matches (optional)
7. Display results in frontend

DATE LOGIC:
- By default, automatically determines whether to fetch today's or yesterday's opportunities
- If run before 10 AM: fetches YESTERDAY's opportunities
- If run after 10 AM: fetches TODAY's opportunities
- Can be overridden with --today or --yesterday flags

NAICS CODES:
- By default, searches ALL company NAICS codes defined in app/config.py
- Can specify specific codes with --naics flag

Usage:
    # Run with auto date detection (all NAICS codes)
    python run_end_to_end_workflow.py

    # Force yesterday's opportunities
    python run_end_to_end_workflow.py --yesterday

    # Force today's opportunities
    python run_end_to_end_workflow.py --today

    # Specific NAICS codes only
    python run_end_to_end_workflow.py --naics 541512 541519

    # With keyword filtering
    python run_end_to_end_workflow.py --keywords "cloud" "AI" "data"

    # Save results to file
    python run_end_to_end_workflow.py --output results.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests

# Import our existing modules
from app.sam_client import SAMClient
from app.openai_analyzer import OpportunityAnalyzer
from app.config import SAM_API_KEY, OPENAI_API_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Configuration
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")

class EndToEndWorkflow:
    """Orchestrates the complete end-to-end workflow"""

    def __init__(self):
        self.sam_client = SAMClient(api_key=SAM_API_KEY)
        self.analyzer = OpportunityAnalyzer(openai_api_key=OPENAI_API_KEY)
        self.backend_api = BACKEND_API_URL
        self.govwin_client = None  # Lazy load GovWin client when needed

    def _get_govwin_client(self):
        """Lazy load GovWin client to avoid unnecessary authentication."""
        if self.govwin_client is None:
            from app.govwin_client import GovWinClient
            from app.config import GOVWIN_USERNAME, GOVWIN_PASSWORD
            self.govwin_client = GovWinClient(username=GOVWIN_USERNAME, password=GOVWIN_PASSWORD)
        return self.govwin_client

    def get_existing_notice_ids(self) -> set:
        """
        Fetch all existing notice IDs from the database to check for duplicates

        Returns:
            Set of existing notice IDs
        """
        try:
            logger.info("Fetching existing notice IDs from database...")
            response = requests.get(f"{self.backend_api}/sam-opportunities/")

            if response.status_code == 200:
                existing_opps = response.json()
                existing_notice_ids = {opp.get('notice_id') for opp in existing_opps if opp.get('notice_id')}
                logger.info(f"Found {len(existing_notice_ids)} existing notice IDs in database")
                return existing_notice_ids
            else:
                logger.warning(f"Failed to fetch existing opportunities: {response.status_code}")
                return set()

        except Exception as e:
            logger.error(f"Error fetching existing notice IDs: {e}")
            return set()

    def fetch_sam_opportunities(self,
                                naics_code: str = None,
                                keywords: List[str] = None,
                                use_yesterday: bool = False,
                                search_date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch opportunities from SAM.gov posted on a specific date

        Args:
            naics_code: NAICS code to filter by
            keywords: Keywords to search in title
            use_yesterday: If True, fetch yesterday's opportunities; if False, fetch today's
            search_date: Specific date to search (format: MM/DD/YYYY). Overrides use_yesterday.

        Returns:
            List of opportunity dictionaries
        """
        # Determine the date to search
        if search_date:
            target_date = search_date
            date_label = search_date
        elif use_yesterday:
            target_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')
            date_label = "yesterday"
        else:
            target_date = datetime.now().strftime('%m/%d/%Y')
            date_label = "today"

        logger.info(f"Fetching SAM.gov opportunities for {date_label} ({target_date}) - NAICS: {naics_code}")

        try:
            # Search for opportunities posted on the target date only
            result = self.sam_client.search_opportunities(
                naics_code=naics_code,
                posted_from=target_date,
                posted_to=target_date,
                limit=100,
                include_description=True
            )

            opportunities = result.get('opportunitiesData', [])
            logger.info(f"Fetched {len(opportunities)} opportunities from SAM.gov for {date_label}")

            # Filter by keywords if provided
            if keywords:
                filtered = []
                for opp in opportunities:
                    title = opp.get('title', '').lower()
                    if any(keyword.lower() in title for keyword in keywords):
                        filtered.append(opp)
                logger.info(f"Filtered to {len(filtered)} opportunities matching keywords: {keywords}")
                return filtered

            return opportunities

        except Exception as e:
            logger.error(f"Error fetching SAM.gov opportunities: {e}")
            raise

    def analyze_and_score_opportunities(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use AI to analyze and score opportunities

        Args:
            opportunities: List of raw SAM.gov opportunities

        Returns:
            Dictionary with ranked_opportunities, unranked_opportunities, and usage
        """
        logger.info(f"Analyzing {len(opportunities)} opportunities with AI...")

        try:
            result = self.analyzer.analyze_opportunities(opportunities, output_format='json')

            ranked = result.get('ranked_opportunities', [])
            unranked = result.get('unranked_opportunities', [])
            usage = result.get('usage', {})

            logger.info(f"AI Analysis complete: {len(ranked)} ranked, {len(unranked)} unranked")
            logger.info(f"Token usage: {usage}")

            return result

        except Exception as e:
            logger.error(f"Error analyzing opportunities: {e}")
            raise

    def store_opportunities_in_database(self, ranked_opportunities: List[Dict[str, Any]]) -> List[int]:
        """
        Store opportunities in database via API

        Args:
            ranked_opportunities: List of analyzed opportunities

        Returns:
            List of created opportunity IDs
        """
        logger.info(f"Storing {len(ranked_opportunities)} opportunities in database...")

        created_ids = []

        for opp in ranked_opportunities:
            try:
                # Map the analyzed opportunity to the database schema
                # Note: SAM API uses camelCase, we need to handle both raw SAM data and AI-enriched data
                payload = {
                    "notice_id": opp.get('notice_id') or opp.get('noticeId'),
                    "title": opp.get('title'),
                    "department": opp.get('department') or opp.get('fullParentPathName'),
                    "standardized_department": opp.get('standardized_department') or opp.get('department') or opp.get('fullParentPathName'),
                    "naics_code": opp.get('naics_code') or opp.get('naicsCode'),
                    "fit_score": float(opp.get('fit_score', 0)),
                    "posted_date": opp.get('posted_date') or opp.get('postedDate'),
                    "response_deadline": opp.get('response_deadline') or opp.get('response_date') or opp.get('responseDeadLine'),
                    "solicitation_number": opp.get('solicitation_number') or opp.get('solicitationNumber'),
                    "description": (opp.get('descriptionText') or opp.get('description', ''))[:1000],  # Truncate if too long
                    "summary_description": opp.get('summary_description', ''),
                    "ptype": opp.get('ptype') or opp.get('type'),
                    "set_aside": opp.get('set_aside') or opp.get('typeOfSetAside'),
                    "assigned_practice_area": opp.get('assigned_practice_area', 'Uncategorized'),
                    "justification": opp.get('justification', ''),
                    "sam_link": opp.get('sam_link') or opp.get('uiLink')
                }

                response = requests.post(
                    f"{self.backend_api}/sam-opportunities/",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 201:
                    created = response.json()
                    created_ids.append(created['id'])
                    logger.info(f"Created opportunity ID {created['id']}: {opp.get('title', 'N/A')[:50]}")
                else:
                    logger.warning(f"Failed to create opportunity {opp.get('notice_id')}: {response.status_code} - {response.text}")

            except Exception as e:
                logger.error(f"Error storing opportunity {opp.get('notice_id')}: {e}")
                continue

        logger.info(f"Successfully stored {len(created_ids)} opportunities")
        return created_ids

    def search_govwin_for_opportunity(self, sam_opportunity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search GovWin for matches to a SAM opportunity using multiple search strategies.

        Args:
            sam_opportunity: SAM opportunity dictionary

        Returns:
            List of GovWin opportunity matches (deduplicated)
        """
        title = sam_opportunity.get('title', '')
        department = sam_opportunity.get('department', '')
        solicitation_number = sam_opportunity.get('solicitationNumber', '')

        logger.info(f"Searching GovWin for: {title[:60]}...")

        try:
            govwin_client = self._get_govwin_client()
            all_matches = []
            seen_ids = set()

            # Strategy 1: Search by title keywords using 'q' parameter
            # GovWin API supports 'q' for general text search
            title_keywords = self._extract_keywords(title)
            if title_keywords:
                logger.info(f"  Strategy 1: Searching by title keywords: {title_keywords[:100]}")
                try:
                    response = govwin_client.search_opportunities({'q': title_keywords})
                    results = response.get('opportunities', []) if isinstance(response, dict) else []
                    for result in results[:10]:  # Limit to top 10
                        gw_id = result.get('id')
                        if gw_id and gw_id not in seen_ids:
                            all_matches.append(result)
                            seen_ids.add(gw_id)
                    logger.info(f"    Found {len(results)} matches")
                except Exception as e:
                    logger.warning(f"    Title search failed: {e}")

            # Strategy 2: Search by department/agency keywords
            if department and department != 'N/A' and not all_matches:
                # Clean up department name for search
                agency_name = department.split(',')[0].strip()  # Get main department name
                agency_name = agency_name.replace('DEPARTMENT OF THE', '').replace('DEPARTMENT OF', '').strip()

                if agency_name and len(agency_name) > 3:  # Avoid searching for too short names
                    logger.info(f"  Strategy 2: Searching by agency keywords: {agency_name}")
                    try:
                        response = govwin_client.search_opportunities({'q': agency_name})
                        results = response.get('opportunities', []) if isinstance(response, dict) else []
                        for result in results[:20]:  # More results since agency is broad
                            gw_id = result.get('id')
                            if gw_id and gw_id not in seen_ids:
                                all_matches.append(result)
                                seen_ids.add(gw_id)
                        logger.info(f"    Found {len(results)} matches")
                    except Exception as e:
                        logger.warning(f"    Agency search failed: {e}")

            # Strategy 3: Search by solicitation number (most specific)
            if solicitation_number and solicitation_number != 'N/A':
                logger.info(f"  Strategy 3: Searching by solicitation number: {solicitation_number}")
                try:
                    # Try exact solicitation number using 'q' parameter
                    response = govwin_client.search_opportunities({'q': solicitation_number})
                    results = response.get('opportunities', []) if isinstance(response, dict) else []
                    for result in results[:5]:
                        gw_id = result.get('id')
                        if gw_id and gw_id not in seen_ids:
                            all_matches.append(result)
                            seen_ids.add(gw_id)
                    logger.info(f"    Found {len(results)} matches")
                except Exception as e:
                    logger.warning(f"    Solicitation number search failed: {e}")

            logger.info(f"  Total unique GovWin matches found: {len(all_matches)}")
            return all_matches

        except Exception as e:
            logger.error(f"Error searching GovWin: {e}")
            return []

    def _extract_keywords(self, title: str) -> str:
        """
        Extract meaningful keywords from a title for searching.
        Removes common words and keeps important terms.

        Args:
            title: Opportunity title

        Returns:
            Filtered keywords string
        """
        # Common words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'for', 'of', 'to', 'in', 'on', 'at',
            'services', 'service', 'support', 'solicitation', 'notice', 'request',
            'sources', 'intent', 'award', 'contract', 'procurement'
        }

        # Split and filter
        words = title.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]

        # Take top meaningful keywords (limit to avoid too broad search)
        return ' '.join(keywords[:5])  # Max 5 keywords

    def evaluate_govwin_matches(self, sam_opportunity: Dict[str, Any], govwin_opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use AI to evaluate and score GovWin matches against a SAM opportunity.

        Uses OpenAI to:
        1. Determine if they're the same opportunity
        2. Calculate match confidence score (0-10)
        3. Identify potential teaming opportunities
        4. Store best matches in database

        Args:
            sam_opportunity: SAM opportunity dictionary
            govwin_opportunities: List of GovWin opportunities

        Returns:
            List of evaluated and scored matches that were stored in database
        """
        if not govwin_opportunities:
            return []

        logger.info(f"Evaluating {len(govwin_opportunities)} GovWin matches with AI...")

        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)

            # Prepare SAM opportunity summary for AI
            sam_summary = {
                'title': sam_opportunity.get('title', 'N/A'),
                'department': sam_opportunity.get('department', 'N/A'),
                'solicitation_number': sam_opportunity.get('solicitationNumber', 'N/A'),
                'posted_date': sam_opportunity.get('posted_date', 'N/A'),
                'response_deadline': sam_opportunity.get('response_date', 'N/A'),
                'naics_code': sam_opportunity.get('naics_code', 'N/A'),
                'description': sam_opportunity.get('summary_description', '')[:500]  # Limit description
            }

            # Prepare GovWin opportunities summaries
            govwin_summaries = []
            for gw_opp in govwin_opportunities[:10]:  # Limit to top 10 to save tokens
                govwin_summaries.append({
                    'id': gw_opp.get('id', 'N/A'),
                    'title': gw_opp.get('title', 'N/A'),
                    'agency': gw_opp.get('agencyName', 'N/A'),
                    'description': gw_opp.get('description', '')[:300]  # Limit description
                })

            # AI prompt for matching
            prompt = f"""You are a federal contracting expert analyzing opportunity matches between SAM.gov and GovWin.

SAM.gov Opportunity:
{json.dumps(sam_summary, indent=2)}

Potential GovWin Matches:
{json.dumps(govwin_summaries, indent=2)}

For each GovWin opportunity, determine:
1. **Match Confidence Score (0-10)**: How confident are you this is the same opportunity or related?
   - 9-10: Definitely the same opportunity (matching solicitation numbers, titles, agencies)
   - 7-8: Very likely the same (similar titles, agencies, timeframes)
   - 5-6: Possibly related (same agency, similar topic)
   - 3-4: Loosely related (same agency or topic but different focus)
   - 0-2: Not related

2. **Match Type**:
   - "same_opportunity": This is the exact same procurement
   - "related_opportunity": Related but different procurement
   - "teaming_opportunity": Different but good teaming potential
   - "not_related": No meaningful relationship

3. **Reasoning**: Brief explanation (1-2 sentences) why you scored it this way

Only include GovWin opportunities with match_confidence >= 5.0 in your response.

Return JSON format:
{{
  "matches": [
    {{
      "govwin_id": "OPP12345",
      "match_confidence": 8.5,
      "match_type": "same_opportunity",
      "reasoning": "Same solicitation number and agency, very likely the same procurement.",
      "teaming_potential": "high/medium/low"
    }}
  ]
}}"""

            # Call OpenAI
            logger.info("  Sending to OpenAI for match evaluation...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a federal contracting expert. Analyze opportunity matches and return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent matching
                response_format={"type": "json_object"}
            )

            ai_response = json.loads(response.choices[0].message.content)
            matches = ai_response.get('matches', [])

            logger.info(f"  AI found {len(matches)} quality matches (confidence >= 5.0)")

            # Store matches in database
            stored_matches = []
            for match in matches:
                try:
                    # Prepare match payload for new API endpoint
                    match_payload = {
                        "sam_notice_id": sam_opportunity.get('notice_id'),
                        "govwin_id": match['govwin_id'],
                        "search_strategy": "ai_matching",
                        "match_score": float(match['match_confidence']),
                        "match_notes": f"{match['match_type']} - {match['reasoning']}",
                        "status": "pending_review"
                    }

                    # Store via new API endpoint that handles external IDs
                    response = requests.post(
                        f"{self.backend_api}/matches/from-external-ids",
                        json=match_payload,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 201:
                        stored_match = response.json()
                        stored_matches.append(stored_match)
                        logger.info(f"    ✓ Stored match: {match['govwin_id']} (score: {match['match_confidence']})")
                    else:
                        logger.warning(f"    ✗ Failed to store match {match['govwin_id']}: {response.status_code} - {response.text}")

                except Exception as e:
                    logger.error(f"    ✗ Error storing match {match.get('govwin_id')}: {e}")
                    continue

            logger.info(f"  Successfully stored {len(stored_matches)} matches in database")

            # Fetch and store contracts for each match
            self.fetch_and_store_contracts(stored_matches)

            return stored_matches

        except Exception as e:
            logger.error(f"Error evaluating GovWin matches: {e}", exc_info=True)
            return []

    def fetch_and_store_contracts(self, stored_matches: List[Dict[str, Any]]) -> None:
        """
        Fetch and store contract information for GovWin matches.

        Args:
            stored_matches: List of matches that were successfully stored
        """
        if not stored_matches:
            return

        logger.info(f"  Fetching contracts for {len(stored_matches)} matches...")

        for match in stored_matches:
            try:
                # Get the GovWin opportunity ID from the match
                govwin_opp_id = match.get('govwin_opportunity', {}).get('govwin_id')
                if not govwin_opp_id:
                    continue

                # Fetch contracts from GovWin API
                contracts_data = self.govwin_client.get_opportunity_contracts(govwin_opp_id)

                if not contracts_data:
                    logger.info(f"    No contracts found for {govwin_opp_id}")
                    continue

                logger.info(f"    Found {len(contracts_data)} contracts for {govwin_opp_id}")

                # Store each contract in the database
                govwin_db_id = match.get('govwin_opportunity', {}).get('id')
                for contract_data in contracts_data:
                    try:
                        # Extract vendor information from company array or vendor object
                        vendor_name = None
                        vendor_id = None
                        if 'company' in contract_data and contract_data['company']:
                            # company is an array
                            vendor_name = contract_data['company'][0].get('name') if contract_data['company'] else None
                            vendor_id = str(contract_data['company'][0].get('id')) if contract_data['company'] else None
                        elif 'vendor' in contract_data:
                            if isinstance(contract_data['vendor'], dict):
                                vendor_name = contract_data['vendor'].get('name')
                                vendor_id = str(contract_data['vendor'].get('id'))
                            else:
                                vendor_name = contract_data.get('vendorName')
                                vendor_id = contract_data.get('vendorId')

                        contract_payload = {
                            "govwin_opportunity_id": govwin_db_id,
                            "contract_id": str(contract_data.get('id')) if contract_data.get('id') else None,
                            "contract_number": contract_data.get('contractNumber'),
                            "title": contract_data.get('title'),
                            "vendor_name": vendor_name,
                            "vendor_id": vendor_id,
                            "contract_value": contract_data.get('value') or contract_data.get('contractValue'),
                            "award_date": contract_data.get('awardDate'),
                            "start_date": contract_data.get('startDate'),
                            "end_date": contract_data.get('expirationDate') or contract_data.get('endDate'),
                            "status": contract_data.get('status'),
                            "contract_type": contract_data.get('type') or contract_data.get('contractType'),
                            "description": contract_data.get('description'),
                            "raw_data": json.dumps(contract_data)
                        }

                        # Store contract via backend API
                        response = requests.post(
                            f"{self.backend_api}/govwin-contracts",
                            json=contract_payload,
                            headers={"Content-Type": "application/json"}
                        )

                        if response.status_code == 201:
                            logger.info(f"      ✓ Stored contract: {contract_payload.get('contract_number', 'N/A')}")
                        else:
                            logger.warning(f"      ✗ Failed to store contract: {response.status_code}")

                    except Exception as e:
                        logger.error(f"      ✗ Error storing contract: {e}")
                        continue

            except Exception as e:
                logger.error(f"    Error fetching contracts for match: {e}")
                continue

    def run_workflow(self,
                     naics_codes: List[str] = None,
                     keywords: List[str] = None,
                     use_yesterday: bool = False,
                     search_date: str = None,
                     skip_govwin: bool = False) -> Dict[str, Any]:
        """
        Run the complete end-to-end workflow

        Args:
            naics_codes: List of NAICS codes to search (defaults to COMPANY_NAICS_CODES from config)
            keywords: Keywords to search
            use_yesterday: If True, fetch yesterday's opportunities; if False, fetch today's
            search_date: Specific date to search (format: MM/DD/YYYY). Overrides use_yesterday.
            skip_govwin: Skip GovWin integration

        Returns:
            Summary of workflow execution
        """
        from app.config import COMPANY_NAICS_CODES

        # Use predefined NAICS codes if none provided
        if not naics_codes:
            naics_codes = COMPANY_NAICS_CODES

        # Determine which date to use
        if search_date:
            # Use the specific date provided
            date_label = search_date
            use_yesterday = None  # Not applicable when using specific date
        else:
            current_hour = datetime.now().hour
            if use_yesterday is None:
                # Auto-determine: If before 10 AM, use yesterday; otherwise use today
                use_yesterday = current_hour < 10

            date_label = "yesterday" if use_yesterday else "today"

        summary = {
            "timestamp": datetime.now().isoformat(),
            "target_date": date_label,
            "naics_codes_searched": naics_codes,
            "sam_opportunities_fetched": 0,
            "opportunities_ranked": 0,
            "opportunities_stored": 0,
            "govwin_matches_found": 0,
            "errors": [],
            "naics_results": {}
        }

        try:
            # Step 1: Fetch SAM.gov opportunities for all NAICS codes
            logger.info("=" * 80)
            logger.info(f"STEP 1: Fetching SAM.gov Opportunities for {date_label.upper()}")
            logger.info(f"Searching {len(naics_codes)} NAICS codes")
            logger.info("=" * 80)

            all_opportunities = []
            for naics in naics_codes:
                logger.info(f"Fetching opportunities for NAICS: {naics}")
                try:
                    opps = self.fetch_sam_opportunities(
                        naics_code=naics,
                        keywords=keywords,
                        use_yesterday=use_yesterday,
                        search_date=search_date
                    )
                    all_opportunities.extend(opps)
                    summary["naics_results"][naics] = len(opps)
                    logger.info(f"  → Found {len(opps)} opportunities for NAICS {naics}")
                except Exception as e:
                    logger.error(f"  → Error fetching NAICS {naics}: {e}")
                    summary["errors"].append(f"NAICS {naics}: {str(e)}")

            # Remove duplicates based on notice_id (across NAICS codes)
            unique_opportunities = {}
            for opp in all_opportunities:
                notice_id = opp.get('noticeId')
                if notice_id and notice_id not in unique_opportunities:
                    unique_opportunities[notice_id] = opp

            opportunities = list(unique_opportunities.values())
            summary["sam_opportunities_fetched"] = len(opportunities)
            logger.info(f"Total unique opportunities fetched from SAM.gov: {len(opportunities)}")

            # Check database for existing opportunities to avoid reprocessing
            logger.info("=" * 80)
            logger.info("CHECKING FOR EXISTING OPPORTUNITIES IN DATABASE")
            logger.info("=" * 80)

            existing_notice_ids = self.get_existing_notice_ids()

            # Filter out opportunities that already exist in database
            new_opportunities = []
            duplicate_count = 0
            for opp in opportunities:
                notice_id = opp.get('noticeId')
                if notice_id in existing_notice_ids:
                    duplicate_count += 1
                    logger.info(f"  → Skipping duplicate: {notice_id} - {opp.get('title', 'N/A')[:60]}")
                else:
                    new_opportunities.append(opp)

            opportunities = new_opportunities
            summary["duplicates_skipped"] = duplicate_count
            summary["new_opportunities_to_process"] = len(opportunities)

            logger.info(f"Duplicates found and skipped: {duplicate_count}")
            logger.info(f"New opportunities to process: {len(opportunities)}")

            if not opportunities:
                logger.warning("No new opportunities to process (all were duplicates). Exiting.")
                return summary

            # Step 2: Analyze and score with AI
            logger.info("=" * 80)
            logger.info("STEP 2: Analyzing Opportunities with AI")
            logger.info("=" * 80)

            analysis_result = self.analyze_and_score_opportunities(opportunities)
            ranked = analysis_result.get('ranked_opportunities', [])
            summary["opportunities_ranked"] = len(ranked)
            summary["ai_token_usage"] = analysis_result.get('usage', {})

            if not ranked:
                logger.warning("No opportunities were ranked. Exiting.")
                return summary

            # Step 3: Store in database
            logger.info("=" * 80)
            logger.info("STEP 3: Storing Opportunities in Database")
            logger.info("=" * 80)

            created_ids = self.store_opportunities_in_database(ranked)
            summary["opportunities_stored"] = len(created_ids)
            summary["created_opportunity_ids"] = created_ids

            # Step 4: GovWin matching (if enabled)
            if not skip_govwin:
                logger.info("=" * 80)
                logger.info("STEP 4: GovWin Matching")
                logger.info("=" * 80)

                high_scoring = [opp for opp in ranked if opp.get('fit_score', 0) >= 6]
                logger.info(f"Found {len(high_scoring)} high-scoring opportunities (fit >= 6) for GovWin matching")

                for opp in high_scoring:
                    govwin_matches = self.search_govwin_for_opportunity(opp)
                    if govwin_matches:
                        evaluated = self.evaluate_govwin_matches(opp, govwin_matches)
                        summary["govwin_matches_found"] += len(evaluated)

            logger.info("=" * 80)
            logger.info("WORKFLOW COMPLETE!")
            logger.info("=" * 80)
            logger.info(f"Summary: {json.dumps(summary, indent=2)}")

            return summary

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            summary["errors"].append(str(e))
            raise


def main():
    parser = argparse.ArgumentParser(
        description='Run end-to-end SAM.gov opportunity workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run for today's opportunities (auto-determine based on time)
  python run_end_to_end_workflow.py

  # Run for yesterday's opportunities
  python run_end_to_end_workflow.py --yesterday

  # Run for specific NAICS codes only
  python run_end_to_end_workflow.py --naics 541512 541519

  # Run with keywords filter
  python run_end_to_end_workflow.py --keywords "cloud" "AI" "data"

  # Save results to file
  python run_end_to_end_workflow.py --output results.json
        """
    )
    parser.add_argument('--naics', type=str, nargs='+',
                        help='Specific NAICS code(s) to search (default: all company NAICS codes from config)')
    parser.add_argument('--keywords', type=str, nargs='+',
                        help='Keywords to search for in opportunity titles')
    parser.add_argument('--date', type=str,
                        help='Specific date to search (format: MM/DD/YYYY, e.g., 10/06/2025)')
    parser.add_argument('--yesterday', action='store_true',
                        help='Fetch yesterday\'s opportunities instead of today\'s')
    parser.add_argument('--today', action='store_true',
                        help='Fetch today\'s opportunities (default if run after 10 AM)')
    parser.add_argument('--skip-govwin', action='store_true',
                        help='Skip GovWin integration')
    parser.add_argument('--output', type=str,
                        help='Output file for summary JSON')

    args = parser.parse_args()

    # Determine the date to use
    search_date = None
    use_yesterday = None

    if args.date:
        # Parse the provided date and convert to MM/DD/YYYY format
        from datetime import datetime
        try:
            # Try parsing various date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%m-%d-%Y']:
                try:
                    parsed_date = datetime.strptime(args.date, fmt)
                    search_date = parsed_date.strftime('%m/%d/%Y')
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Unable to parse date: {args.date}")
            logger.info(f"Using specified date: {search_date}")
        except Exception as e:
            logger.error(f"Error parsing date '{args.date}': {e}")
            logger.error("Expected formats: YYYY-MM-DD, MM/DD/YYYY, YYYY/MM/DD, or MM-DD-YYYY")
            exit(1)
    elif args.today:
        use_yesterday = False
    elif args.yesterday:
        use_yesterday = True
    else:
        # Auto-determine based on time (before 10 AM = yesterday, after = today)
        use_yesterday = None  # Let run_workflow decide

    logger.info("Starting End-to-End Workflow")
    date_str = search_date if search_date else ('Yesterday' if args.yesterday else 'Today' if args.today else 'Auto')
    logger.info(f"Parameters: NAICS={args.naics or 'ALL'}, Keywords={args.keywords}, Date={date_str}")

    workflow = EndToEndWorkflow()

    try:
        summary = workflow.run_workflow(
            naics_codes=args.naics,
            keywords=args.keywords,
            use_yesterday=use_yesterday,
            search_date=search_date,
            skip_govwin=args.skip_govwin
        )

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Summary saved to {args.output}")

        return 0

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
