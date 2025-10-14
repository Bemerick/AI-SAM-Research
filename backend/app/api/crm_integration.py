"""
API endpoints for Microsoft Dynamics CRM integration.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from ..database import get_db
from ..models import SAMOpportunity
from ..dynamics_client import DynamicsClient, map_sam_opportunity_to_crm

router = APIRouter(prefix="/crm", tags=["CRM Integration"])
logger = logging.getLogger(__name__)


def get_dynamics_client() -> DynamicsClient:
    """
    Get an authenticated Dynamics CRM client.

    Returns:
        DynamicsClient with valid access token

    Raises:
        ValueError: If authentication is not configured
        Exception: If token acquisition fails
    """
    from ..dynamics_auth import get_access_token, DynamicsAuthConfig

    config = DynamicsAuthConfig()

    # Check if authentication is configured
    if not config.is_configured():
        missing = config.get_missing_config()
        logger.warning(
            f"Dynamics CRM authentication not configured. Missing: {', '.join(missing)}. "
            "Operating in mock mode."
        )
        # Return client without token for testing
        return DynamicsClient(
            resource_url=config.resource_url or "https://yourorg.crm.dynamics.com",
            access_token=None
        )

    # Get access token
    try:
        access_token = get_access_token()
        return DynamicsClient(resource_url=config.resource_url, access_token=access_token)
    except Exception as e:
        logger.error(f"Failed to get Dynamics CRM client: {str(e)}")
        raise


@router.post("/opportunities/{opportunity_id}/send")
async def send_opportunity_to_crm(
    opportunity_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Send a SAM opportunity to Microsoft Dynamics CRM.

    Args:
        opportunity_id: The ID of the SAM opportunity to send
        db: Database session

    Returns:
        Dictionary with success status and CRM ID

    Raises:
        HTTPException: If opportunity not found or CRM operation fails
    """
    # Get the opportunity from the database
    opportunity = db.query(SAMOpportunity).filter(SAMOpportunity.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Convert to dictionary
    opportunity_dict = {
        'id': opportunity.id,
        'notice_id': opportunity.notice_id,
        'title': opportunity.title,
        'department': opportunity.department,
        'solicitation_number': opportunity.solicitation_number,
        'naics_code': opportunity.naics_code,
        'response_deadline': opportunity.response_deadline,
        'posted_date': opportunity.posted_date,
        'fit_score': opportunity.fit_score,
        'assigned_practice_area': opportunity.assigned_practice_area,
        'justification': opportunity.justification,
        'summary_description': opportunity.summary_description,
        'sam_link': opportunity.sam_link,
        'set_aside': opportunity.set_aside,
        'ptype': opportunity.ptype,
    }

    try:
        # Map SAM opportunity to CRM fields
        crm_data = map_sam_opportunity_to_crm(opportunity_dict)

        # Get Dynamics client and create opportunity
        dynamics_client = get_dynamics_client()

        # Check if we're in mock mode (no authentication)
        if not dynamics_client.access_token:
            logger.info(f"Operating in mock mode - authentication not configured")
            result = {
                'crm_id': 'mock-crm-id-12345',
                'status': 'success',
                'message': 'Mock Mode: Opportunity would be sent to CRM (authentication not configured)',
                'mapped_data': crm_data  # Include mapped data for testing
            }
        else:
            # Actually send to CRM
            result = dynamics_client.create_opportunity(crm_data)
            logger.info(f"Opportunity {opportunity_id} successfully sent to CRM: {result.get('crm_id')}")

        return {
            'success': True,
            'opportunity_id': opportunity_id,
            'notice_id': opportunity.notice_id,
            'crm_result': result
        }

    except Exception as e:
        logger.error(f"Failed to send opportunity {opportunity_id} to CRM: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send opportunity to CRM: {str(e)}"
        )


@router.get("/opportunities/{opportunity_id}/status")
async def get_crm_sync_status(
    opportunity_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if an opportunity has been synced to CRM.

    This is a placeholder endpoint. You may want to add a field to the SAMOpportunity
    model to track CRM sync status and CRM ID.

    Args:
        opportunity_id: The ID of the SAM opportunity
        db: Database session

    Returns:
        Dictionary with sync status
    """
    opportunity = db.query(SAMOpportunity).filter(SAMOpportunity.id == opportunity_id).first()

    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # TODO: Add fields to SAMOpportunity model to track CRM sync
    # For now, return a placeholder response
    return {
        'opportunity_id': opportunity_id,
        'synced_to_crm': False,
        'crm_id': None,
        'last_synced_at': None
    }
