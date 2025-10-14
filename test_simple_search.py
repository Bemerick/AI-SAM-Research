#!/usr/bin/env python
"""
Simple test script to understand the basic requirements of the SAM.gov API.
"""
import json
from app.sam_client import SAMClient

def main():
    """
    Main function to test a simple search with minimal parameters.
    """
    # Initialize the SAM client
    client = SAMClient()
    
    print("Testing simple search with minimal parameters")
    
    # Use a very narrow date range (30 days)
    posted_from = "04/21/2025"  # 30 days before current date
    posted_to = "05/21/2025"    # Current date
    
    # Try with just one procurement type
    p_type = ["k"]  # k = Combined Synopsis/Solicitation
    
    try:
        # Make a simple search with minimal parameters
        result = client.search_opportunities(
            p_type=p_type,
            posted_from=posted_from,
            posted_to=posted_to,
            limit=5
        )
        
        # Print the total number of records found
        total_records = result.get("totalRecords", 0)
        print(f"Found {total_records} opportunities")
        
        # Print details of each opportunity
        opportunities = result.get("opportunitiesData", [])
        for i, opp in enumerate(opportunities, 1):
            print(f"\nOpportunity {i}:")
            print(f"  Title: {opp.get('title')}")
            print(f"  Notice ID: {opp.get('noticeId')}")
            print(f"  Department: {opp.get('department')}")
            print(f"  Posted Date: {opp.get('postedDate')}")
            print(f"  Type: {opp.get('type')}")
            
        # Save the full JSON response to a file for reference
        with open("sam_simple_search_results.json", "w") as f:
            json.dump(result, f, indent=2)
            print("\nFull results saved to sam_simple_search_results.json")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
