#!/usr/bin/env python
"""
Test script to search GovWin for opportunities matching high-scoring SAM.gov opportunities.
This validates the matching concept before building the full AI agent architecture.
"""
import json
import sys
import os
from pathlib import Path

# Add the AI-Govwin directory to the path to import govwin_client
sys.path.insert(0, str(Path(__file__).parent.parent / "AI-Govwin"))

from govwin_client import GovWinClient


def load_high_scoring_sam_opportunities(json_file="opportunity_analysis.json", min_score=6):
    """Load SAM opportunities with fit_score > min_score."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    ranked_opps = data.get("ranked_opportunities", [])
    high_scoring = [opp for opp in ranked_opps if opp.get("fit_score", 0) > min_score]

    print(f"Found {len(high_scoring)} opportunities with fit_score > {min_score}")
    return high_scoring


def extract_agency_name(full_parent_path):
    """
    Extract the top-level agency name from fullParentPathName.
    Example: "HOMELAND SECURITY, DEPARTMENT OF.US COAST GUARD..." -> "HOMELAND SECURITY"
    """
    if not full_parent_path:
        return None

    # Split on periods and take the first part
    parts = full_parent_path.split('.')
    if parts:
        # Remove common suffixes like ", DEPARTMENT OF"
        agency = parts[0].replace(", DEPARTMENT OF", "").strip()
        return agency
    return None


def extract_title_keywords(title, max_keywords=5):
    """
    Extract meaningful keywords from the opportunity title.
    Removes common stop words and returns the most relevant terms.
    """
    if not title:
        return []

    # Common stop words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can'
    }

    # Split title into words and filter
    words = title.lower().split()
    keywords = [
        word.strip('.,;:!?()[]{}"\'-')
        for word in words
        if len(word) > 3 and word.lower() not in stop_words
    ]

    # Return up to max_keywords
    return keywords[:max_keywords]


def search_govwin_for_match(govwin_client, sam_opp):
    """
    Search GovWin for opportunities matching the SAM opportunity.
    Uses agency name, NAICS code, and title keywords.
    """
    print("\n" + "="*80)
    print(f"SAM Opportunity: {sam_opp.get('title')}")
    print(f"Notice ID: {sam_opp.get('noticeId')}")
    print(f"Fit Score: {sam_opp.get('fit_score')}")
    print(f"Department: {sam_opp.get('department')}")
    print(f"NAICS Code: {sam_opp.get('naicsCode')}")
    print(f"Full Parent Path: {sam_opp.get('fullParentPathName')}")
    print("="*80)

    # Extract search parameters
    agency_name = extract_agency_name(sam_opp.get('fullParentPathName'))
    naics_code = sam_opp.get('naicsCode')
    title = sam_opp.get('title', '')
    title_keywords = extract_title_keywords(title)

    print(f"\nExtracted Agency: {agency_name}")
    print(f"Title Keywords: {', '.join(title_keywords)}")
    print(f"Search Strategy: Using agency name, title keywords, and/or NAICS code")

    # Strategy 1: Search by keyword (agency name)
    print("\n--- Strategy 1: Search by Keyword (Agency Name) ---")
    search_params_keyword = {}
    if agency_name:
        search_params_keyword['q'] = agency_name
        search_params_keyword['max'] = 10

    if search_params_keyword:
        try:
            print(f"Searching GovWin with params: {search_params_keyword}")
            response = govwin_client.search_opportunities(search_params_keyword)

            # Extract opportunities list from response
            results_keyword = response.get('opportunities', []) if isinstance(response, dict) else response
            print(f"Found {len(results_keyword)} opportunities by keyword")

            # Display first 5 results
            for i, opp in enumerate(results_keyword[:5], 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {opp.get('id')}")
                print(f"    Title: {opp.get('title')}")
                print(f"    Type: {opp.get('type')}")
                print(f"    Gov Entity: {opp.get('govEntity', {}).get('title', 'N/A')}")
        except Exception as e:
            print(f"Error searching by keyword: {e}")
            results_keyword = []
    else:
        results_keyword = []

    # Strategy 2: Search by NAICS code
    print("\n--- Strategy 2: Search by NAICS Code ---")
    search_params_naics = {}
    if naics_code:
        search_params_naics['naics'] = naics_code  # Note: parameter name is 'naics', not 'naicsCode'
        search_params_naics['max'] = 10

    if search_params_naics:
        try:
            print(f"Searching GovWin with params: {search_params_naics}")
            response = govwin_client.search_opportunities(search_params_naics)

            # Extract opportunities list from response
            results_naics = response.get('opportunities', []) if isinstance(response, dict) else response
            print(f"Found {len(results_naics)} opportunities by NAICS")

            # Display first 5 results
            for i, opp in enumerate(results_naics[:5], 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {opp.get('id')}")
                print(f"    Title: {opp.get('title')}")
                print(f"    Type: {opp.get('type')}")
                print(f"    Primary NAICS: {opp.get('primaryNAICS', {}).get('id', 'N/A')}")
        except Exception as e:
            print(f"Error searching by NAICS: {e}")
            results_naics = []
    else:
        results_naics = []

    # Strategy 3: Search by title keywords
    print("\n--- Strategy 3: Search by Title Keywords ---")
    search_params_title = {}
    if title_keywords:
        # Join keywords with space for broader search
        search_params_title['q'] = ' '.join(title_keywords)
        search_params_title['max'] = 10

    if search_params_title:
        try:
            print(f"Searching GovWin with params: {search_params_title}")
            response = govwin_client.search_opportunities(search_params_title)

            # Extract opportunities list from response
            results_title = response.get('opportunities', []) if isinstance(response, dict) else response
            print(f"Found {len(results_title)} opportunities by title keywords")

            # Display first 5 results
            for i, opp in enumerate(results_title[:5], 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {opp.get('id')}")
                print(f"    Title: {opp.get('title')}")
                print(f"    Type: {opp.get('type')}")
                print(f"    Gov Entity: {opp.get('govEntity', {}).get('title', 'N/A')}")
        except Exception as e:
            print(f"Error searching by title keywords: {e}")
            results_title = []
    else:
        results_title = []

    # Strategy 4: Combined search (agency + NAICS)
    print("\n--- Strategy 4: Search by Agency + NAICS ---")
    search_params_combined = {}
    if agency_name:
        search_params_combined['q'] = agency_name
    if naics_code:
        search_params_combined['naics'] = naics_code
    search_params_combined['max'] = 10

    if len(search_params_combined) > 1:
        try:
            print(f"Searching GovWin with params: {search_params_combined}")
            response = govwin_client.search_opportunities(search_params_combined)

            # Extract opportunities list from response
            results_combined = response.get('opportunities', []) if isinstance(response, dict) else response
            print(f"Found {len(results_combined)} opportunities by agency + NAICS")

            # Display all results for combined search (likely more specific)
            for i, opp in enumerate(results_combined, 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {opp.get('id')}")
                print(f"    Title: {opp.get('title')}")
                print(f"    Type: {opp.get('type')}")
                print(f"    Gov Entity: {opp.get('govEntity', {}).get('title', 'N/A')}")
                print(f"    Primary NAICS: {opp.get('primaryNAICS', {}).get('id', 'N/A')}")
                print(f"    Description: {opp.get('description', '')[:200]}...")
        except Exception as e:
            print(f"Error searching by agency + NAICS: {e}")
            results_combined = []
    else:
        results_combined = []

    # Strategy 5: Multi-keyword search (title keywords + NAICS)
    print("\n--- Strategy 5: Search by Title Keywords + NAICS ---")
    search_params_multi = {}
    if title_keywords:
        search_params_multi['q'] = ' '.join(title_keywords)
    if naics_code:
        search_params_multi['naics'] = naics_code
    search_params_multi['max'] = 10

    if len(search_params_multi) > 1:
        try:
            print(f"Searching GovWin with params: {search_params_multi}")
            response = govwin_client.search_opportunities(search_params_multi)

            # Extract opportunities list from response
            results_multi = response.get('opportunities', []) if isinstance(response, dict) else response
            print(f"Found {len(results_multi)} opportunities by title keywords + NAICS")

            # Display all results
            for i, opp in enumerate(results_multi, 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {opp.get('id')}")
                print(f"    Title: {opp.get('title')}")
                print(f"    Type: {opp.get('type')}")
                print(f"    Gov Entity: {opp.get('govEntity', {}).get('title', 'N/A')}")
                print(f"    Primary NAICS: {opp.get('primaryNAICS', {}).get('id', 'N/A')}")
                print(f"    Description: {opp.get('description', '')[:200]}...")
        except Exception as e:
            print(f"Error searching by title keywords + NAICS: {e}")
            results_multi = []
    else:
        results_multi = []

    return {
        'sam_opportunity': sam_opp,
        'keyword_results': results_keyword,
        'naics_results': results_naics,
        'title_results': results_title,
        'combined_results': results_combined,
        'multi_results': results_multi
    }


def main():
    """Main test function."""
    print("GovWin Matching Test Script")
    print("="*80)

    # Load high-scoring SAM opportunities
    try:
        sam_opportunities = load_high_scoring_sam_opportunities(min_score=6)
    except FileNotFoundError:
        print("Error: opportunity_analysis.json not found.")
        print("Run analyze_opportunities.py first to generate the analysis file.")
        return

    if not sam_opportunities:
        print("No opportunities with fit_score > 6 found.")
        return

    # Initialize GovWin client
    print("\nInitializing GovWin client...")
    try:
        govwin_client = GovWinClient()
        govwin_client.authenticate()
        print("✓ GovWin client authenticated successfully")
    except Exception as e:
        print(f"Error initializing GovWin client: {e}")
        print("Check your GovWin API credentials in the .env file")
        return

    # Test with the first high-scoring opportunity
    print("\nTesting with first high-scoring opportunity...")
    test_opp = sam_opportunities[0]

    results = search_govwin_for_match(govwin_client, test_opp)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"SAM Opportunity: {test_opp.get('title')}")
    print(f"Agency Keyword Search Results: {len(results['keyword_results'])} opportunities")
    print(f"NAICS Search Results: {len(results['naics_results'])} opportunities")
    print(f"Title Keywords Search Results: {len(results['title_results'])} opportunities")
    print(f"Agency + NAICS Combined Results: {len(results['combined_results'])} opportunities")
    print(f"Title Keywords + NAICS Results: {len(results['multi_results'])} opportunities")

    # Save results to file
    output_file = "govwin_match_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to {output_file}")

    print("\n" + "="*80)
    print("Test complete. Review the results to assess matching quality.")
    print("Next steps:")
    print("1. Manually evaluate if any GovWin results match the SAM opportunity")
    print("2. Refine search strategies based on results")
    print("3. Design AI evaluation logic for automated matching")
    print("="*80)


if __name__ == "__main__":
    main()
