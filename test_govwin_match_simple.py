"""
Simple test to verify GovWin ID 256560 and search for HRIT opportunities.
"""
import logging
import json
from app.govwin_client import GovWinClient
from app.config import GOVWIN_USERNAME, GOVWIN_PASSWORD
from app.config import SAM_API_KEY
from app.sam_client import SAMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_govwin_hrit():
    """Test GovWin opportunity retrieval and search."""

    logger.info("Initializing GovWin client...")
    govwin_client = GovWinClient(username=GOVWIN_USERNAME, password=GOVWIN_PASSWORD)

    # Test 1: Get specific GovWin opportunity by ID
    logger.info("=" * 80)
    logger.info("TEST 1: Fetching GovWin Opportunity ID 256560")
    logger.info("=" * 80)

    try:
        opportunity = govwin_client.get_opportunity("256560")
        logger.info(f"✓ Successfully retrieved GovWin ID 256560")
        logger.info(f"\nOpportunity Details:")
        logger.info(f"  ID: {opportunity.get('id', 'N/A')}")
        logger.info(f"  Title: {opportunity.get('title', 'N/A')}")
        logger.info(f"  Agency: {opportunity.get('agencyName', 'N/A')}")
        logger.info(f"  Total Value: ${opportunity.get('totalValue', 'N/A'):,}" if opportunity.get('totalValue') else "  Total Value: N/A")
        logger.info(f"  Posted Date: {opportunity.get('postedDate', 'N/A')}")
        logger.info(f"  Description: {opportunity.get('description', 'N/A')[:200]}...")

        # Save to file
        with open('govwin_256560_details.json', 'w') as f:
            json.dump(opportunity, f, indent=2)
        logger.info(f"\n✓ Full details saved to: govwin_256560_details.json")

    except Exception as e:
        logger.error(f"✗ Failed to retrieve GovWin ID 256560: {e}")
        return

    # Test 2: Search for HRIT opportunities in GovWin
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Searching GovWin for HRIT opportunities")
    logger.info("=" * 80)

    search_terms = [
        {"title": "HRIT"},
        {"title": "Human Resources Information Technology"},
        {"agencyName": "Office of Personnel Management"},
    ]

    all_results = []

    for params in search_terms:
        logger.info(f"\nSearching with params: {params}")
        try:
            results = govwin_client.search_opportunities(params)
            logger.info(f"  Found {len(results)} opportunities")

            for opp in results[:5]:  # Show first 5
                logger.info(f"    - ID: {opp.get('id')} | {opp.get('title', 'N/A')[:60]}")
                if opp.get('id') not in [r.get('id') for r in all_results]:
                    all_results.append(opp)

                # Check if this is ID 256560
                if str(opp.get('id')) == "256560":
                    logger.info(f"      ✓✓✓ FOUND GovWin ID 256560 in search results! ✓✓✓")

        except Exception as e:
            logger.error(f"  Error searching: {e}")
            continue

    logger.info(f"\n\nTotal unique opportunities found: {len(all_results)}")

    # Test 3: Find the HRIT opportunity in SAM.gov
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Finding HRIT opportunity in SAM.gov")
    logger.info("=" * 80)

    sam_client = SAMClient(api_key=SAM_API_KEY)

    # Search for HRIT in SAM
    result = sam_client.search_opportunities(
        title="HRIT",
        limit=10
    )

    sam_opportunities = result.get('opportunitiesData', [])
    logger.info(f"Found {len(sam_opportunities)} SAM.gov opportunities matching 'HRIT'")

    for i, opp in enumerate(sam_opportunities, 1):
        logger.info(f"\n{i}. {opp.get('title', 'N/A')}")
        logger.info(f"   Notice ID: {opp.get('noticeId', 'N/A')}")
        logger.info(f"   Department: {opp.get('fullParentPathName', 'N/A')}")
        logger.info(f"   Posted: {opp.get('postedDate', 'N/A')}")
        logger.info(f"   Deadline: {opp.get('responseDeadLine', 'N/A')}")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✓ GovWin ID 256560 found: Yes")
    logger.info(f"✓ SAM.gov HRIT opportunities found: {len(sam_opportunities)}")
    logger.info(f"✓ GovWin HRIT search results: {len(all_results)}")

    # Check if GovWin 256560 matches any SAM opportunities
    if sam_opportunities and opportunity:
        logger.info(f"\n--- Potential Match Analysis ---")
        logger.info(f"GovWin 256560 Title: {opportunity.get('title', 'N/A')}")
        for sam_opp in sam_opportunities:
            sam_title = sam_opp.get('title', 'N/A')
            if 'HRIT' in sam_title and 'OPM' in sam_opp.get('fullParentPathName', ''):
                logger.info(f"  ✓ Likely match: {sam_title}")
                logger.info(f"    SAM Notice ID: {sam_opp.get('noticeId')}")

if __name__ == "__main__":
    test_govwin_hrit()
