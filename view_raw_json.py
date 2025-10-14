#!/usr/bin/env python
"""
Script to view the raw JSON response from the SAM.gov API.
"""
import json
import requests
from app.config import SAM_API_KEY, SAM_API_BASE_URL

def main():
    """
    Make a direct API call and print the raw JSON response.
    """
    # Define parameters for the API call
    params = {
        'api_key': SAM_API_KEY,
        'ptype': 'k',  # Combined Synopsis/Solicitation
        'ncode': '541330',  # Engineering Services
        'postedFrom': '05/01/2025',
        'postedTo': '05/21/2025',
        'limit': 2,
        'offset': 0
    }
    
    # Build the URL
    url = f"{SAM_API_BASE_URL}?{requests.compat.urlencode(params, doseq=True)}"
    
    print(f"Making API call to: {url}")
    
    try:
        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        # Print the raw JSON response
        print("\nRaw JSON Response:")
        print(json.dumps(data, indent=2))
        
        # Save the raw JSON response to a file
        with open("raw_sam_response.json", "w") as f:
            json.dump(data, f, indent=2)
            print("\nRaw JSON response saved to raw_sam_response.json")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
