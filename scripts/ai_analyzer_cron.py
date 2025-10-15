#!/usr/bin/env python
"""
AI Analyzer Cron Job - Runs on Render as a scheduled job
Analyzes unscored SAM opportunities and assigns practice areas
"""
import os
import sys
import requests
import logging
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

def analyze_opportunity(analyzer, opp):
    """Analyze a single opportunity using OpenAI"""
    try:
        # Analyze this opportunity
        result = analyzer.analyze_opportunities([opp], output_format="json")

        # Extract the analysis for this opportunity
        ranked_opps = result.get('ranked_opportunities', [])
        if ranked_opps and len(ranked_opps) > 0:
            analyzed = ranked_opps[0]
            return {
                'fit_score': analyzed.get('fit_score', 0),
                'assigned_practice_area': analyzed.get('assigned_practice_area'),
                'justification': analyzed.get('justification'),
                'summary_description': analyzed.get('summary_description', opp.get('description', ''))
            }
        else:
            # Check if it was unranked
            unranked = result.get('unranked_opportunities', [])
            if unranked:
                logger.warning(f"Opportunity {opp.get('notice_id')} was marked as unrankable")
            return None

    except Exception as e:
        logger.error(f"Error analyzing opportunity {opp.get('notice_id')}: {e}")
        return None

def update_opportunity(opp_id, analysis_data):
    """Update opportunity via backend API"""
    try:
        response = requests.patch(
            f"{BACKEND_API_URL}/api/sam-opportunities/{opp_id}/",
            json=analysis_data,
            timeout=30
        )
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

    try:
        # Initialize analyzer
        analyzer = OpportunityAnalyzer(openai_api_key=OPENAI_API_KEY)

        # Fetch unscored opportunities
        response = requests.get(f"{BACKEND_API_URL}/api/sam-opportunities/?fit_score=0&limit=100", timeout=30)
        response.raise_for_status()
        opportunities = response.json()

        logger.info(f"Found {len(opportunities)} unscored opportunities")

        analyzed_count = 0
        updated_count = 0

        # Process each opportunity
        for opp in opportunities:
            opp_id = opp.get('id')
            notice_id = opp.get('notice_id')

            logger.info(f"Analyzing opportunity {notice_id} (ID: {opp_id})...")

            # Analyze
            analysis = analyze_opportunity(analyzer, opp)

            if analysis:
                analyzed_count += 1

                # Update via API
                if update_opportunity(opp_id, analysis):
                    updated_count += 1

        logger.info(f"Analyzed {analyzed_count} opportunities")
        logger.info(f"Updated {updated_count} opportunities")

    except Exception as e:
        logger.error(f"Error in AI analyzer: {e}", exc_info=True)
        raise

    logger.info("=" * 80)
    logger.info(f"AI Analyzer completed at {datetime.now()}")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
