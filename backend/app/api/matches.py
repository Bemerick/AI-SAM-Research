"""
API endpoints for matches between SAM and GovWin opportunities.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from . import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get("/", response_model=List[schemas.MatchWithDetails])
def list_matches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by match status"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum AI match score"),
    max_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum AI match score"),
    search_strategy: Optional[str] = Query(None, description="Filter by search strategy"),
    db: Session = Depends(get_db)
):
    """
    List matches with optional filters.
    """
    return crud.get_matches(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
        min_score=min_score,
        max_score=max_score,
        search_strategy=search_strategy
    )


@router.get("/pending", response_model=List[schemas.MatchWithDetails])
def list_pending_matches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List matches with status = 'pending_review'.
    """
    return crud.get_matches(
        db=db,
        skip=skip,
        limit=limit,
        status="pending_review"
    )


@router.get("/{match_id}", response_model=schemas.MatchWithDetails)
def get_match(
    match_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific match by ID with full details.
    """
    match = crud.get_match_with_details(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.post("/", response_model=schemas.Match, status_code=201)
def create_match(
    match: schemas.MatchCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new match between SAM and GovWin opportunities.
    """
    # Verify both opportunities exist
    sam_opp = crud.get_sam_opportunity(db, match.sam_opportunity_id)
    if not sam_opp:
        raise HTTPException(status_code=404, detail="SAM opportunity not found")

    govwin_opp = crud.get_govwin_opportunity(db, match.govwin_opportunity_id)
    if not govwin_opp:
        raise HTTPException(status_code=404, detail="GovWin opportunity not found")

    return crud.create_match(db, match)


@router.post("/from-external-ids", response_model=schemas.Match, status_code=201)
def create_match_from_external_ids(
    match_data: schemas.MatchCreateFromExternalIDs,
    db: Session = Depends(get_db)
):
    """
    Create a new match using external IDs (SAM notice ID and GovWin string ID).
    This endpoint will look up or create the GovWin opportunity automatically.
    """
    # Find SAM opportunity by notice ID
    sam_opp = crud.get_sam_opportunity_by_notice_id(db, match_data.sam_notice_id)
    if not sam_opp:
        raise HTTPException(
            status_code=404,
            detail=f"SAM opportunity with notice_id {match_data.sam_notice_id} not found"
        )

    # Find or create GovWin opportunity by string ID
    govwin_opp = crud.get_govwin_opportunity_by_govwin_id(db, match_data.govwin_id)
    if not govwin_opp:
        # GovWin opportunity doesn't exist yet - we need to create a placeholder
        # The workflow should ideally pass the full GovWin data, but we can create a minimal entry
        govwin_create = schemas.GovWinOpportunityCreate(
            govwin_id=match_data.govwin_id,
            title=f"GovWin {match_data.govwin_id}",  # Placeholder
            raw_data=None  # Will be updated later
        )
        govwin_opp = crud.create_govwin_opportunity(db, govwin_create)

    # Create the match using internal database IDs
    match_create = schemas.MatchCreate(
        sam_opportunity_id=sam_opp.id,
        govwin_opportunity_id=govwin_opp.id,
        search_strategy=match_data.search_strategy,
        ai_match_score=match_data.match_score,
        ai_reasoning=match_data.match_notes,
        status=match_data.status
    )

    return crud.create_match(db, match_create)


@router.patch("/{match_id}", response_model=schemas.Match)
def update_match(
    match_id: int,
    match_update: schemas.MatchUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a match (status, notes, AI score, etc.).
    """
    match = crud.update_match(db, match_id, match_update)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.delete("/{match_id}", status_code=204)
def delete_match(
    match_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a match.
    """
    success = crud.delete_match(db, match_id)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found")
    return None
