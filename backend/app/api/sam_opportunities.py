"""
API endpoints for SAM.gov opportunities.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/sam-opportunities", tags=["SAM Opportunities"])


class FetchByDateRequest(BaseModel):
    """Request model for fetching SAM opportunities by date."""
    posted_date: str  # Format: YYYY-MM-DD
    naics_codes: Optional[List[str]] = None  # Optional: specific NAICS codes, otherwise use defaults


class FetchByDateResponse(BaseModel):
    """Response model for fetch by date endpoint."""
    message: str
    fetched_count: int
    stored_count: int
    duplicate_count: int
    error_count: int


class ShareOpportunityRequest(BaseModel):
    """Request model for sharing an opportunity via email."""
    to_emails: List[EmailStr]
    sender_name: Optional[str] = None
    message: Optional[str] = None


class ShareOpportunityResponse(BaseModel):
    """Response model for share opportunity endpoint."""
    success: bool
    message: str


@router.get("/", response_model=List[schemas.SAMOpportunity])
def list_sam_opportunities(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    min_fit_score: Optional[float] = Query(None, ge=0, le=10, description="Minimum fit score"),
    department: Optional[str] = Query(None, description="Filter by department"),
    naics_code: Optional[str] = Query(None, description="Filter by NAICS code"),
    review_for_bid: Optional[str] = Query(None, description="Filter by review_for_bid status"),
    recommend_bid: Optional[str] = Query(None, description="Filter by recommend_bid status"),
    is_followed: Optional[int] = Query(None, ge=0, le=1, description="Filter by followed status (0=not followed, 1=followed)"),
    db: Session = Depends(get_db)
):
    """
    List SAM opportunities with optional filters.
    """
    # Get opportunities with base filters
    opportunities = crud.get_sam_opportunities(
        db=db,
        skip=skip,
        limit=limit,
        min_fit_score=min_fit_score,
        department=department,
        naics_code=naics_code,
        is_followed=is_followed
    )

    # Apply workflow filters in-memory (could optimize with DB query)
    if review_for_bid:
        opportunities = [opp for opp in opportunities if opp.review_for_bid == review_for_bid]
    if recommend_bid:
        opportunities = [opp for opp in opportunities if opp.recommend_bid == recommend_bid]

    # Add match_count to each opportunity
    from ..models import Match
    for opp in opportunities:
        match_count = db.query(Match).filter(Match.sam_opportunity_id == opp.id).count()
        opp.match_count = match_count

    return opportunities


@router.get("/unscored", response_model=List[schemas.SAMOpportunity])
def list_unscored_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List SAM opportunities with fit_score = 0 or NULL (unscored).
    """
    return crud.get_unscored_sam_opportunities(
        db=db,
        skip=skip,
        limit=limit
    )


@router.get("/high-scoring", response_model=List[schemas.SAMOpportunity])
def list_high_scoring_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List SAM opportunities with fit_score >= 6.
    """
    return crud.get_sam_opportunities(
        db=db,
        skip=skip,
        limit=limit,
        min_fit_score=6.0
    )


@router.get("/{opportunity_id}", response_model=schemas.SAMOpportunity)
def get_sam_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific SAM opportunity by ID.
    """
    opportunity = crud.get_sam_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")

    # Add match_count
    from ..models import Match
    opportunity.match_count = db.query(Match).filter(Match.sam_opportunity_id == opportunity.id).count()

    return opportunity


