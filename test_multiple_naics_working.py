#!/usr/bin/env python
"""
Test script to demonstrate searching SAM.gov opportunities with multiple NAICS codes.
This version uses a working approach with a 30-day date range.
"""
import json
from app.sam_client import SAMClient

def main():
    """
    Main function to test searching with multiple NAICS codes.
    """
    # Initialize the SAM client
    client = SAMClient()
    
    # Define multiple NAICS codes for testing
    # Common NAICS codes for government contracting:
    # 541330 - Engineering Services
    # 541512 - Computer Systems Design Services
    # 541511 - Custom Computer Programming Services
    naics_codes = ["541330", "541512", "541511"]
    
    print(f"Searching for opportunities with multiple NAICS codes: {', '.join(naics_codes)}")
    
    # Use a narrow date range (30 days) that works with the API
    posted_from = "04/21/2025"  # 30 days before current date
    posted_to = "05/21/2025"    # Current date
    
    # Set procurement type
    p_type = ["k"]  # k = Combined Synopsis/Solicitation
    
    # Make separate API calls for each NAICS code and combine results
    all_opportunities = []
    unique_notice_ids = set()
    total_records = 0
    
    for naics_code in naics_codes:
        print(f"\nSearching for opportunities with NAICS code: {naics_code}")
        try:
            result = client.search_opportunities(
                p_type=p_type,
                naics_code=naics_code,
                posted_from=posted_from,
                posted_to=posted_to,
                limit=5  # Limit to 5 results per NAICS code for brevity
            )
            
            # Add to total records count
            records_found = result.get("totalRecords", 0)
            total_records += records_found
            print(f"Found {records_found} opportunities for NAICS code {naics_code}")
            
            # Add unique opportunities to our combined list
            opportunities = result.get("opportunitiesData", [])
            for opp in opportunities:
                notice_id = opp.get("noticeId")
                if notice_id not in unique_notice_ids:
                    unique_notice_ids.add(notice_id)
                    all_opportunities.append(opp)
                    
        except Exception as e:
            print(f"Error searching for NAICS code {naics_code}: {str(e)}")
    
    # Print summary of combined results
    print(f"\nTotal records across all NAICS codes: {total_records}")
    print(f"Unique opportunities found: {len(all_opportunities)}")
    
    # Print details of each unique opportunity
    for i, opp in enumerate(all_opportunities, 1):
        print(f"\nOpportunity {i}:")
        print(f"  Title: {opp.get('title')}")
        print(f"  Notice ID: {opp.get('noticeId')}")
        print(f"  Solicitation Number: {opp.get('solicitationNumber')}")
        print(f"  Department: {opp.get('department')}")
        print(f"  Posted Date: {opp.get('postedDate')}")
        print(f"  Type: {opp.get('type')}")
        print(f"  NAICS Code: {opp.get('naicsCode')}")
        
        # Print the response deadline if available
        if opp.get('responseDeadLine'):
            print(f"  Response Deadline: {opp.get('responseDeadLine')}")
            
        # Print award information if available
        if opp.get('award'):
            award = opp.get('award')
            print("  Award Information:")
            print(f"    Date: {award.get('date')}")
            print(f"    Number: {award.get('number')}")
            print(f"    Amount: ${award.get('amount')}")
            
            # Print awardee information if available
            if award.get('awardee'):
                awardee = award.get('awardee')
                print(f"    Awardee: {awardee.get('name')}")
    
    # Save the combined results to a file for reference
    combined_results = {
        "totalRecords": total_records,
        "uniqueRecords": len(all_opportunities),
        "opportunitiesData": all_opportunities
    }
    
    with open("sam_multiple_naics_results.json", "w") as f:
        json.dump(combined_results, f, indent=2)
        print("\nFull results saved to sam_multiple_naics_results.json")

if __name__ == "__main__":
    main()
