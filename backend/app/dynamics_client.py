"""
Microsoft Dynamics 365 CRM Client.
Provides methods for interacting with Dynamics CRM Dataverse Web API.
"""
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DynamicsClient:
    """Client for Microsoft Dynamics 365 CRM Dataverse Web API."""

    def __init__(self, resource_url: str, access_token: Optional[str] = None):
        """
        Initialize the Dynamics CRM client.

        Args:
            resource_url: Base URL for Dynamics CRM (e.g., https://yourorg.crm.dynamics.com)
            access_token: OAuth access token for authentication
        """
        self.resource_url = resource_url.rstrip('/')
        self.access_token = access_token
        self.api_version = "v9.2"
        self.base_api_url = f"{self.resource_url}/api/data/{self.api_version}"

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

        endpoint = f"{self.base_api_url}/opportunities"

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

        endpoint = f"{self.base_api_url}/opportunities({opportunity_id})"

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

        endpoint = f"{self.base_api_url}/opportunities({opportunity_id})"

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

        endpoint = f"{self.base_api_url}/opportunities"

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


def map_sam_opportunity_to_crm(sam_opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a SAM.gov opportunity to Dynamics CRM opportunity fields.

    Args:
        sam_opportunity: SAM opportunity dictionary

    Returns:
        Dictionary with CRM-formatted opportunity fields
    """
    # Map SAM fields to Dynamics CRM opportunity fields
    # Note: You'll need to customize these field mappings based on your CRM schema

    crm_data = {
        'name': sam_opportunity.get('title', 'Untitled Opportunity')[:300],  # CRM has field length limits
        'description': _build_description(sam_opportunity),
    }

    # Add optional fields if they exist
    if sam_opportunity.get('response_deadline'):
        crm_data['estimatedclosedate'] = _format_date(sam_opportunity['response_deadline'])

    if sam_opportunity.get('fit_score'):
        # Map fit score to a custom field or probability
        # Assuming fit_score is 0-10, convert to percentage
        fit_score = sam_opportunity['fit_score']
        crm_data['closeprobability'] = int(min(fit_score * 10, 100))

    # Custom fields - adjust these based on your CRM customizations
    # These would typically be prefixed with your publisher prefix
    # Example: new_samnoticeid, new_samlink, etc.

    if sam_opportunity.get('notice_id'):
        crm_data['new_samnoticeid'] = sam_opportunity['notice_id']

    if sam_opportunity.get('solicitation_number'):
        crm_data['new_solicitationnumber'] = sam_opportunity['solicitation_number']

    if sam_opportunity.get('naics_code'):
        crm_data['new_naicscode'] = sam_opportunity['naics_code']

    if sam_opportunity.get('department'):
        crm_data['new_department'] = sam_opportunity['department'][:100]

    if sam_opportunity.get('sam_link'):
        crm_data['new_samlink'] = sam_opportunity['sam_link']

    if sam_opportunity.get('assigned_practice_area'):
        crm_data['new_practicearea'] = sam_opportunity['assigned_practice_area']

    if sam_opportunity.get('set_aside'):
        crm_data['new_setaside'] = sam_opportunity['set_aside']

    if sam_opportunity.get('ptype'):
        crm_data['new_procurementtype'] = sam_opportunity['ptype']

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

    Args:
        date_str: Date string in various formats

    Returns:
        ISO 8601 formatted date string
    """
    if not date_str:
        return None

    try:
        # Try parsing common formats
        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If none match, return as-is
        return date_str

    except Exception:
        return date_str
