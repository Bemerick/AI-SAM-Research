"""
API endpoints for the SAM.gov API client.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import OpportunitySearchParams, OpportunityResponse, Opportunity
from app.sam_client import SAMClient, SAMApiError

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def get_sam_client() -> SAMClient:
    """
    Dependency to get the SAM.gov API client.
    
    Returns:
        An instance of the SAMClient.
    """
    try:
        return SAMClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=OpportunityResponse)
async def search_opportunities(
    p_type: Optional[List[str]] = Query(None, description="List of procurement types"),
    notice_id: Optional[str] = Query(None, description="Notice ID"),
    sol_num: Optional[str] = Query(None, description="Solicitation number"),
    title: Optional[str] = Query(None, description="Title of the opportunity"),
    state: Optional[str] = Query(None, description="Place of performance state"),
    zip_code: Optional[str] = Query(None, description="Place of performance ZIP code"),
    set_aside_type: Optional[str] = Query(None, description="Type of set-aside code"),
    naics_code: Optional[List[str]] = Query(None, description="NAICS codes - can provide multiple"),
    classification_code: Optional[str] = Query(None, description="Classification code"),
    posted_from: Optional[str] = Query(None, description="Posted from date (mm/dd/yyyy)"),
    posted_to: Optional[str] = Query(None, description="Posted to date (mm/dd/yyyy)"),
    response_deadline_from: Optional[str] = Query(None, description="Response deadline from date (mm/dd/yyyy)"),
    response_deadline_to: Optional[str] = Query(None, description="Response deadline to date (mm/dd/yyyy)"),
    limit: int = Query(10, description="Number of records to fetch"),
    offset: int = Query(0, description="Offset value for pagination"),
    include_description: bool = Query(False, description="Whether to include the full description text"),
    sam_client: SAMClient = Depends(get_sam_client)
) -> Dict[str, Any]:
    """
    Search for opportunities in SAM.gov.
    
    Returns:
        The opportunities matching the search criteria.
    """
    try:
        result = sam_client.search_opportunities(
            p_type=p_type,
            notice_id=notice_id,
            sol_num=sol_num,
            title=title,
            state=state,
            zip_code=zip_code,
            set_aside_type=set_aside_type,
            naics_code=naics_code,
            classification_code=classification_code,
            posted_from=posted_from,
            posted_to=posted_to,
            response_deadline_from=response_deadline_from,
            response_deadline_to=response_deadline_to,
            limit=limit,
            offset=offset,
            include_description=include_description
        )
        
        # Convert snake_case to camelCase for response
        return {
            "total_records": result.get("totalRecords", 0),
            "limit": result.get("limit", limit),
            "offset": result.get("offset", offset),
            "opportunities_data": result.get("opportunitiesData", []),
            "links": result.get("links", [])
        }
    except SAMApiError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{notice_id}", response_model=Opportunity)
async def get_opportunity(
    notice_id: str,
    include_description: bool = Query(False, description="Whether to include the full description text"),
    sam_client: SAMClient = Depends(get_sam_client)
) -> Dict[str, Any]:
    """
    Get a specific opportunity by its notice ID.
    
    Args:
        notice_id: The notice ID of the opportunity.
        
    Returns:
        The opportunity details.
    """
    try:
        result = sam_client.get_opportunity_by_id(notice_id, include_description=include_description)
        
        # Check if any opportunities were found
        opportunities_data = result.get("opportunitiesData", [])
        if not opportunities_data:
            raise HTTPException(status_code=404, detail=f"Opportunity with notice ID {notice_id} not found")
        
        # Return the first (and should be only) opportunity
        return opportunities_data[0]
    except SAMApiError as e:
        raise HTTPException(status_code=400, detail=str(e))
