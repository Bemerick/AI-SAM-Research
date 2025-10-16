import os
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Union
import time

class GovWinClient:
    """
    Client for interacting with the GovWin WSAPI.
    Handles authentication and retrieval of opportunities.
    """
    
    BASE_URL = "https://services.govwin.com/neo-ws"
    TOKEN_URL = f"{BASE_URL}/oauth/token"
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, 
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the GovWin client with credentials.
        
        Args:
            client_id: The client ID for OAuth2 authentication
            client_secret: The client secret for OAuth2 authentication
            username: The username for authentication
            password: The password for authentication
        """
        # Load environment variables
        load_dotenv()
        
        # Set credentials from parameters or environment variables
        self.client_id = client_id or os.getenv("GOVWIN_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GOVWIN_CLIENT_SECRET")
        self.username = username or os.getenv("GOVWIN_USERNAME")
        self.password = password or os.getenv("GOVWIN_PASSWORD")
        
        # Validate credentials
        if not all([self.client_id, self.client_secret, self.username, self.password]):
            raise ValueError("Missing credentials. Please provide client_id, client_secret, username, and password.")
        
        # Authentication state
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        
        # Authenticate on initialization
        self.authenticate()
    
    def authenticate(self) -> None:
        """
        Authenticate with the GovWin WSAPI using OAuth2 password grant type.
        Sets the access_token, refresh_token, and token_expires_at properties.
        """
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
            'scope': 'read'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip,deflate'
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=payload, headers=headers)

            # Handle authentication errors with detailed feedback
            if response.status_code == 400:
                error_data = response.json() if response.text else {}
                error_type = error_data.get('error', 'unknown')
                error_desc = error_data.get('error_description', 'No description provided')
                print(f"Authentication failed: {response.status_code} Client Error: {response.reason} for url: {self.TOKEN_URL}")
                print(f"Error: {error_type}")
                print(f"Description: {error_desc}")
                raise ValueError(f"GovWin authentication failed: {error_type} - {error_desc}")

            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            self.token_expires_at = time.time() + token_data['expires_in']

            print("Authentication successful.")
        except ValueError:
            # Re-raise ValueError (authentication errors)
            raise
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            raise
    
    def refresh_auth_token(self) -> None:
        """
        Refresh the access token using the refresh token.
        """
        if not self.refresh_token:
            self.authenticate()
            return
        
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip,deflate'
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            self.token_expires_at = time.time() + token_data['expires_in']
            
            print("Token refresh successful.")
        except:
            # If refresh fails, try full authentication
            print("Token refresh failed. Attempting full authentication.")
            self.authenticate()
    
    def ensure_valid_token(self) -> None:
        """
        Ensure that the access token is valid, refreshing if necessary.
        """
        # Add a buffer of 60 seconds to avoid edge cases
        if time.time() > (self.token_expires_at - 60):
            self.refresh_auth_token()
    
    def make_api_request(self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make an authenticated request to the GovWin WSAPI.
        
        Args:
            endpoint: The API endpoint to call (without the base URL)
            method: The HTTP method to use (GET, POST, etc.)
            data: Optional data to send with the request
            
        Returns:
            The JSON response from the API
        """
        self.ensure_valid_token()
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept-Encoding': 'gzip,deflate'
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Print response status and URL for debugging
            print(f"API Request: {method} {url}")
            print(f"Status Code: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                # Check if token is invalid
                try:
                    error_data = response.json()
                    if error_data.get('error') == 'invalid_token':
                        print("Token expired. Refreshing...")
                        self.refresh_auth_token()
                        # Retry the request
                        return self.make_api_request(endpoint, method, data)
                except:
                    pass
            
            print(f"API request failed: {e}")
            # Try to print response body for more details
            try:
                error_body = response.text
                print(f"Error details: {error_body}")
            except:
                pass
            raise
    
    def get_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Retrieve a single opportunity by ID.
        
        Args:
            opportunity_id: The ID of the opportunity to retrieve
            
        Returns:
            The opportunity data
        """
        endpoint = f"opportunities/{opportunity_id}"
        response = self.make_api_request(endpoint)
        
        # Extract the opportunity from the response
        if 'opportunities' in response and isinstance(response['opportunities'], list) and len(response['opportunities']) > 0:
            return response['opportunities'][0]
        return response
    
    def get_opportunity_attribute(self, opportunity_id: str, attribute_name: str) -> Dict[str, Any]:
        """
        Get extended attribute information for a specific opportunity.
        
        Args:
            opportunity_id: The ID of the opportunity
            attribute_name: The name of the attribute to retrieve
            
        Returns:
            The attribute data
        """
        endpoint = f"opportunities/{opportunity_id}/{attribute_name}"
        return self.make_api_request(endpoint)
    
    def get_opportunity_milestones(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Get milestones for a specific opportunity.
        
        Args:
            opportunity_id: The ID of the opportunity
            
        Returns:
            The milestones data
        """
        return self.get_opportunity_attribute(opportunity_id, "milestones")
    
    def get_opportunity_assessment(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Get assessment data for a specific opportunity.

        Args:
            opportunity_id: The ID of the opportunity

        Returns:
            The assessment data
        """
        return self.get_opportunity_attribute(opportunity_id, "assessment")

    def get_opportunity_contracts(self, opportunity_id: str) -> List[Dict[str, Any]]:
        """
        Get contracts for a specific opportunity.

        Args:
            opportunity_id: The ID of the opportunity

        Returns:
            List of contract data
        """
        response = self.get_opportunity_attribute(opportunity_id, "contracts")
        # Extract contracts array from response
        if isinstance(response, dict) and 'contracts' in response:
            return response['contracts']
        return []
    
    def get_opportunities(self, opportunity_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple opportunities by ID.
        Uses the batch endpoint that allows retrieving up to 10 opportunities in a single request.
        
        Args:
            opportunity_ids: A list of opportunity IDs to retrieve
            
        Returns:
            A list of opportunity data
        """
        results = []
        
        # Process in batches of 10 (API limit)
        for i in range(0, len(opportunity_ids), 10):
            batch = opportunity_ids[i:i+10]
            try:
                # Join IDs with commas for the batch endpoint
                ids_string = ",".join(batch)
                endpoint = f"opportunities/{ids_string}"
                batch_results = self.make_api_request(endpoint)
                
                # Extract opportunities from the response
                if 'opportunities' in batch_results and isinstance(batch_results['opportunities'], list):
                    batch_data = batch_results['opportunities']
                    print(f"Found {len(batch_data)} opportunities in batch")
                    results.extend(batch_data)
                    
                    # Print summary of retrieved opportunities
                    for opp in batch_data:
                        opp_id = opp.get('id') or opp.get('iqOppId', 'Unknown ID')
                        opp_title = opp.get('title', 'Unknown Title')
                        print(f"Retrieved: {opp_id} - {opp_title}")
                else:
                    print("No opportunities found in response")
                
            except Exception as e:
                print(f"Failed to retrieve opportunities {', '.join(batch)}: {e}")
        
        return results
    
    def search_opportunities(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve a list of opportunities by search parameters.
        
        Args:
            search_params: Dictionary of search parameters
            
        Returns:
            A list of opportunity data
        """
        endpoint = "opportunities"
        return self.make_api_request(endpoint, method="GET", data=search_params)
    
    def get_opportunities_by_saved_search(self, search_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve a list of opportunities by saved search ID.
        
        Args:
            search_id: The saved search ID
            
        Returns:
            A list of opportunity data
        """
        endpoint = "opportunities"
        params = {"savedSearchId": search_id}
        return self.make_api_request(endpoint, method="GET", data=params)
    
    def get_marked_opportunities(self, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve a list of this organization's opportunities selected for download.
        
        Args:
            version: Optional version parameter ("2" or "2.2")
            
        Returns:
            A list of opportunity data
        """
        endpoint = "opportunities"
        params = {}
        if version:
            params["markedVersion"] = version
        else:
            params["markedOpps"] = "true"
        return self.make_api_request(endpoint, method="GET", data=params)


if __name__ == "__main__":
    try:
        # Example usage
        client = GovWinClient()
        
        print("\n===== GovWin API Client Test =====\n")
        
        # Example: Get a single opportunity
        opportunity_id = "OPP183709"  # Valid ID with required OPP prefix
        print(f"\n1. Retrieving single opportunity {opportunity_id}...")
        opportunity = client.get_opportunity(opportunity_id)
        
        # Print key information about the opportunity
        print(f"\nOpportunity Details:")
        print(f"  ID: {opportunity.get('iqOppId')}")
        print(f"  Global ID: {opportunity.get('id')}")
        print(f"  Title: {opportunity.get('title')}")
        print(f"  Status: {opportunity.get('status')}")
        
        # Get agency information
        gov_entity = opportunity.get('govEntity', {})
        if isinstance(gov_entity, dict):
            agency_title = gov_entity.get('title')
        else:
            agency_title = None
        print(f"  Agency: {agency_title}")
        
        # Get value and NAICS information
        print(f"  Value: ${opportunity.get('oppValue', 0):,}")
        
        naics = opportunity.get('primaryNAICS', {})
        if isinstance(naics, dict):
            naics_id = naics.get('id')
            naics_title = naics.get('title')
        else:
            naics_id = None
            naics_title = None
        print(f"  NAICS: {naics_id} - {naics_title}")
        
        # Print smart tags
        print(f"\nSmart Tags:")
        smart_tags = opportunity.get('smartTagObject', [])
        if smart_tags:
            for tag in smart_tags:
                if tag.get('isPrimary'):
                    print(f"  Primary: {tag.get('name')} ({tag.get('type')})")
                else:
                    print(f"  Secondary: {tag.get('name')} ({tag.get('type')})")
        else:
            print("  No smart tags found")
        
        # Example: Get multiple opportunities (batch endpoint)
        opportunity_ids = ["OPP183709", "OPP215651", "OPP243343"]  # Valid IDs with required OPP prefix
        print(f"\n2. Retrieving multiple opportunities {', '.join(opportunity_ids)}...")
        opportunities = client.get_opportunities(opportunity_ids)
        
        # Print a summary of all retrieved opportunities
        print(f"\nOpportunities Summary:")
        for i, opp in enumerate(opportunities, 1):
            opp_id = opp.get('iqOppId') or opp.get('id', 'Unknown ID')
            opp_title = opp.get('title', 'Unknown Title')
            opp_status = opp.get('status', 'Unknown Status')
            opp_value = opp.get('oppValue', 0)
            print(f"  {i}. {opp_id} - {opp_title} ({opp_status}) - ${opp_value:,}")
        
    except Exception as e:
        print(f"Error: {e}")
