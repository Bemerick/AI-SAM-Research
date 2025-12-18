"""
Microsoft Dynamics 365 CRM Client.
Provides methods for interacting with Dynamics CRM Dataverse Web API.
"""
import os
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DynamicsClient:
    """Client for Microsoft Dynamics 365 CRM Dataverse Web API."""

    def __init__(self, resource_url: str, access_token: Optional[str] = None, opportunity_table: Optional[str] = None):
        """
        Initialize the Dynamics CRM client.

        Args:
            resource_url: Base URL for Dynamics CRM (e.g., https://yourorg.crm.dynamics.com)
            access_token: OAuth access token for authentication
            opportunity_table: Custom opportunity table name (defaults to 'opportunities')
        """
        self.resource_url = resource_url.rstrip('/')
        self.access_token = access_token
        self.api_version = "v9.2"
        self.base_api_url = f"{self.resource_url}/api/data/{self.api_version}"
        # Support custom opportunity tables
        self.opportunity_table = opportunity_table or os.getenv('DYNAMICS_OPPORTUNITY_TABLE', 'opportunities')

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'OData-MaxVersion': '4.0',
            'OData-Version': '4.0',
            'Prefer': 'return=representation'
        }

        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        return headers

    def create_opportunity(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new opportunity in Dynamics CRM.

        Args:
            opportunity_data: Dictionary containing opportunity fields

        Returns:
            Dictionary with created opportunity details including ID

        Raises:
            Exception: If API call fails
        """
        if not self.access_token:
            raise Exception("No access token provided - cannot create opportunity")

        endpoint = f"{self.base_api_url}/{self.opportunity_table}"

        try:
            logger.info(f"Creating opportunity in Dynamics CRM: {opportunity_data.get('name', 'Unknown')}")

            response = requests.post(
                endpoint,
                json=opportunity_data,
                headers=self._get_headers(),
                timeout=30
            )

            response.raise_for_status()

            # Extract the opportunity ID from response headers
            opportunity_id = None
            if 'OData-EntityId' in response.headers:
                # Format: https://yourorg.crm.dynamics.com/api/data/v9.2/opportunities(guid)
                entity_id_url = response.headers['OData-EntityId']
                opportunity_id = entity_id_url.split('(')[-1].rstrip(')')

            result_data = response.json() if response.content else {}

            logger.info(f"Successfully created opportunity with ID: {opportunity_id}")

            return {
                'crm_id': opportunity_id or result_data.get('opportunityid'),
                'status': 'success',
                'message': 'Opportunity successfully created in CRM',
                'data': result_data
            }

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error creating opportunity: {e}"
            if e.response is not None:
                try:
                    error_details = e.response.json()
                    error_msg = f"CRM API error: {error_details.get('error', {}).get('message', str(e))}"
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"

            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error creating opportunity in CRM: {str(e)}")
            raise

    def update_opportunity(self, opportunity_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing opportunity in Dynamics CRM.

        Args:
            opportunity_id: The GUID of the opportunity to update
            update_data: Dictionary containing fields to update

        Returns:
            Dictionary with update status

        Raises:
            Exception: If API call fails
        """
        if not self.access_token:
            raise Exception("No access token provided - cannot update opportunity")

        endpoint = f"{self.base_api_url}/{self.opportunity_table}({opportunity_id})"

        try:
            logger.info(f"Updating opportunity {opportunity_id} in Dynamics CRM")

            response = requests.patch(
                endpoint,
                json=update_data,
                headers=self._get_headers(),
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"Successfully updated opportunity {opportunity_id}")

            return {
                'crm_id': opportunity_id,
                'status': 'success',
                'message': 'Opportunity successfully updated in CRM'
            }

        except Exception as e:
            logger.error(f"Error updating opportunity in CRM: {str(e)}")
            raise

    def get_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Retrieve an opportunity from Dynamics CRM.

        Args:
            opportunity_id: The GUID of the opportunity

        Returns:
            Dictionary containing opportunity data

        Raises:
            Exception: If API call fails
        """
        if not self.access_token:
            raise Exception("No access token provided - cannot retrieve opportunity")

        endpoint = f"{self.base_api_url}/{self.opportunity_table}({opportunity_id})"

        try:
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error retrieving opportunity from CRM: {str(e)}")
            raise

    def search_opportunities(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for opportunities in Dynamics CRM.

        Args:
            filters: Optional OData filter criteria

        Returns:
            List of opportunity dictionaries

        Raises:
            Exception: If API call fails
        """
        if not self.access_token:
            raise Exception("No access token provided - cannot search opportunities")

        endpoint = f"{self.base_api_url}/{self.opportunity_table}"

        # Build OData query parameters
        params = {}
        if filters:
            if 'filter' in filters:
                params['$filter'] = filters['filter']
            if 'select' in filters:
                params['$select'] = filters['select']
            if 'top' in filters:
                params['$top'] = filters['top']

        try:
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()
            return data.get('value', [])

        except Exception as e:
            logger.error(f"Error searching opportunities in CRM: {str(e)}")
            raise


def map_sam_opportunity_to_crm(sam_opportunity: Dict[str, Any], customer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Map a SAM.gov opportunity to Dynamics CRM opportunity fields.

    Args:
        sam_opportunity: SAM opportunity dictionary
        customer_id: Optional GUID of the Account or Contact to associate with the opportunity

    Returns:
        Dictionary with CRM-formatted opportunity fields
    """
    # Map SAM fields to Dynamics CRM opportunity fields
    # Using only standard Dynamics 365 Sales fields

    # Required field: name (Topic)
    crm_data = {
        'name': sam_opportunity.get('title', 'Untitled Opportunity')[:300],  # CRM has field length limits
    }

    # Customer (Account or Contact) - Highly recommended, some CRM configs require it
    # If customer_id is provided, link the opportunity to that account/contact
    if customer_id:
        # For an Account: use customerid_account@odata.bind
        # For a Contact: use customerid_contact@odata.bind
        # The format depends on whether customer_id is an account or contact GUID
        crm_data['customerid_account@odata.bind'] = f"/accounts({customer_id})"

    # Optional standard fields
    # Description - Include all key information since custom fields don't exist yet
    crm_data['description'] = _build_description(sam_opportunity)

    # Estimated close date - Use response deadline
    if sam_opportunity.get('response_deadline'):
        crm_data['estimatedclosedate'] = _format_date(sam_opportunity['response_deadline'])

    # Close probability - Map fit score (0-10) to percentage
    if sam_opportunity.get('fit_score'):
        fit_score = sam_opportunity['fit_score']
        crm_data['closeprobability'] = int(min(fit_score * 10, 100))

    # Current situation - Add solicitation/NAICS info
    current_situation_parts = []
    if sam_opportunity.get('solicitation_number'):
        current_situation_parts.append(f"Solicitation: {sam_opportunity['solicitation_number']}")
    if sam_opportunity.get('naics_code'):
        current_situation_parts.append(f"NAICS: {sam_opportunity['naics_code']}")
    if sam_opportunity.get('department'):
        current_situation_parts.append(f"Agency: {sam_opportunity['department']}")
    if sam_opportunity.get('set_aside'):
        current_situation_parts.append(f"Set-Aside: {sam_opportunity['set_aside']}")

    if current_situation_parts:
        crm_data['currentsituation'] = '\n'.join(current_situation_parts)[:1500]

    # Customer need - Add practice area if available
    if sam_opportunity.get('assigned_practice_area'):
        crm_data['customerneed'] = f"Practice Area: {sam_opportunity['assigned_practice_area']}"

    # Budget amount - Not typically available in SAM, leave unset
    # Estimated value - Not typically available in SAM, leave unset

    # NOTE: To add custom fields, you need to:
    # 1. Create custom fields in Dynamics 365 (Settings > Customizations > Customize the System)
    # 2. Uncomment and adjust the lines below with your actual field names
    # 3. Custom fields typically have a publisher prefix (e.g., cr7f3_samnoticeid, new_samlink, etc.)

    # Example custom fields (commented out until created in CRM):
    # if sam_opportunity.get('notice_id'):
    #     crm_data['cr7f3_samnoticeid'] = sam_opportunity['notice_id']
    # if sam_opportunity.get('sam_link'):
    #     crm_data['cr7f3_samlink'] = sam_opportunity['sam_link']
    # if sam_opportunity.get('ptype'):
    #     crm_data['cr7f3_procurementtype'] = sam_opportunity['ptype']

    return crm_data


def _build_description(sam_opportunity: Dict[str, Any]) -> str:
    """Build a comprehensive description for the CRM opportunity."""
    parts = []

    if sam_opportunity.get('summary_description'):
        parts.append(f"Summary: {sam_opportunity['summary_description']}")

    if sam_opportunity.get('justification'):
        parts.append(f"\nFit Analysis: {sam_opportunity['justification']}")

    if sam_opportunity.get('notice_id'):
        parts.append(f"\nNotice ID: {sam_opportunity['notice_id']}")

    if sam_opportunity.get('solicitation_number'):
        parts.append(f"Solicitation: {sam_opportunity['solicitation_number']}")

    if sam_opportunity.get('posted_date'):
        parts.append(f"Posted: {sam_opportunity['posted_date']}")

    description = '\n'.join(parts)

    # CRM description field typically has a limit (e.g., 2000 characters)
    if len(description) > 2000:
        description = description[:1997] + '...'

    return description


def _format_date(date_str: str) -> str:
    """
    Format a date string for Dynamics CRM.

    Dynamics CRM expects date fields in YYYY-MM-DD format (Edm.Date type).

    Args:
        date_str: Date string in various formats

    Returns:
        Date string formatted as YYYY-MM-DD, or None if parsing fails
    """
    if not date_str:
        return None

    try:
        # If the string contains timezone info, use dateutil parser
        if '+' in date_str or date_str.endswith('Z') or 'T' in date_str:
            from dateutil import parser
            dt = parser.parse(date_str)
            return dt.strftime('%Y-%m-%d')

        # Try parsing common formats without timezone
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # Last resort: extract just the date portion if it's in ISO format
        if len(date_str) >= 10:
            date_part = date_str[:10]
            # Validate it's a proper date
            datetime.strptime(date_part, '%Y-%m-%d')
            return date_part

        return None

    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return None