@router.get("/notice/{notice_id}", response_model=schemas.SAMOpportunity)
def get_sam_opportunity_by_notice_id(
    notice_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific SAM opportunity by notice ID.
    """
    opportunity = crud.get_sam_opportunity_by_notice_id(db, notice_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")
    return opportunity


@router.post("/", response_model=schemas.SAMOpportunity, status_code=201)
def create_sam_opportunity(
    opportunity: schemas.SAMOpportunityCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new SAM opportunity.
    Handles amendment tracking for opportunities with the same solicitation number.
    """
    # Check if this exact notice_id already exists (true duplicate)
    existing = crud.get_sam_opportunity_by_notice_id(db, opportunity.notice_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"SAM opportunity with notice_id '{opportunity.notice_id}' already exists"
        )

    # Check if an opportunity with the same solicitation_number exists (amendment/update)
    if opportunity.solicitation_number:
        from ..models import SAMOpportunity
        related_opps = db.query(SAMOpportunity).filter(
            SAMOpportunity.solicitation_number == opportunity.solicitation_number
        ).order_by(SAMOpportunity.created_at).all()

        if related_opps:
            # This is an amendment
            # Find the original (first one with is_amendment == 0)
            original = next((o for o in related_opps if o.is_amendment == 0), related_opps[0])

            # Update opportunity data to mark as amendment
            opportunity.is_amendment = len(related_opps)
            opportunity.original_notice_id = original.notice_id

            # Mark the most recent one as superseded
            most_recent = related_opps[-1]
            most_recent.superseded_by_notice_id = opportunity.notice_id
            db.commit()

    return crud.create_sam_opportunity(db, opportunity)


@router.patch("/{opportunity_id}", response_model=schemas.SAMOpportunity)
def update_sam_opportunity(
    opportunity_id: int,
    opportunity_update: schemas.SAMOpportunityUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a SAM opportunity (typically workflow fields).
    """
    opportunity = crud.update_sam_opportunity(db, opportunity_id, opportunity_update)
    if not opportunity:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")
    return opportunity


@router.post("/{opportunity_id}/toggle-follow", response_model=schemas.SAMOpportunity)
def toggle_follow_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Toggle the follow status of a SAM opportunity.
    """
    opportunity = crud.get_sam_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")

    # Toggle the follow status
    new_status = 0 if opportunity.is_followed else 1
    opportunity_update = schemas.SAMOpportunityUpdate(is_followed=new_status)

    updated_opportunity = crud.update_sam_opportunity(db, opportunity_id, opportunity_update)
    return updated_opportunity


@router.delete("/{opportunity_id}", status_code=204)
def delete_sam_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a SAM opportunity.
    """
    success = crud.delete_sam_opportunity(db, opportunity_id)
    if not success:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")
    return None


@router.get("/{opportunity_id}/matches", response_model=List[schemas.MatchWithDetails])
def get_opportunity_matches(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all GovWin matches for a specific SAM opportunity.
    """
    # Verify opportunity exists
    opportunity = crud.get_sam_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")

    # Get matches using sam_notice_id filter
    matches = crud.get_matches(db, sam_notice_id=opportunity.notice_id)
    return matches


@router.get("/{opportunity_id}/matches/{match_id}/contracts", response_model=List[schemas.GovWinContract])
def get_match_contracts(
    opportunity_id: int,
    match_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all contracts for a specific GovWin match.
    """
    # Verify opportunity exists
    opportunity = crud.get_sam_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")

    # Get the match
    match = crud.get_match(db, match_id)
    if not match or match.sam_opportunity_id != opportunity_id:
        raise HTTPException(status_code=404, detail="Match not found for this opportunity")

    # Get contracts for the GovWin opportunity
    contracts = crud.get_contracts_by_govwin_opportunity(db, match.govwin_opportunity_id)
    return contracts


@router.post("/fetch-by-date", response_model=FetchByDateResponse)
def fetch_sam_opportunities_by_date(
    request: FetchByDateRequest,
    db: Session = Depends(get_db)
):
    """
    Fetch SAM opportunities for a specific date.
    Uses the same duplicate checking logic as the cron job.
    """
    import os
    from datetime import datetime

    # Get SAM API key from environment
    sam_api_key = os.getenv('SAM_API_KEY')
    if not sam_api_key:
        raise HTTPException(status_code=500, detail="SAM_API_KEY not configured")

    # Parse the posted_date
    try:
        target_date = datetime.strptime(request.posted_date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Default NAICS codes if not provided
    default_naics_codes = [
        "519190", "518210", "541430", "541490", "541511", "541512", "541519",
        "541611", "541618", "541690", "541715", "541990", "561110", "611430", "921190"
    ]
    naics_codes = request.naics_codes or default_naics_codes

    # Import SAM client from root app directory
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
    from app.sam_client import SAMClient

    client = SAMClient(api_key=sam_api_key)

    fetched_count = 0
    stored_count = 0
    duplicate_count = 0
    error_count = 0

    # Fetch for each NAICS code
    for naics_code in naics_codes:
        try:
            # Fetch opportunities for this NAICS code and date
            result = client.search_opportunities(
                naics_code=naics_code,
                posted_from=target_date,
                posted_to=target_date + timedelta(days=1),
                limit=100,
                include_description=True
            )

            opportunities = result.get('opportunitiesData', [])
            fetched_count += len(opportunities)

            # Store each opportunity
            for opp in opportunities:
                if not opp.get("noticeId"):
                    error_count += 1
                    continue

                try:
                    notice_id = opp.get("noticeId")
                    solicitation_number = opp.get("solicitationNumber")

                    # Check if this exact notice_id already exists (true duplicate)
                    existing_notice = crud.get_sam_opportunity_by_notice_id(db, notice_id)
                    if existing_notice:
                        duplicate_count += 1
                        continue

                    # Extract nested fields
                    place_of_performance = opp.get("placeOfPerformance") or {}
                    city_data = place_of_performance.get("city") or {}
                    state_data = place_of_performance.get("state") or {}
                    point_of_contact = opp.get("pointOfContact") or []
                    primary_contact = point_of_contact[0] if point_of_contact else {}

                    # Check if an opportunity with the same solicitation_number exists (amendment/update)
                    is_amendment_num = 0
                    original_notice_id = None

                    if solicitation_number:
                        # Find all opportunities with this solicitation number
                        from ..models import SAMOpportunity
                        related_opps = db.query(SAMOpportunity).filter(
                            SAMOpportunity.solicitation_number == solicitation_number
                        ).order_by(SAMOpportunity.created_at).all()

                        if related_opps:
                            # This is an amendment
                            # Find the original (first one with is_amendment == 0)
                            original = next((o for o in related_opps if o.is_amendment == 0), related_opps[0])
                            original_notice_id = original.notice_id

                            # Calculate amendment number (how many amendments exist + 1)
                            is_amendment_num = len(related_opps)

                            # Mark the most recent one as superseded
                            most_recent = related_opps[-1]
                            most_recent.superseded_by_notice_id = notice_id
                            db.commit()

                    # Create opportunity data
                    opportunity_data = schemas.SAMOpportunityCreate(
                        notice_id=notice_id,
                        title=opp.get("title"),
                        department=opp.get("fullParentPathName"),
                        standardized_department=opp.get("fullParentPathName"),
                        naics_code=opp.get("naicsCode"),
                        full_parent_path=opp.get("fullParentPathName"),
                        fit_score=0.0,
                        posted_date=opp.get("postedDate"),
                        response_deadline=opp.get("responseDeadLine"),
                        solicitation_number=solicitation_number,
                        description=opp.get("descriptionText") or opp.get("description", ""),
                        summary_description="",
                        type=opp.get("type"),
                        ptype=opp.get("type"),
                        classification_code=opp.get("classificationCode"),
                        set_aside=opp.get("typeOfSetAsideDescription") or opp.get("typeOfSetAside"),
                        place_of_performance_city=city_data.get("name") if isinstance(city_data, dict) else None,
                        place_of_performance_state=state_data.get("code") if isinstance(state_data, dict) else None,
                        place_of_performance_zip=place_of_performance.get("zip"),
                        point_of_contact_email=primary_contact.get("email"),
                        point_of_contact_name=primary_contact.get("fullName"),
                        sam_link=opp.get("uiLink"),
                        assigned_practice_area=None,
                        justification=None,
                        is_amendment=is_amendment_num,
                        original_notice_id=original_notice_id,
                        superseded_by_notice_id=None,
                    )

                    crud.create_sam_opportunity(db, opportunity_data)
                    stored_count += 1

                except Exception as e:
                    error_count += 1
                    print(f"Error storing opportunity {opp.get('noticeId')}: {e}")

        except Exception as e:
            error_count += 1
            print(f"Error fetching for NAICS {naics_code}: {e}")

    return FetchByDateResponse(
        message=f"Fetched opportunities for {request.posted_date}",
        fetched_count=fetched_count,
        stored_count=stored_count,
        duplicate_count=duplicate_count,
        error_count=error_count
    )


@router.post("/{opportunity_id}/share", response_model=ShareOpportunityResponse)
def share_opportunity_via_email(
    opportunity_id: int,
    request: ShareOpportunityRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Share an opportunity via email.
    Sends an HTML-formatted email with opportunity details.
    """
    import os
    from ..email_service import EmailService, format_opportunity_email_html

    # Get the opportunity
    opportunity = crud.get_sam_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Get frontend URL from environment or construct it
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    detail_url = f"{frontend_url}/opportunities/{opportunity_id}"

    # Convert opportunity to dict for email formatting
    opp_dict = {
        "title": opportunity.title,
        "notice_id": opportunity.notice_id,
        "fit_score": opportunity.fit_score,
        "department": opportunity.department,
        "solicitation_number": opportunity.solicitation_number,
        "naics_code": opportunity.naics_code,
        "assigned_practice_area": opportunity.assigned_practice_area,
        "posted_date": opportunity.posted_date,
        "response_deadline": opportunity.response_deadline,
        "set_aside": opportunity.set_aside,
        "ptype": opportunity.ptype,
        "place_of_performance_city": opportunity.place_of_performance_city,
        "place_of_performance_state": opportunity.place_of_performance_state,
        "summary_description": opportunity.summary_description,
        "sam_link": opportunity.sam_link,
    }

    # Format HTML email
    html_body = format_opportunity_email_html(
        opportunity=opp_dict,
        detail_url=detail_url,
        sender_name=request.sender_name
    )

    # Email subject
    subject = f"SAM Opportunity: {opportunity.title}"

    # Send email in background
    def send_email_task():
        success = EmailService.send_opportunity_share_email(
            to_emails=request.to_emails,
            subject=subject,
            html_body=html_body
        )
        if not success:
            # Log error but don't raise exception in background task
            print(f"Failed to send email to {request.to_emails}")

    background_tasks.add_task(send_email_task)

    return ShareOpportunityResponse(
        success=True,
        message=f"Email will be sent to {len(request.to_emails)} recipient(s)"
    )
