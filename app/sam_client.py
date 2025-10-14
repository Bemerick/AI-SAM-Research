"""
SAM.gov API client module.

This module provides functions to interact with the SAM.gov Get Opportunities Public API.
"""
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode

from app.config import SAM_API_BASE_URL, SAM_API_KEY, DEFAULT_LIMIT, DEFAULT_OFFSET


class SAMApiError(Exception):
    """Exception raised for SAM.gov API errors."""
    pass


class SAMClient:
    """Client for interacting with the SAM.gov API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the SAM.gov API client.
        
        Args:
            api_key: The API key for SAM.gov. Defaults to the one in config.
            base_url: The base URL for the SAM.gov API. Defaults to the one in config.
        """
        self.api_key = api_key or SAM_API_KEY
        self.base_url = base_url or SAM_API_BASE_URL
        
        if not self.api_key:
            raise ValueError("SAM.gov API key is required. Set it in .env file or pass it to the constructor.")
    
    def _build_url(self, endpoint: str, params: Dict[str, Any]) -> str:
        """
        Build the URL for the API request.
        
        Args:
            endpoint: The API endpoint.
            params: The query parameters.
            
        Returns:
            The complete URL for the API request.
        """
        # Add API key to parameters
        params['api_key'] = self.api_key
        
        # Build the URL
        url = f"{self.base_url}{endpoint}?{urlencode(params, doseq=True)}"
        return url
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the SAM.gov API.
        
        Args:
            endpoint: The API endpoint.
            params: The query parameters.
            
        Returns:
            The JSON response from the API.
            
        Raises:
            SAMApiError: If the API returns an error.
        """
        url = self._build_url(endpoint, params)
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_message = f"HTTP Error: {status_code}"
            
            try:
                error_data = e.response.json()
                error_detail = error_data.get('error', '')
                if error_detail:
                    error_message = f"{error_message} - {error_detail}"
                else:
                    # Try to get any available error information
                    error_message = f"{error_message} - {str(error_data)}"
            except ValueError:
                # If we can't parse JSON, try to get the text content
                error_message = f"{error_message} - {e.response.text}"
            
            # Print the URL that caused the error (for debugging)
            print(f"Error URL: {url}")
            
            raise SAMApiError(error_message) from e
        except requests.exceptions.RequestException as e:
            raise SAMApiError(f"Request Error: {str(e)}") from e
        except ValueError as e:
            raise SAMApiError(f"Invalid JSON response: {str(e)}") from e
    
    def search_opportunities(self, 
                           p_type: Optional[List[str]] = None,
                           notice_id: Optional[str] = None,
                           sol_num: Optional[str] = None,
                           title: Optional[str] = None,
                           state: Optional[str] = None,
                           zip_code: Optional[str] = None,
                           set_aside_type: Optional[str] = None,
                           naics_code: Optional[Union[str, List[str]]] = None,
                           classification_code: Optional[str] = None,
                           posted_from: Optional[Union[str, datetime]] = None,
                           posted_to: Optional[Union[str, datetime]] = None,
                           response_deadline_from: Optional[Union[str, datetime]] = None,
                           response_deadline_to: Optional[Union[str, datetime]] = None,
                           limit: int = DEFAULT_LIMIT,
                           offset: int = DEFAULT_OFFSET,
                           include_description: bool = False) -> Dict[str, Any]:
        """
        Search for opportunities in SAM.gov.
        
        Args:
            p_type: List of procurement types.
            notice_id: Notice ID.
            sol_num: Solicitation number.
            title: Title of the opportunity.
            state: Place of performance state.
            zip_code: Place of performance ZIP code.
            set_aside_type: Type of set-aside code.
            naics_code: NAICS code.
            classification_code: Classification code.
            posted_from: Posted from date (mm/dd/yyyy).
            posted_to: Posted to date (mm/dd/yyyy).
            response_deadline_from: Response deadline from date (mm/dd/yyyy).
            response_deadline_to: Response deadline to date (mm/dd/yyyy).
            limit: Number of records to fetch.
            offset: Offset value for pagination.
            
        Returns:
            The JSON response from the API.
        """
        # Build parameters
        params = {
            'limit': limit,
            'offset': offset
        }
        
        # Add optional parameters if provided
        if p_type:
            params['ptype'] = p_type
        if notice_id:
            params['noticeid'] = notice_id
        if sol_num:
            params['solnum'] = sol_num
        if title:
            params['title'] = title
        if state:
            params['state'] = state
        if zip_code:
            params['zip'] = zip_code
        if set_aside_type:
            params['typeOfSetAside'] = set_aside_type
        if naics_code:
            # The SAM.gov API expects a single NAICS code as a string
            params['ncode'] = naics_code
        if classification_code:
            params['ccode'] = classification_code
            
        # Format date parameters
        # SAM.gov API now requires postedFrom and postedTo parameters
        if posted_from:
            if isinstance(posted_from, datetime):
                posted_from = posted_from.strftime('%m/%d/%Y')
            params['postedFrom'] = posted_from
        else:
            # Default to 30 days ago
            from datetime import timedelta
            default_from = (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y')
            params['postedFrom'] = default_from
            
        if posted_to:
            if isinstance(posted_to, datetime):
                posted_to = posted_to.strftime('%m/%d/%Y')
            params['postedTo'] = posted_to
        else:
            # Default to today
            default_to = datetime.now().strftime('%m/%d/%Y')
            params['postedTo'] = default_to
            
        if response_deadline_from:
            if isinstance(response_deadline_from, datetime):
                response_deadline_from = response_deadline_from.strftime('%m/%d/%Y')
            params['rdlfrom'] = response_deadline_from
            
        if response_deadline_to:
            if isinstance(response_deadline_to, datetime):
                response_deadline_to = response_deadline_to.strftime('%m/%d/%Y')
            params['rdlto'] = response_deadline_to
        
        # Make the request
        result = self._make_request('', params)
        
        # If include_description is True, fetch the description for each opportunity
        if include_description and result.get('opportunitiesData'):
            opportunities = result.get('opportunitiesData', [])
            for opportunity in opportunities:
                try:
                    # Replace the description URL with the actual description text
                    notice_id = opportunity.get('noticeId')
                    if notice_id:
                        description_text = self.get_opportunity_description(notice_id)
                        opportunity['descriptionText'] = description_text
                except Exception as e:
                    # If there's an error fetching the description, log it but continue
                    print(f"Error fetching description for {notice_id}: {str(e)}")
                    opportunity['descriptionText'] = "Error fetching description"
        
        return result
    
    def get_opportunity_description(self, notice_id: str) -> str:
        """
        Get the description for a specific opportunity by its notice ID.
        
        Args:
            notice_id: The notice ID of the opportunity.
            
        Returns:
            The description text for the opportunity.
        """
        # The description URL is in the format:
        # https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid={notice_id}
        description_url = f"https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid={notice_id}"
        
        params = {
            'api_key': self.api_key
        }
        
        try:
            response = requests.get(f"{description_url}&api_key={self.api_key}")
            response.raise_for_status()
            data = response.json()
            
            # The description is in the 'description' field of the response
            return data.get('description', '')
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_message = f"HTTP Error: {status_code}"
            
            try:
                error_data = e.response.json()
                error_detail = error_data.get('error', '')
                if error_detail:
                    error_message = f"{error_message} - {error_detail}"
                else:
                    # Try to get any available error information
                    error_message = f"{error_message} - {str(error_data)}"
            except ValueError:
                # If we can't parse JSON, try to get the text content
                error_message = f"{error_message} - {e.response.text}"
            
            raise SAMApiError(error_message) from e
        except Exception as e:
            raise SAMApiError(f"Error fetching description: {str(e)}") from e
    
    def get_opportunity_by_id(self, notice_id: str, include_description: bool = False) -> Dict[str, Any]:
        """
        Get a specific opportunity by its notice ID.
        
        Args:
            notice_id: The notice ID of the opportunity.
            include_description: Whether to include the full description text.
            
        Returns:
            The JSON response from the API.
        """
        result = self.search_opportunities(notice_id=notice_id, limit=1)
        
        if include_description and result.get('opportunitiesData'):
            opportunities = result.get('opportunitiesData', [])
            for opportunity in opportunities:
                try:
                    # Replace the description URL with the actual description text
                    notice_id = opportunity.get('noticeId')
                    if notice_id:
                        description_text = self.get_opportunity_description(notice_id)
                        opportunity['descriptionText'] = description_text
                except Exception as e:
                    # If there's an error fetching the description, log it but continue
                    print(f"Error fetching description for {notice_id}: {str(e)}")
                    opportunity['descriptionText'] = "Error fetching description"
        
        return result
