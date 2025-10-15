"""
Azure Function for SAM.gov Opportunity Nightly Workflow

This function runs automatically every night (1 AM UTC / 6 PM PST / 9 PM EST) and:
1. Fetches new opportunities from SAM.gov
2. Analyzes and scores them with AI
3. Stores high-scoring opportunities in the database
4. Searches GovWin for matches
5. Evaluates and stores matches

Configured via Azure Function App Settings (environment variables):
- SAM_API_KEY
- GOVWIN_CLIENT_ID, GOVWIN_CLIENT_SECRET, GOVWIN_USERNAME, GOVWIN_PASSWORD
- OPENAI_API_KEY
- DATABASE_URL
- BACKEND_API_URL (the deployed web app URL)
"""

import azure.functions as func
import logging
import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import our workflow modules
from app.sam_client import SAMClient
from app.openai_analyzer import OpportunityAnalyzer
from app.config import COMPANY_NAICS_CODES

app = func.FunctionApp()

# Get configuration from environment variables
SAM_API_KEY = os.getenv("SAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOVWIN_CLIENT_ID = os.getenv("GOVWIN_CLIENT_ID")
GOVWIN_CLIENT_SECRET = os.getenv("GOVWIN_CLIENT_SECRET")
GOVWIN_USERNAME = os.getenv("GOVWIN_USERNAME")
GOVWIN_PASSWORD = os.getenv("GOVWIN_PASSWORD")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")

class WorkflowRunner:
    """Runs the nightly workflow in Azure Functions"""

    def __init__(self):
        self.sam_client = SAMClient(api_key=SAM_API_KEY)
        self.analyzer = OpportunityAnalyzer(openai_api_key=OPENAI_API_KEY)
        self.backend_api = BACKEND_API_URL
        self.govwin_client = None

    def _get_govwin_client(self):
        """Lazy load GovWin client"""
        if self.govwin_client is None:
            from app.govwin_client import GovWinClient
            self.govwin_client = GovWinClient(username=GOVWIN_USERNAME, password=GOVWIN_PASSWORD)
        return self.govwin_client

    def get_existing_notice_ids(self) -> set:
        """Fetch existing notice IDs from database"""
        try:
            logging.info("Fetching existing notice IDs from database...")
            response = requests.get(f"{self.backend_api}/sam-opportunities/")

            if response.status_code == 200:
                existing_opps = response.json()
                existing_notice_ids = {opp.get('notice_id') for opp in existing_opps if opp.get('notice_id')}
                logging.info(f"Found {len(existing_notice_ids)} existing notice IDs")
                return existing_notice_ids
            else:
                logging.warning(f"Failed to fetch existing opportunities: {response.status_code}")
                return set()
        except Exception as e:
            logging.error(f"Error fetching existing notice IDs: {e}")
            return set()

    def fetch_sam_opportunities(self, naics_code: str, search_date: str) -> List[Dict[str, Any]]:
        """Fetch opportunities from SAM.gov for a specific date and NAICS code"""
        logging.info(f"Fetching SAM.gov opportunities for {search_date} - NAICS: {naics_code}")

        try:
            result = self.sam_client.search_opportunities(
                naics_code=naics_code,
                posted_from=search_date,
                posted_to=search_date,
                limit=100,
                include_description=True
            )

            opportunities = result.get('opportunitiesData', [])
            logging.info(f"Fetched {len(opportunities)} opportunities for NAICS {naics_code}")
            return opportunities

        except Exception as e:
            logging.error(f"Error fetching SAM.gov opportunities: {e}")
            return []

    def analyze_and_score_opportunities(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use AI to analyze and score opportunities"""
        logging.info(f"Analyzing {len(opportunities)} opportunities with AI...")

        try:
            result = self.analyzer.analyze_opportunities(opportunities, output_format='json')
            ranked = result.get('ranked_opportunities', [])
            logging.info(f"AI Analysis complete: {len(ranked)} ranked opportunities")
            return result
        except Exception as e:
            logging.error(f"Error analyzing opportunities: {e}")
            return {'ranked_opportunities': [], 'unranked_opportunities': [], 'usage': {}}

    def store_opportunities_in_database(self, ranked_opportunities: List[Dict[str, Any]]) -> List[int]:
        """Store opportunities in database via API"""
        logging.info(f"Storing {len(ranked_opportunities)} opportunities in database...")

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
                    "description": (opp.get('descriptionText') or opp.get('description', ''))[:1000],
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
                    logging.info(f"Created opportunity ID {created['id']}")
                else:
                    logging.warning(f"Failed to create opportunity: {response.status_code}")

            except Exception as e:
                logging.error(f"Error storing opportunity: {e}")
                continue

        logging.info(f"Successfully stored {len(created_ids)} opportunities")
        return created_ids

    def search_govwin_for_opportunity(self, sam_opportunity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search GovWin for matches to a SAM opportunity"""
        title = sam_opportunity.get('title', '')
        logging.info(f"Searching GovWin for: {title[:60]}...")

        try:
            govwin_client = self._get_govwin_client()
            all_matches = []
            seen_ids = set()

            # Extract keywords from title
            title_keywords = self._extract_keywords(title)
            if title_keywords:
                try:
                    response = govwin_client.search_opportunities({'q': title_keywords})
                    results = response.get('opportunities', []) if isinstance(response, dict) else []
                    for result in results[:10]:
                        gw_id = result.get('id')
                        if gw_id and gw_id not in seen_ids:
                            all_matches.append(result)
                            seen_ids.add(gw_id)
                except Exception as e:
                    logging.warning(f"GovWin search failed: {e}")

            logging.info(f"Found {len(all_matches)} GovWin matches")
            return all_matches

        except Exception as e:
            logging.error(f"Error searching GovWin: {e}")
            return []

    def _extract_keywords(self, title: str) -> str:
        """Extract meaningful keywords from title"""
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'for', 'of', 'to', 'in', 'on', 'at',
            'services', 'service', 'support', 'solicitation', 'notice', 'request'
        }
        words = title.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return ' '.join(keywords[:5])

    def evaluate_govwin_matches(self, sam_opportunity: Dict[str, Any], govwin_opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use AI to evaluate and score GovWin matches"""
        if not govwin_opportunities:
            return []

        logging.info(f"Evaluating {len(govwin_opportunities)} GovWin matches with AI...")

        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)

            # Prepare summaries for AI
            sam_summary = {
                'title': sam_opportunity.get('title', 'N/A'),
                'department': sam_opportunity.get('department', 'N/A'),
                'solicitation_number': sam_opportunity.get('solicitationNumber', 'N/A'),
                'description': sam_opportunity.get('summary_description', '')[:500]
            }

            govwin_summaries = []
            for gw_opp in govwin_opportunities[:10]:
                govwin_summaries.append({
                    'id': gw_opp.get('id', 'N/A'),
                    'title': gw_opp.get('title', 'N/A'),
                    'agency': gw_opp.get('agencyName', 'N/A'),
                    'description': gw_opp.get('description', '')[:300]
                })

            # AI matching prompt
            prompt = f"""You are a federal contracting expert analyzing opportunity matches.

SAM.gov Opportunity:
{json.dumps(sam_summary, indent=2)}

Potential GovWin Matches:
{json.dumps(govwin_summaries, indent=2)}

For each GovWin opportunity, determine:
1. Match Confidence Score (0-10)
2. Match Type: same_opportunity, related_opportunity, teaming_opportunity, or not_related
3. Reasoning (1-2 sentences)

Only include matches with confidence >= 5.0.

Return JSON format:
{{
  "matches": [
    {{
      "govwin_id": "OPP12345",
      "match_confidence": 8.5,
      "match_type": "same_opportunity",
      "reasoning": "Same solicitation and agency",
      "teaming_potential": "high/medium/low"
    }}
  ]
}}"""

            # Call OpenAI
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a federal contracting expert. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            ai_response = json.loads(response.choices[0].message.content)
            matches = ai_response.get('matches', [])
            logging.info(f"AI found {len(matches)} quality matches")

            # Store matches in database
            stored_matches = []
            for match in matches:
                try:
                    match_payload = {
                        "sam_notice_id": sam_opportunity.get('notice_id'),
                        "govwin_id": match['govwin_id'],
                        "search_strategy": "ai_matching",
                        "match_score": float(match['match_confidence']),
                        "match_notes": f"{match['match_type']} - {match['reasoning']}",
                        "status": "pending_review"
                    }

                    response = requests.post(
                        f"{self.backend_api}/matches/from-external-ids",
                        json=match_payload,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 201:
                        stored_matches.append(response.json())
                        logging.info(f"Stored match: {match['govwin_id']}")

                        # Fetch and store related contracts for this match
                        try:
                            contracts = self.fetch_and_store_contracts(match['govwin_id'])
                            if contracts:
                                logging.info(f"Stored {len(contracts)} contracts for {match['govwin_id']}")
                        except Exception as contract_error:
                            logging.warning(f"Failed to fetch contracts for {match['govwin_id']}: {contract_error}")
                    else:
                        logging.warning(f"Failed to store match: {response.status_code}")

                except Exception as e:
                    logging.error(f"Error storing match: {e}")
                    continue

            return stored_matches

        except Exception as e:
            logging.error(f"Error evaluating matches: {e}")
            return []

    def fetch_and_store_contracts(self, govwin_id: str) -> List[Dict[str, Any]]:
        """
        Fetch contracts for a GovWin opportunity and store them in the database.

        Args:
            govwin_id: The GovWin opportunity ID

        Returns:
            List of stored contract records
        """
        try:
            logging.info(f"Fetching contracts for GovWin ID: {govwin_id}")

            # Fetch contracts from GovWin API
            contracts = self.govwin_client.get_opportunity_contracts(govwin_id)

            if not contracts:
                logging.info(f"No contracts found for {govwin_id}")
                return []

            logging.info(f"Found {len(contracts)} contracts for {govwin_id}")

            # Store each contract in the database
            stored_contracts = []
            for contract in contracts:
                try:
                    # Prepare contract payload
                    contract_payload = {
                        "govwin_opportunity_id": govwin_id,
                        "contract_data": contract  # Store the full contract object
                    }

                    # Store via backend API
                    response = requests.post(
                        f"{self.backend_api}/govwin-contracts",
                        json=contract_payload,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 201:
                        stored_contracts.append(response.json())
                        contract_id = contract.get('id', 'Unknown')
                        contract_title = contract.get('title', 'Unknown')
                        logging.info(f"Stored contract: {contract_id} - {contract_title[:50]}")
                    else:
                        logging.warning(f"Failed to store contract: {response.status_code} - {response.text}")

                except Exception as e:
                    logging.error(f"Error storing individual contract: {e}")
                    continue

            logging.info(f"Successfully stored {len(stored_contracts)} contracts for {govwin_id}")
            return stored_contracts

        except Exception as e:
            logging.error(f"Error fetching/storing contracts for {govwin_id}: {e}")
            return []

    def run(self) -> Dict[str, Any]:
        """Run the complete nightly workflow"""

        # Determine target date (yesterday by default for nightly run)
        target_date = (datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')

        summary = {
            "timestamp": datetime.now().isoformat(),
            "target_date": target_date,
            "sam_opportunities_fetched": 0,
            "opportunities_stored": 0,
            "govwin_matches_found": 0,
            "errors": []
        }

        try:
            logging.info("=" * 80)
            logging.info(f"Starting Nightly Workflow for {target_date}")
            logging.info("=" * 80)

            # Step 1: Fetch existing notice IDs to avoid duplicates
            existing_notice_ids = self.get_existing_notice_ids()

            # Step 2: Fetch SAM.gov opportunities for all NAICS codes
            all_opportunities = []
            for naics in COMPANY_NAICS_CODES:
                logging.info(f"Fetching opportunities for NAICS: {naics}")
                try:
                    opps = self.fetch_sam_opportunities(naics, target_date)
                    all_opportunities.extend(opps)
                except Exception as e:
                    logging.error(f"Error fetching NAICS {naics}: {e}")
                    summary["errors"].append(f"NAICS {naics}: {str(e)}")

            # Remove duplicates
            unique_opportunities = {}
            for opp in all_opportunities:
                notice_id = opp.get('noticeId')
                if notice_id and notice_id not in unique_opportunities and notice_id not in existing_notice_ids:
                    unique_opportunities[notice_id] = opp

            opportunities = list(unique_opportunities.values())
            summary["sam_opportunities_fetched"] = len(opportunities)
            logging.info(f"Total new unique opportunities: {len(opportunities)}")

            if not opportunities:
                logging.info("No new opportunities to process")
                return summary

            # Step 3: Analyze and score with AI
            analysis_result = self.analyze_and_score_opportunities(opportunities)
            ranked = analysis_result.get('ranked_opportunities', [])
            unranked = analysis_result.get('unranked_opportunities', [])

            # Create a map of AI scores by notice_id
            ai_scores_map = {opp.get('notice_id'): opp for opp in ranked if opp.get('notice_id')}

            # Prepare all opportunities for storage, merging AI insights where available
            all_opportunities_to_store = []
            for opp in opportunities:
                notice_id = opp.get('noticeId')
                if notice_id in ai_scores_map:
                    # Use the AI-enriched version
                    all_opportunities_to_store.append(ai_scores_map[notice_id])
                else:
                    # Use original opportunity with default scoring
                    from app.openai_analyzer import BusinessDevelopmentAgent
                    agent = BusinessDevelopmentAgent(api_key=OPENAI_API_KEY)
                    standardized = agent._standardize_opportunity(opp.copy())
                    standardized['fit_score'] = 0  # No AI score available
                    standardized['assigned_practice_area'] = 'Uncategorized'
                    standardized['justification'] = 'Not analyzed by AI'
                    all_opportunities_to_store.append(standardized)

            logging.info(f"Storing {len(all_opportunities_to_store)} total opportunities (Ranked: {len(ranked)}, Unranked/Unprocessed: {len(all_opportunities_to_store) - len(ranked)})")

            # Step 4: Store in database
            created_ids = self.store_opportunities_in_database(all_opportunities_to_store)
            summary["opportunities_stored"] = len(created_ids)
            summary["ai_ranked_count"] = len(ranked)
            summary["unranked_count"] = len(all_opportunities_to_store) - len(ranked)

            # Step 5: GovWin matching for high-scoring opportunities
            high_scoring = [opp for opp in ranked if opp.get('fit_score', 0) >= 6]
            logging.info(f"Found {len(high_scoring)} high-scoring opportunities for GovWin matching")

            for opp in high_scoring:
                govwin_matches = self.search_govwin_for_opportunity(opp)
                if govwin_matches:
                    evaluated = self.evaluate_govwin_matches(opp, govwin_matches)
                    summary["govwin_matches_found"] += len(evaluated)

            logging.info("=" * 80)
            logging.info("Nightly Workflow Complete!")
            logging.info(f"Summary: {json.dumps(summary, indent=2)}")
            logging.info("=" * 80)

            return summary

        except Exception as e:
            logging.error(f"Workflow error: {e}", exc_info=True)
            summary["errors"].append(str(e))
            return summary

# =============================
# 3-FUNCTION ARCHITECTURE
# =============================

@app.timer_trigger(schedule="0 0 1 * * *", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False)
def SAMFetcher(myTimer: func.TimerRequest) -> None:
    """
    Function 1: SAM Fetcher
    Schedule: 1:00 AM UTC daily (9:00 PM EDT / 6:00 PM PDT)

    Fetches opportunities from SAM.gov and stores raw data in database.
    - No AI analysis (fit_score = 0)
    - No GovWin matching
    - Just fetch and store

    This function should complete in < 5 minutes.
    """
    if myTimer.past_due:
        logging.info('[SAMFetcher] The timer is past due!')

    logging.info('[SAMFetcher] Starting at: %s', datetime.utcnow())

    try:
        workflow = WorkflowRunner()
        sam_client = workflow.sam_client
        backend_api = workflow.backend_api

        # Use yesterday's date to fetch latest opportunities
        search_date = (datetime.utcnow() - timedelta(days=1)).strftime("%m/%d/%Y")

        summary = {
            "function": "SAMFetcher",
            "start_time": datetime.utcnow().isoformat(),
            "search_date": search_date,
            "naics_codes_processed": 0,
            "opportunities_fetched": 0,
            "opportunities_stored": 0,
            "errors": []
        }

        # Get existing notice IDs to avoid duplicates
        existing_notice_ids = workflow.get_existing_notice_ids()
        logging.info(f"[SAMFetcher] Found {len(existing_notice_ids)} existing opportunities in database")

        # Fetch opportunities for each NAICS code
        for naics_code in COMPANY_NAICS_CODES:
            try:
                logging.info(f"[SAMFetcher] Fetching opportunities for NAICS {naics_code}")
                opportunities = workflow.fetch_sam_opportunities(naics_code, search_date)

                # Filter out duplicates
                new_opportunities = [opp for opp in opportunities if opp.get('notice_id') not in existing_notice_ids]

                logging.info(f"[SAMFetcher] Found {len(opportunities)} opportunities, {len(new_opportunities)} are new")
                summary["opportunities_fetched"] += len(new_opportunities)

                # Store each opportunity with fit_score=0 (unscored)
                for opp in new_opportunities:
                    try:
                        # Skip if no notice_id
                        notice_id = opp.get("notice_id") or opp.get("noticeId")
                        if not notice_id:
                            logging.warning(f"[SAMFetcher] Skipping opportunity without notice_id: {opp.get('title', 'Unknown')}")
                            continue

                        # Prepare opportunity data with fit_score=0
                        opportunity_data = {
                            "notice_id": notice_id,
                            "title": opp.get("title"),
                            "department": opp.get("department"),
                            "standardized_department": opp.get("standardized_department"),
                            "sub_tier": opp.get("sub_tier"),
                            "office": opp.get("office"),
                            "naics_code": opp.get("naics_code"),
                            "full_parent_path": opp.get("full_parent_path"),
                            "fit_score": 0.0,  # Unscored - to be processed by AIAnalyzer
                            "posted_date": opp.get("posted_date"),
                            "response_deadline": opp.get("response_deadline"),
                            "solicitation_number": opp.get("solicitation_number"),
                            "description": opp.get("description"),
                            "summary_description": "",  # No AI summary yet
                            "type": opp.get("type"),
                            "ptype": opp.get("ptype"),
                            "classification_code": opp.get("classification_code"),
                            "set_aside": opp.get("set_aside"),
                            "place_of_performance_city": opp.get("place_of_performance_city"),
                            "place_of_performance_state": opp.get("place_of_performance_state"),
                            "place_of_performance_zip": opp.get("place_of_performance_zip"),
                            "point_of_contact_email": opp.get("point_of_contact_email"),
                            "point_of_contact_name": opp.get("point_of_contact_name"),
                            "sam_link": opp.get("sam_link"),
                            "assigned_practice_area": None,  # No AI assignment yet
                            "justification": None,  # No AI justification yet
                        }

                        # POST to backend API
                        response = requests.post(
                            f"{backend_api}/sam-opportunities/",
                            json=opportunity_data,
                            timeout=30
                        )

                        if response.status_code == 201:
                            summary["opportunities_stored"] += 1
                            existing_notice_ids.add(notice_id)
                            logging.info(f"[SAMFetcher] Stored: {opp.get('title')[:50]}... (fit_score=0)")
                        elif response.status_code == 400 and "already exists" in response.text:
                            logging.info(f"[SAMFetcher] Already exists: {notice_id}")
                        else:
                            error_detail = response.text[:200] if response.text else "No error details"
                            logging.warning(f"[SAMFetcher] Failed to store {notice_id}: {response.status_code} - {error_detail}")
                            summary["errors"].append(f"Failed to store {notice_id}: {response.status_code}")

                    except Exception as e:
                        logging.error(f"[SAMFetcher] Error storing opportunity: {e}")
                        summary["errors"].append(f"Error storing opportunity: {str(e)}")

                summary["naics_codes_processed"] += 1

            except Exception as e:
                logging.error(f"[SAMFetcher] Error processing NAICS {naics_code}: {e}")
                summary["errors"].append(f"NAICS {naics_code}: {str(e)}")

        summary["end_time"] = datetime.utcnow().isoformat()
        summary["duration_seconds"] = (datetime.fromisoformat(summary["end_time"]) -
                                       datetime.fromisoformat(summary["start_time"])).total_seconds()

        logging.info(f'[SAMFetcher] Completed successfully: {json.dumps(summary, indent=2)}')

    except Exception as e:
        logging.error(f'[SAMFetcher] Failed: {e}', exc_info=True)
        raise


@app.timer_trigger(schedule="0 30 1 * * *", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False)
def AIAnalyzer(myTimer: func.TimerRequest) -> None:
    """
    Function 2: AI Analyzer
    Schedule: 1:30 AM UTC daily (30 minutes after SAMFetcher)

    Analyzes and scores unprocessed opportunities (fit_score = 0).
    - Queries database for opportunities with fit_score = 0
    - Processes in batches of 20
    - Calls OpenAI to analyze and score
    - Updates database with fit_score, justification, assigned_practice_area

    This function processes opportunities in batches to avoid timeouts.
    """
    if myTimer.past_due:
        logging.info('[AIAnalyzer] The timer is past due!')

    logging.info('[AIAnalyzer] Starting at: %s', datetime.utcnow())

    try:
        workflow = WorkflowRunner()
        analyzer = workflow.analyzer
        backend_api = workflow.backend_api

        summary = {
            "function": "AIAnalyzer",
            "start_time": datetime.utcnow().isoformat(),
            "opportunities_found": 0,
            "opportunities_analyzed": 0,
            "opportunities_updated": 0,
            "errors": []
        }

        # Query database for unscored opportunities (fit_score = 0 or NULL)
        logging.info("[AIAnalyzer] Fetching unscored opportunities from database...")
        response = requests.get(f"{backend_api}/sam-opportunities/?limit=1000", timeout=30)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch opportunities: {response.status_code}")

        all_opportunities = response.json()

        # Filter for unscored opportunities (fit_score is 0 or None)
        unscored_opportunities = [
            opp for opp in all_opportunities
            if opp.get("fit_score") is None or opp.get("fit_score") == 0.0
        ]

        summary["opportunities_found"] = len(unscored_opportunities)
        logging.info(f"[AIAnalyzer] Found {len(unscored_opportunities)} unscored opportunities")

        # Process in batches of 20
        BATCH_SIZE = 20
        for i in range(0, len(unscored_opportunities), BATCH_SIZE):
            batch = unscored_opportunities[i:i+BATCH_SIZE]
            logging.info(f"[AIAnalyzer] Processing batch {i//BATCH_SIZE + 1} ({len(batch)} opportunities)")

            # Analyze the batch with OpenAI
            try:
                # Map sam_link to uiLink for compatibility with analyzer
                for opp in batch:
                    if 'uiLink' not in opp or not opp.get('uiLink'):
                        opp['uiLink'] = opp.get('sam_link', 'N/A')

                result = analyzer.analyze_opportunities(batch, output_format='json')
                ranked_opportunities = result.get('ranked_opportunities', [])

                logging.info(f"[AIAnalyzer] Analyzed {len(ranked_opportunities)} opportunities in batch")

                # Update each opportunity with its analysis
                for ranked_opp in ranked_opportunities:
                    try:
                        # Find the original opportunity by notice_id
                        notice_id = ranked_opp.get("notice_id")
                        original_opp = next((o for o in batch if o.get("notice_id") == notice_id), None)

                        if not original_opp:
                            logging.warning(f"[AIAnalyzer] Could not find original opportunity for notice_id: {notice_id}")
                            continue

                        # Update via PATCH endpoint
                        update_data = {
                            "fit_score": float(ranked_opp.get("fit_score", 0.0)),
                            "analysis_data": json.dumps({
                                "justification": ranked_opp.get("justification", ""),
                                "assigned_practice_area": ranked_opp.get("assigned_practice_area", ""),
                                "summary_description": ranked_opp.get("summary_description", "")
                            })
                        }

                        patch_response = requests.patch(
                            f"{backend_api}/sam-opportunities/{original_opp['id']}",
                            json=update_data,
                            timeout=30
                        )

                        if patch_response.status_code == 200:
                            summary["opportunities_updated"] += 1
                            summary["opportunities_analyzed"] += 1
                            logging.info(f"[AIAnalyzer] Updated: {ranked_opp.get('title', '')[:50]}... (fit_score={ranked_opp.get('fit_score')})")
                        else:
                            error_detail = patch_response.text[:200] if patch_response.text else "No error details"
                            logging.warning(f"[AIAnalyzer] Failed to update {original_opp['id']}: {patch_response.status_code} - {error_detail}")
                            summary["errors"].append(f"Failed to update {original_opp['id']}: {patch_response.status_code}")

                    except Exception as e:
                        logging.error(f"[AIAnalyzer] Error updating opportunity: {e}")
                        summary["errors"].append(f"Error updating opportunity: {str(e)}")

            except Exception as e:
                logging.error(f"[AIAnalyzer] Error analyzing batch: {e}")
                summary["errors"].append(f"Batch analysis error: {str(e)}")

        summary["end_time"] = datetime.utcnow().isoformat()
        summary["duration_seconds"] = (datetime.fromisoformat(summary["end_time"]) -
                                       datetime.fromisoformat(summary["start_time"])).total_seconds()

        logging.info(f'[AIAnalyzer] Completed successfully: {json.dumps(summary, indent=2)}')

    except Exception as e:
        logging.error(f'[AIAnalyzer] Failed: {e}', exc_info=True)
        raise


@app.timer_trigger(schedule="0 0 2 * * *", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False)
def GovWinMatcher(myTimer: func.TimerRequest) -> None:
    """
    Function 3: GovWin Matcher
    Schedule: 2:00 AM UTC daily (after AIAnalyzer completes)

    Finds GovWin matches for high-scoring opportunities (fit_score >= 6).
    - Queries database for opportunities with fit_score >= 6 without GovWin matches
    - Processes in batches
    - Searches GovWin API for matches
    - Uses AI to evaluate match quality
    - Stores matches in database

    This function processes opportunities in batches to avoid timeouts.
    """
    if myTimer.past_due:
        logging.info('[GovWinMatcher] The timer is past due!')

    logging.info('[GovWinMatcher] Starting at: %s', datetime.utcnow())

    try:
        workflow = WorkflowRunner()
        backend_api = workflow.backend_api

        summary = {
            "function": "GovWinMatcher",
            "start_time": datetime.utcnow().isoformat(),
            "opportunities_found": 0,
            "opportunities_processed": 0,
            "matches_found": 0,
            "errors": []
        }

        # Query database for high-scoring opportunities without matches
        logging.info("[GovWinMatcher] Fetching high-scoring opportunities from database...")
        response = requests.get(f"{backend_api}/sam-opportunities/?min_fit_score=6.0&limit=1000", timeout=30)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch opportunities: {response.status_code}")

        all_opportunities = response.json()

        # Filter for opportunities without matches (match_count is 0 or None)
        opportunities_without_matches = [
            opp for opp in all_opportunities
            if opp.get("match_count") is None or opp.get("match_count") == 0
        ]

        summary["opportunities_found"] = len(opportunities_without_matches)
        logging.info(f"[GovWinMatcher] Found {len(opportunities_without_matches)} high-scoring opportunities without matches")

        # Process in batches of 10 (GovWin matching is slower)
        BATCH_SIZE = 10
        for i in range(0, len(opportunities_without_matches), BATCH_SIZE):
            batch = opportunities_without_matches[i:i+BATCH_SIZE]
            logging.info(f"[GovWinMatcher] Processing batch {i//BATCH_SIZE + 1} ({len(batch)} opportunities)")

            for opp in batch:
                try:
                    # Step 1: Search GovWin for potential matches
                    govwin_opps = workflow.search_govwin_for_opportunity(opp)

                    # Step 2: Evaluate matches with AI if any found
                    if govwin_opps:
                        scored_matches = workflow.evaluate_govwin_matches(opp, govwin_opps)

                        if scored_matches:
                            summary["matches_found"] += len(scored_matches)
                            logging.info(f"[GovWinMatcher] Found {len(scored_matches)} scored matches for: {opp.get('title', '')[:50]}...")

                    summary["opportunities_processed"] += 1

                except Exception as e:
                    logging.error(f"[GovWinMatcher] Error matching opportunity {opp.get('id')}: {e}")
                    summary["errors"].append(f"Opportunity {opp.get('id')}: {str(e)}")

        summary["end_time"] = datetime.utcnow().isoformat()
        summary["duration_seconds"] = (datetime.fromisoformat(summary["end_time"]) -
                                       datetime.fromisoformat(summary["start_time"])).total_seconds()

        logging.info(f'[GovWinMatcher] Completed successfully: {json.dumps(summary, indent=2)}')

    except Exception as e:
        logging.error(f'[GovWinMatcher] Failed: {e}', exc_info=True)
        raise
