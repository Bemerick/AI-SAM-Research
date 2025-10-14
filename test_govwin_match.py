"""
Test script to verify GovWin matching for the HRIT opportunity.

The user reported finding a match for the Federal Human Resources Information
Technology (HRIT) Modernization opportunity in GovWin, with GovWin ID = 256560.

This script will:
1. Search for the HRIT opportunity in SAM.gov
2. Search for related opportunities in GovWin
3. Verify that GovWin ID 256560 appears in the results
"""
import logging
import json
from app.sam_client import SAMClient
from app.govwin_client import GovWinClient
from app.config import SAM_API_KEY, GOVWIN_USERNAME, GOVWIN_PASSWORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_hrit_match():
    """Test matching for the HRIT opportunity."""

    # Initialize clients
    logger.info("Initializing SAM.gov and GovWin clients...")
    sam_client = SAMClient(api_key=SAM_API_KEY)
    govwin_client = GovWinClient(username=GOVWIN_USERNAME, password=GOVWIN_PASSWORD)

    # Step 1: Search for HRIT opportunity in SAM.gov
    logger.info("=" * 80)
    logger.info("STEP 1: Searching for HRIT opportunity in SAM.gov")
    logger.info("=" * 80)

    # Search by title keywords
    result = sam_client.search_opportunities(
        title="Human Resources Information Technology Modernization",
        limit=10
    )

    sam_opportunities = result.get('opportunitiesData', [])
    logger.info(f"Found {len(sam_opportunities)} opportunities matching 'HRIT Modernization'")

    if not sam_opportunities:
        logger.warning("No HRIT opportunities found in SAM.gov. Trying broader search...")
        result = sam_client.search_opportunities(
            title="HRIT",
            limit=10
        )
        sam_opportunities = result.get('opportunitiesData', [])
        logger.info(f"Found {len(sam_opportunities)} opportunities matching 'HRIT'")

    if not sam_opportunities:
        logger.error("Could not find HRIT opportunity in SAM.gov")
        return

    # Display found opportunities
    for i, opp in enumerate(sam_opportunities, 1):
        logger.info(f"\n{i}. {opp.get('title', 'N/A')}")
        logger.info(f"   Notice ID: {opp.get('noticeId', 'N/A')}")
        logger.info(f"   Department: {opp.get('fullParentPathName', 'N/A')}")
        logger.info(f"   Posted: {opp.get('postedDate', 'N/A')}")

    # Use the first opportunity for testing
    sam_opp = sam_opportunities[0]
    logger.info(f"\nUsing opportunity: {sam_opp.get('title', 'N/A')}")

    # Step 2: Search GovWin for related opportunities
    logger.info("=" * 80)
    logger.info("STEP 2: Searching GovWin for related opportunities")
    logger.info("=" * 80)

    # Extract keywords from SAM opportunity
    sam_title = sam_opp.get('title', '')
    logger.info(f"Searching GovWin with keywords from: {sam_title}")

    # Try different search strategies
    search_terms = [
        "Human Resources Information Technology Modernization",
        "HRIT Modernization",
        "Federal HRIT",
        "OPM HRIT",
    ]

    all_govwin_matches = []

    for search_term in search_terms:
        logger.info(f"\n--- Searching GovWin for: '{search_term}' ---")
        try:
            govwin_results = govwin_client.search_opportunities(
                keywords=search_term,
                max_results=10
            )

            logger.info(f"Found {len(govwin_results)} GovWin opportunities for '{search_term}'")

            for gw_opp in govwin_results:
                gw_id = gw_opp.get('id')
                if gw_id not in [m.get('id') for m in all_govwin_matches]:
                    all_govwin_matches.append(gw_opp)
                    logger.info(f"  - ID: {gw_id} | {gw_opp.get('title', 'N/A')[:70]}")

                    # Check if this is the expected match
                    if str(gw_id) == "256560":
                        logger.info(f"  ✓✓✓ FOUND EXPECTED MATCH! GovWin ID 256560 ✓✓✓")

        except Exception as e:
            logger.error(f"Error searching GovWin for '{search_term}': {e}")
            continue

    # Step 3: Verify if GovWin ID 256560 was found
    logger.info("=" * 80)
    logger.info("STEP 3: Verification")
    logger.info("=" * 80)

    found_256560 = any(str(gw.get('id')) == "256560" for gw in all_govwin_matches)

    if found_256560:
        logger.info("✓ SUCCESS: Found GovWin ID 256560 in search results!")

        # Get details of the match
        match_256560 = next(gw for gw in all_govwin_matches if str(gw.get('id')) == "256560")
        logger.info(f"\nGovWin Match Details (ID 256560):")
        logger.info(f"  Title: {match_256560.get('title', 'N/A')}")
        logger.info(f"  Agency: {match_256560.get('agency', 'N/A')}")
        logger.info(f"  Posted: {match_256560.get('posted_date', 'N/A')}")
        logger.info(f"  Value: {match_256560.get('value', 'N/A')}")

        # Save the match details
        output = {
            "sam_opportunity": {
                "notice_id": sam_opp.get('noticeId'),
                "title": sam_opp.get('title'),
                "department": sam_opp.get('fullParentPathName'),
                "posted_date": sam_opp.get('postedDate')
            },
            "govwin_match": match_256560,
            "match_verified": True
        }

        with open('hrit_govwin_match_test.json', 'w') as f:
            json.dump(output, f, indent=2)
        logger.info("\nMatch details saved to: hrit_govwin_match_test.json")

    else:
        logger.warning("✗ GovWin ID 256560 NOT found in search results")
        logger.info(f"\nTotal unique GovWin opportunities found: {len(all_govwin_matches)}")

        # Try direct lookup by ID
        logger.info("\nAttempting direct lookup of GovWin ID 256560...")
        try:
            direct_result = govwin_client.get_opportunity_by_id("256560")
            if direct_result:
                logger.info("✓ Direct lookup successful!")
                logger.info(f"  Title: {direct_result.get('title', 'N/A')}")
                logger.info(f"  Agency: {direct_result.get('agency', 'N/A')}")
        except Exception as e:
            logger.error(f"Direct lookup failed: {e}")

    logger.info("=" * 80)
    logger.info("Test complete!")

if __name__ == "__main__":
    test_hrit_match()
