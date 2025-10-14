"""
CRUD (Create, Read, Update, Delete) operations for database models.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional
from datetime import datetime
import json

from backend.app import models, schemas


# SAM Opportunity CRUD
def get_sam_opportunity(db: Session, opportunity_id: int) -> Optional[models.SAMOpportunity]:
    """Get SAM opportunity by ID."""
    return db.query(models.SAMOpportunity).filter(models.SAMOpportunity.id == opportunity_id).first()


def get_sam_opportunity_by_notice_id(db: Session, notice_id: str) -> Optional[models.SAMOpportunity]:
    """Get SAM opportunity by notice ID."""
    return db.query(models.SAMOpportunity).filter(models.SAMOpportunity.notice_id == notice_id).first()


def get_sam_opportunities(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    min_fit_score: Optional[float] = None,
    department: Optional[str] = None,
    naics_code: Optional[str] = None
) -> List[models.SAMOpportunity]:
    """Get list of SAM opportunities with optional filters."""
    query = db.query(models.SAMOpportunity)

    if min_fit_score is not None:
        query = query.filter(models.SAMOpportunity.fit_score >= min_fit_score)
    if department:
        query = query.filter(models.SAMOpportunity.department.ilike(f"%{department}%"))
    if naics_code:
        query = query.filter(models.SAMOpportunity.naics_code == naics_code)

    return query.order_by(desc(models.SAMOpportunity.fit_score)).offset(skip).limit(limit).all()


def create_sam_opportunity(db: Session, opportunity: schemas.SAMOpportunityCreate) -> models.SAMOpportunity:
    """Create new SAM opportunity."""
    db_opportunity = models.SAMOpportunity(**opportunity.model_dump())
    db.add(db_opportunity)
    db.commit()
    db.refresh(db_opportunity)
    return db_opportunity


def update_sam_opportunity(
    db: Session,
    opportunity_id: int,
    opportunity_update: schemas.SAMOpportunityUpdate
) -> Optional[models.SAMOpportunity]:
    """Update SAM opportunity."""
    db_opportunity = get_sam_opportunity(db, opportunity_id)
    if db_opportunity:
        update_data = opportunity_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_opportunity, key, value)
        db.commit()
        db.refresh(db_opportunity)
    return db_opportunity


def delete_sam_opportunity(db: Session, opportunity_id: int) -> bool:
    """Delete SAM opportunity."""
    db_opportunity = get_sam_opportunity(db, opportunity_id)
    if db_opportunity:
        db.delete(db_opportunity)
        db.commit()
        return True
    return False


# GovWin Opportunity CRUD
def get_govwin_opportunity(db: Session, opportunity_id: int) -> Optional[models.GovWinOpportunity]:
    """Get GovWin opportunity by ID."""
    return db.query(models.GovWinOpportunity).filter(models.GovWinOpportunity.id == opportunity_id).first()


def get_govwin_opportunity_by_govwin_id(db: Session, govwin_id: str) -> Optional[models.GovWinOpportunity]:
    """Get GovWin opportunity by GovWin ID."""
    return db.query(models.GovWinOpportunity).filter(models.GovWinOpportunity.govwin_id == govwin_id).first()


def get_govwin_opportunities(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[models.GovWinOpportunity]:
    """Get list of GovWin opportunities."""
    return db.query(models.GovWinOpportunity).offset(skip).limit(limit).all()


def create_govwin_opportunity(db: Session, opportunity: schemas.GovWinOpportunityCreate) -> models.GovWinOpportunity:
    """Create new GovWin opportunity or return existing."""
    # Check if already exists
    existing = get_govwin_opportunity_by_govwin_id(db, opportunity.govwin_id)
    if existing:
        return existing

    db_opportunity = models.GovWinOpportunity(**opportunity.model_dump())
    db.add(db_opportunity)
    db.commit()
    db.refresh(db_opportunity)
    return db_opportunity


def delete_govwin_opportunity(db: Session, opportunity_id: int) -> bool:
    """Delete GovWin opportunity."""
    db_opportunity = get_govwin_opportunity(db, opportunity_id)
    if db_opportunity:
        db.delete(db_opportunity)
        db.commit()
        return True
    return False


# Match CRUD
def get_match(db: Session, match_id: int) -> Optional[models.Match]:
    """Get match by ID."""
    return db.query(models.Match).filter(models.Match.id == match_id).first()


def get_match_with_details(db: Session, match_id: int) -> Optional[models.Match]:
    """Get match with full SAM and GovWin opportunity details."""
    return db.query(models.Match).filter(models.Match.id == match_id).first()


def get_matches(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    search_strategy: Optional[str] = None,
    sam_notice_id: Optional[str] = None
) -> List[models.Match]:
    """Get list of matches with optional filters."""
    query = db.query(models.Match)

    if status:
        query = query.filter(models.Match.status == status)
    if min_score is not None:
        query = query.filter(models.Match.ai_match_score >= min_score)
    if max_score is not None:
        query = query.filter(models.Match.ai_match_score <= max_score)
    if search_strategy:
        query = query.filter(models.Match.search_strategy == search_strategy)
    if sam_notice_id:
        query = query.join(models.SAMOpportunity).filter(models.SAMOpportunity.notice_id == sam_notice_id)

    return query.order_by(desc(models.Match.ai_match_score)).offset(skip).limit(limit).all()


def create_match(db: Session, match: schemas.MatchCreate) -> models.Match:
    """Create new match or return existing."""
    # Check if match already exists
    existing = db.query(models.Match).filter(
        and_(
            models.Match.sam_opportunity_id == match.sam_opportunity_id,
            models.Match.govwin_opportunity_id == match.govwin_opportunity_id
        )
    ).first()

    if existing:
        return existing

    db_match = models.Match(**match.model_dump())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match


def update_match(
    db: Session,
    match_id: int,
    match_update: schemas.MatchUpdate
) -> Optional[models.Match]:
    """Update match."""
    db_match = get_match(db, match_id)
    if db_match:
        update_data = match_update.model_dump(exclude_unset=True)

        # Set reviewed_at timestamp if status is being changed from pending_review
        if 'status' in update_data and db_match.status == 'pending_review':
            update_data['reviewed_at'] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(db_match, key, value)

        db.commit()
        db.refresh(db_match)
    return db_match


def delete_match(db: Session, match_id: int) -> bool:
    """Delete match."""
    db_match = get_match(db, match_id)
    if db_match:
        db.delete(db_match)
        db.commit()
        return True
    return False


# Search Log CRUD
def create_search_log(db: Session, search_log: schemas.SearchLogCreate) -> models.SearchLog:
    """Create search log entry."""
    db_log = models.SearchLog(**search_log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_search_logs(
    db: Session,
    sam_opportunity_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[models.SearchLog]:
    """Get search logs."""
    query = db.query(models.SearchLog)

    if sam_opportunity_id:
        query = query.filter(models.SearchLog.sam_opportunity_id == sam_opportunity_id)

    return query.order_by(desc(models.SearchLog.created_at)).offset(skip).limit(limit).all()


# Statistics and Analytics
def get_match_statistics(db: Session) -> dict:
    """Get match statistics."""
    total = db.query(models.Match).count()
    pending = db.query(models.Match).filter(models.Match.status == "pending_review").count()
    confirmed = db.query(models.Match).filter(models.Match.status == "confirmed").count()
    rejected = db.query(models.Match).filter(models.Match.status == "rejected").count()
    needs_info = db.query(models.Match).filter(models.Match.status == "needs_info").count()

    # Average AI score
    from sqlalchemy import func
    avg_score = db.query(func.avg(models.Match.ai_match_score)).filter(
        models.Match.ai_match_score.isnot(None)
    ).scalar()

    # Top search strategy
    top_strategy = db.query(
        models.Match.search_strategy,
        func.count(models.Match.id).label('count')
    ).group_by(models.Match.search_strategy).order_by(desc('count')).first()

    return {
        "total_matches": total,
        "pending_review": pending,
        "confirmed": confirmed,
        "rejected": rejected,
        "needs_info": needs_info,
        "average_ai_score": float(avg_score) if avg_score else None,
        "top_search_strategy": top_strategy[0] if top_strategy else None
    }


def get_opportunity_statistics(db: Session) -> dict:
    """Get opportunity statistics."""
    from sqlalchemy import func

    total_sam = db.query(models.SAMOpportunity).count()
    total_govwin = db.query(models.GovWinOpportunity).count()
    high_scoring = db.query(models.SAMOpportunity).filter(models.SAMOpportunity.fit_score > 6).count()
    avg_fit = db.query(func.avg(models.SAMOpportunity.fit_score)).scalar()
    total_searches = db.query(models.SearchLog).count()

    return {
        "total_sam_opportunities": total_sam,
        "total_govwin_opportunities": total_govwin,
        "high_scoring_sam_opps": high_scoring,
        "avg_fit_score": float(avg_fit) if avg_fit else None,
        "total_searches_performed": total_searches
    }


# GovWin Contract CRUD
def get_contracts_by_govwin_opportunity(db: Session, govwin_opportunity_id: int) -> List[models.GovWinContract]:
    """Get all contracts for a GovWin opportunity."""
    return db.query(models.GovWinContract).filter(
        models.GovWinContract.govwin_opportunity_id == govwin_opportunity_id
    ).all()


def get_contract(db: Session, contract_id: int) -> Optional[models.GovWinContract]:
    """Get a contract by ID."""
    return db.query(models.GovWinContract).filter(models.GovWinContract.id == contract_id).first()


def create_govwin_contract(db: Session, contract: schemas.GovWinContractCreate) -> models.GovWinContract:
    """Create a new GovWin contract."""
    db_contract = models.GovWinContract(**contract.model_dump())
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract


def delete_govwin_contract(db: Session, contract_id: int) -> bool:
    """Delete a GovWin contract."""
    contract = get_contract(db, contract_id)
    if contract:
        db.delete(contract)
        db.commit()
        return True
    return False
