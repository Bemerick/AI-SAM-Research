#!/usr/bin/env python
"""
Test script to demonstrate retrieving SAM.gov opportunities with their descriptions.
"""
import json
from app.sam_client import SAMClient

def main():
    """
    Main function to test retrieving opportunities with descriptions.
    """
    # Initialize the SAM client
    client = SAMClient()
    
    # Use a narrow date range (30 days) that works with the API
    posted_from = "04/21/2025"  # 30 days before current date
    posted_to = "05/21/2025"    # Current date
    
    # Set procurement type
    p_type = ["k"]  # k = Combined Synopsis/Solicitation
    
    # Pick a single NAICS code for this test
    naics_code = "541330"  # Engineering Services
    
    print(f"Searching for opportunities with NAICS code {naics_code} and retrieving descriptions")
    
    try:
        # Search for opportunities and include descriptions
        result = client.search_opportunities(
            p_type=p_type,
            naics_code=naics_code,
            posted_from=posted_from,
            posted_to=posted_to,
            limit=2,  # Limit to 2 results for brevity
            include_description=True  # This will fetch descriptions
        )
        
        # Print the total number of records found
        total_records = result.get("totalRecords", 0)
        print(f"Found {total_records} opportunities for NAICS code {naics_code}")
        
        # Print details of each opportunity including description
        opportunities = result.get("opportunitiesData", [])
        for i, opp in enumerate(opportunities, 1):
            print(f"\nOpportunity {i}:")
            print(f"  Title: {opp.get('title')}")
            print(f"  Notice ID: {opp.get('noticeId')}")
            print(f"  Solicitation Number: {opp.get('solicitationNumber')}")
            print(f"  Department: {opp.get('fullParentPathName', '').split('.')[0]}")
            print(f"  Posted Date: {opp.get('postedDate')}")
            print(f"  Type: {opp.get('type')}")
            print(f"  NAICS Code: {opp.get('naicsCode')}")
            
            # Print the response deadline if available
            if opp.get('responseDeadLine'):
                print(f"  Response Deadline: {opp.get('responseDeadLine')}")
            
            # Print the description if available
            if opp.get('descriptionText'):
                # Truncate the description if it's too long
                description = opp.get('descriptionText')
                if len(description) > 500:
                    description = description[:500] + "... [truncated]"
                print(f"\n  Description: {description}")
            else:
                print("\n  Description: Not available")
            
            # Print the link to view the opportunity on SAM.gov
            if opp.get('uiLink'):
                print(f"\n  View on SAM.gov: {opp.get('uiLink')}")
        
        # Save the full JSON response to a file for reference
        with open("sam_with_descriptions.json", "w") as f:
            json.dump(result, f, indent=2)
            print("\nFull results saved to sam_with_descriptions.json")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
