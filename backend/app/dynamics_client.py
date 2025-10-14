"""
Microsoft Dynamics CRM integration client.

This module handles communication with Microsoft Dynamics CRM via the Dataverse Web API.
"""
import logging
from typing import Dict, Any, Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class DynamicsClient:
    """Client for interacting with Microsoft Dynamics CRM."""

    def __init__(
        self,
        resource_url: str,
        access_token: Optional[str] = None
    ):
        """
        Initialize the Dynamics CRM client.

        Args:
            resource_url: The Dynamics CRM instance URL (e.g., https://yourorg.crm.dynamics.com)
            access_token: OAuth access token for authentication
        """
        self.resource_url = resource_url.rstrip('/')
        self.api_url = f"{self.resource_url}/api/data/v9.2"
        self.access_token = access_token

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'OData-MaxVersion': '4.0',
            'OData-Version': '4.0',
        }

        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        return headers

    def create_opportunity(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an opportunity in Dynamics CRM.

        Args:
            opportunity_data: Dictionary containing opportunity fields mapped to CRM schema

        Returns:
            Dictionary containing the created opportunity data including the CRM ID

        Raises:
            Exception: If the API request fails
        """
        # Use custom table - Web API collection name (logical name is new_opportunity, plural is Opportunities)
        url = f"{self.api_url}/new_opportunities"

        try:
            response = requests.post(
                url,
                json=opportunity_data,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            # Get the ID from the OData-EntityId header
            entity_id = response.headers.get('OData-EntityId', '')
            opportunity_id = entity_id.split('(')[-1].rstrip(')')

            logger.info(f"Successfully created opportunity in CRM with ID: {opportunity_id}")

            return {
                'crm_id': opportunity_id,
                'status': 'success',
                'message': 'Opportunity created successfully in CRM'
            }

        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to create opportunity in CRM. Status: {e.response.status_code if e.response else 'N/A'}")
            logger.error(f"Error detail: {error_detail}")
            logger.error(f"Request data: {opportunity_data}")
            raise Exception(f"CRM API Error ({e.response.status_code if e.response else 'N/A'}): {error_detail}")
        except Exception as e:
            logger.error(f"Error creating opportunity in CRM: {str(e)}")
            raise

    def update_opportunity(self, crm_id: str, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing opportunity in Dynamics CRM.

        Args:
            crm_id: The GUID of the opportunity in CRM
            opportunity_data: Dictionary containing fields to update

        Returns:
            Dictionary containing the update status
        """
        url = f"{self.api_url}/opportunities({crm_id})"

        try:
            response = requests.patch(
                url,
                json=opportunity_data,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            logger.info(f"Successfully updated opportunity in CRM: {crm_id}")

            return {
                'crm_id': crm_id,
                'status': 'success',
                'message': 'Opportunity updated successfully in CRM'
            }

        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to update opportunity in CRM: {error_detail}")
            raise Exception(f"CRM API Error: {error_detail}")
        except Exception as e:
            logger.error(f"Error updating opportunity in CRM: {str(e)}")
            raise

    def get_opportunity(self, crm_id: str) -> Dict[str, Any]:
        """
        Retrieve an opportunity from Dynamics CRM.

        Args:
            crm_id: The GUID of the opportunity in CRM

        Returns:
            Dictionary containing the opportunity data
        """
        url = f"{self.api_url}/opportunities({crm_id})"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to get opportunity from CRM: {error_detail}")
            raise Exception(f"CRM API Error: {error_detail}")
        except Exception as e:
            logger.error(f"Error getting opportunity from CRM: {str(e)}")
            raise


def map_sam_opportunity_to_crm(sam_opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map SAM.gov opportunity fields to Dynamics CRM opportunity fields.

    This function should be customized based on your specific CRM schema.

    Args:
        sam_opportunity: SAM opportunity data from our database

    Returns:
        Dictionary with fields mapped to CRM schema
    """
    crm_data = {}

    # Required field for custom table - Primary column (all lowercase)
    if sam_opportunity.get('title'):
        crm_data['new_name'] = sam_opportunity['title']

    # Map to custom CRM fields - all lowercase field names
    # Only include fields that exist and work properly in CRM
    if sam_opportunity.get('summary_description'):
        crm_data['new_description'] = sam_opportunity['summary_description']

    if sam_opportunity.get('sam_link'):
        crm_data['new_marketresearchurl'] = sam_opportunity['sam_link']

    # Set sales stage to default value (picklist field)
    crm_data['new_salesstage'] = 100000000

    # Note: The following fields have issues and are commented out:
    # - new_rfprfqduedate: Date format issues (doesn't accept "N/A" or simple date strings)
    # - new_rfprfqreleasedate: Date format issues
    # - new_naicscode: Is a choice field (picklist) that only accepts specific values (100000000-100000012), not actual NAICS codes
    # - new_accountname: Field doesn't exist in CRM schema

    return crm_data
