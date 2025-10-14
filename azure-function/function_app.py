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
                payload = {
                    "notice_id": opp.get('notice_id'),
                    "title": opp.get('title'),
                    "department": opp.get('department', 'N/A'),
                    "standardized_department": opp.get('standardized_department', opp.get('department', 'N/A')),
                    "naics_code": opp.get('naics_code', 'N/A'),
                    "fit_score": float(opp.get('fit_score', 0)),
                    "posted_date": opp.get('posted_date'),
                    "response_deadline": opp.get('response_date'),
                    "solicitation_number": opp.get('solicitationNumber', 'N/A'),
                    "description": opp.get('descriptionText', '')[:1000],
                    "summary_description": opp.get('summary_description', ''),
                    "ptype": opp.get('ptype', 'N/A'),
                    "set_aside": opp.get('set_aside', 'N/A'),
                    "assigned_practice_area": opp.get('assigned_practice_area', 'Uncategorized'),
                    "justification": opp.get('justification', ''),
                    "sam_link": opp.get('uiLink', 'N/A')
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
                    else:
                        logging.warning(f"Failed to store match: {response.status_code}")

                except Exception as e:
                    logging.error(f"Error storing match: {e}")
                    continue

            return stored_matches

        except Exception as e:
            logging.error(f"Error evaluating matches: {e}")
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

            if not ranked:
                logging.warning("No opportunities were ranked")
                return summary

            # Step 4: Store in database
            created_ids = self.store_opportunities_in_database(ranked)
            summary["opportunities_stored"] = len(created_ids)

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


@app.timer_trigger(schedule="0 0 1 * * *", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False)
def NightlyWorkflow(myTimer: func.TimerRequest) -> None:
    """
    Timer-triggered Azure Function that runs nightly at 1 AM UTC (6 PM PST / 9 PM EST)

    Schedule: "0 0 1 * * *" = 1:00 AM UTC every day

    To change the schedule, modify the cron expression:
    Format: "second minute hour day month dayOfWeek"

    Examples:
    - "0 0 2 * * *"  = 2:00 AM UTC daily
    - "0 30 1 * * *" = 1:30 AM UTC daily
    - "0 0 9 * * 1-5" = 9:00 AM UTC on weekdays only
    """
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed at: %s', datetime.utcnow())

    # Run the workflow
    try:
        workflow = WorkflowRunner()
        summary = workflow.run()

        logging.info('Workflow completed successfully')
        logging.info(f'Summary: {json.dumps(summary, indent=2)}')

    except Exception as e:
        logging.error(f'Workflow failed: {e}', exc_info=True)
        raise
