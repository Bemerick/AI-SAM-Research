"""
API endpoints for SAM.gov opportunities.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/sam-opportunities", tags=["SAM Opportunities"])


@router.get("/", response_model=List[schemas.SAMOpportunity])
def list_sam_opportunities(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    min_fit_score: Optional[float] = Query(None, ge=0, le=10, description="Minimum fit score"),
    department: Optional[str] = Query(None, description="Filter by department"),
    naics_code: Optional[str] = Query(None, description="Filter by NAICS code"),
    review_for_bid: Optional[str] = Query(None, description="Filter by review_for_bid status"),
    recommend_bid: Optional[str] = Query(None, description="Filter by recommend_bid status"),
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
        naics_code=naics_code
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
    """
    # Check if already exists
    existing = crud.get_sam_opportunity_by_notice_id(db, opportunity.notice_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"SAM opportunity with notice_id '{opportunity.notice_id}' already exists"
        )

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
