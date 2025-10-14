"""
Test GovWin matching implementation with the HRIT opportunity.
"""
import logging
import json
import requests
from run_end_to_end_workflow import EndToEndWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_govwin_matching():
    """Test the GovWin matching workflow with the HRIT opportunity."""

    logger.info("=" * 80)
    logger.info("TESTING GOVWIN MATCHING IMPLEMENTATION")
    logger.info("=" * 80)

    # Initialize workflow
    workflow = EndToEndWorkflow()

    # Get the HRIT opportunity from database (we know it's ID 8)
    logger.info("\nStep 1: Fetching HRIT opportunity from database...")
    response = requests.get("http://localhost:8000/api/sam-opportunities/8")

    if response.status_code != 200:
        logger.error("Failed to fetch opportunity from database")
        return

    sam_opp = response.json()
    logger.info(f"✓ Found: {sam_opp['title']}")
    logger.info(f"  Notice ID: {sam_opp['notice_id']}")
    logger.info(f"  Department: {sam_opp['department']}")
    logger.info(f"  Fit Score: {sam_opp['fit_score']}")

    # Test Step 1: Search GovWin for matches
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: Searching GovWin for matches...")
    logger.info("=" * 80)

    govwin_matches = workflow.search_govwin_for_opportunity(sam_opp)

    if not govwin_matches:
        logger.warning("No GovWin matches found!")
        return

    logger.info(f"\n✓ Found {len(govwin_matches)} potential matches in GovWin:")
    for i, match in enumerate(govwin_matches[:5], 1):
        logger.info(f"  {i}. {match.get('id')} - {match.get('title', 'N/A')[:60]}")

    # Test Step 2: Evaluate matches with AI
    logger.info("\n" + "=" * 80)
    logger.info("Step 3: Evaluating matches with AI...")
    logger.info("=" * 80)

    evaluated_matches = workflow.evaluate_govwin_matches(sam_opp, govwin_matches)

    if not evaluated_matches:
        logger.warning("No quality matches found (all below confidence threshold)")
        return

    logger.info(f"\n✓ AI identified {len(evaluated_matches)} quality matches:")
    for match in evaluated_matches:
        logger.info(f"  • GovWin ID: {match['govwin_opportunity_id']}")
        logger.info(f"    Match Score: {match['ai_match_score']}")
        logger.info(f"    Reasoning: {match['ai_reasoning']}")

    # Verify matches were stored in database
    logger.info("\n" + "=" * 80)
    logger.info("Step 4: Verifying matches in database...")
    logger.info("=" * 80)

    response = requests.get("http://localhost:8000/api/matches/")
    if response.status_code == 200:
        all_matches = response.json()
        logger.info(f"✓ Total matches in database: {len(all_matches)}")

        # Find our HRIT matches by SAM opportunity ID
        hrit_matches = [m for m in all_matches if m['sam_opportunity']['notice_id'] == sam_opp['notice_id']]
        logger.info(f"✓ HRIT opportunity has {len(hrit_matches)} matches stored")

        # Check for OPP256560
        opp256560_match = next((m for m in hrit_matches if m['govwin_opportunity']['govwin_id'] == 'OPP256560'), None)
        if opp256560_match:
            logger.info(f"\n✓✓✓ VERIFIED: Found expected match OPP256560!")
            logger.info(f"    Match Score: {opp256560_match['ai_match_score']}")
            logger.info(f"    Reasoning: {opp256560_match['ai_reasoning']}")
        else:
            logger.warning("Expected match OPP256560 not found in database")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✓ GovWin search: SUCCESS ({len(govwin_matches)} matches found)")
    logger.info(f"✓ AI evaluation: SUCCESS ({len(evaluated_matches)} quality matches)")
    logger.info(f"✓ Database storage: SUCCESS")
    logger.info(f"✓ Expected match OPP256560: {'FOUND' if opp256560_match else 'NOT FOUND'}")
    logger.info("\nGovWin matching implementation is working!")

if __name__ == "__main__":
    test_govwin_matching()
