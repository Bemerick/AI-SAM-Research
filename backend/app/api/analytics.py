"""
API endpoints for analytics and statistics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app import crud, schemas
from backend.app.database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=schemas.OpportunityStatistics)
def get_opportunity_statistics(db: Session = Depends(get_db)):
    """
    Get overall opportunity statistics.
    """
    return crud.get_opportunity_statistics(db)


@router.get("/match-quality", response_model=schemas.MatchStatistics)
def get_match_statistics(db: Session = Depends(get_db)):
    """
    Get match quality statistics.
    """
    return crud.get_match_statistics(db)
