#!/usr/bin/env python
"""
Test script to search for SAM.gov opportunities containing specific key terms
in both their titles and descriptions.

This script searches for opportunities:
1. With specific procurement types (p, r, o, k)
2. Posted within the last 5 days
3. Containing specified key terms in either title or description
"""
import json
import re
from datetime import datetime, timedelta
from app.sam_client import SAMClient

def search_for_keywords(text, keywords):
    """
    Search for keywords in text.
    
    Args:
        text: The text to search in.
        keywords: List of keywords to search for.
        
    Returns:
        A list of found keywords.
    """
    if not text:
        return []
    
    # Convert text to lowercase for case-insensitive search
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in keywords:
        # Use word boundaries to find whole words/phrases
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_keywords.append(keyword)
    
    return found_keywords

def main():
    """
    Main function to search for opportunities with specific key terms.
    """
    # Initialize the SAM client
    client = SAMClient()
    
    # Define key terms to search for
    key_terms = ["financial assessment", "human capital", "workforce"]
    print(f"Searching for opportunities containing any of these key terms: {', '.join(key_terms)}")
    
    # Set procurement types
    p_types = ["p", "r", "o", "k"]
    p_type_descriptions = {
        "p": "Presolicitation",
        "r": "Sources Sought",
        "o": "Solicitation",
        "k": "Combined Synopsis/Solicitation"
    }
    print(f"Limiting to procurement types: {', '.join([p_type_descriptions.get(pt, pt) for pt in p_types])}")
    
    # Set date range (last 5 days)
    today = datetime.now()
    five_days_ago = today - timedelta(days=5)
    posted_from = five_days_ago.strftime("%m/%d/%Y")
    posted_to = today.strftime("%m/%d/%Y")
    print(f"Searching for opportunities posted between {posted_from} and {posted_to}")
    
    # Make the API call
    try:
        # Search for opportunities with the specified parameters
        result = client.search_opportunities(
            p_type=p_types,
            posted_from=posted_from,
            posted_to=posted_to,
            limit=50,  # Increase limit to get more results
            include_description=True  # Fetch descriptions for keyword search
        )
        
        # Get the total number of records
        total_records = result.get("totalRecords", 0)
        print(f"Found {total_records} total opportunities matching the date and procurement type criteria")
        
        # Filter opportunities based on key terms in title or description
        matching_opportunities = []
        opportunities = result.get("opportunitiesData", [])
        
        for opp in opportunities:
            title = opp.get("title", "")
            description = opp.get("descriptionText", "")
            
            # Search for key terms in title
            title_matches = search_for_keywords(title, key_terms)
            
            # Search for key terms in description
            description_matches = search_for_keywords(description, key_terms)
            
            # Combine unique matches
            all_matches = list(set(title_matches + description_matches))
            
            if all_matches:
                # Add matches to the opportunity data
                opp["keywordMatches"] = all_matches
                matching_opportunities.append(opp)
        
        # Print results
        print(f"\nFound {len(matching_opportunities)} opportunities containing the specified key terms")
        
        # Print details of each matching opportunity
        for i, opp in enumerate(matching_opportunities, 1):
            print(f"\nOpportunity {i}:")
            print(f"  Title: {opp.get('title')}")
            print(f"  Notice ID: {opp.get('noticeId')}")
            print(f"  Solicitation Number: {opp.get('solicitationNumber')}")
            print(f"  Department: {opp.get('fullParentPathName', '').split('.')[0] if opp.get('fullParentPathName') else 'N/A'}")
            print(f"  Posted Date: {opp.get('postedDate')}")
            print(f"  Type: {opp.get('type')}")
            print(f"  Matching Keywords: {', '.join(opp.get('keywordMatches', []))}")
            
            # Print the response deadline if available
            if opp.get('responseDeadLine'):
                print(f"  Response Deadline: {opp.get('responseDeadLine')}")
            
            # Print a snippet of the description with context around the matching keywords
            if opp.get('descriptionText'):
                description = opp.get('descriptionText')
                
                # For each matching keyword in the description, show context
                for keyword in opp.get('keywordMatches', []):
                    if keyword in description.lower():
                        # Find the position of the keyword
                        start_pos = description.lower().find(keyword.lower())
                        if start_pos >= 0:
                            # Get context (100 chars before and after)
                            context_start = max(0, start_pos - 100)
                            context_end = min(len(description), start_pos + len(keyword) + 100)
                            context = description[context_start:context_end]
                            
                            # Add ellipsis if we're not at the beginning or end
                            if context_start > 0:
                                context = "..." + context
                            if context_end < len(description):
                                context = context + "..."
                                
                            print(f"\n  Context for '{keyword}':")
                            print(f"    {context}")
            
            # Print the link to view the opportunity on SAM.gov
            if opp.get('uiLink'):
                print(f"\n  View on SAM.gov: {opp.get('uiLink')}")
        
        # Save the matching opportunities to a file
        if matching_opportunities:
            output_data = {
                "searchCriteria": {
                    "keyTerms": key_terms,
                    "procurementTypes": p_types,
                    "dateRange": {
                        "from": posted_from,
                        "to": posted_to
                    }
                },
                "totalMatches": len(matching_opportunities),
                "opportunities": matching_opportunities
            }
            
            with open("keyword_search_results.json", "w") as f:
                json.dump(output_data, f, indent=2)
                print("\nFull results saved to keyword_search_results.json")
        else:
            print("\nNo matching opportunities found.")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
