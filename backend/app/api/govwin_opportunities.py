"""
API endpoints for GovWin opportunities.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/govwin-opportunities", tags=["GovWin Opportunities"])


@router.get("/", response_model=List[schemas.GovWinOpportunity])
def list_govwin_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List all GovWin opportunities.
    """
    return crud.get_govwin_opportunities(db, skip=skip, limit=limit)


@router.get("/{opportunity_id}", response_model=schemas.GovWinOpportunity)
def get_govwin_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific GovWin opportunity by ID.
    """
    opportunity = crud.get_govwin_opportunity(db, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="GovWin opportunity not found")
    return opportunity


@router.get("/govwin-id/{govwin_id}", response_model=schemas.GovWinOpportunity)
def get_govwin_opportunity_by_govwin_id(
    govwin_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific GovWin opportunity by GovWin ID.
    """
    opportunity = crud.get_govwin_opportunity_by_govwin_id(db, govwin_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="GovWin opportunity not found")
    return opportunity


@router.post("/", response_model=schemas.GovWinOpportunity, status_code=201)
def create_govwin_opportunity(
    opportunity: schemas.GovWinOpportunityCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new GovWin opportunity (or return existing).
    """
    return crud.create_govwin_opportunity(db, opportunity)


@router.delete("/{opportunity_id}", status_code=204)
def delete_govwin_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a GovWin opportunity.
    """
    success = crud.delete_govwin_opportunity(db, opportunity_id)
    if not success:
        raise HTTPException(status_code=404, detail="GovWin opportunity not found")
    return None
