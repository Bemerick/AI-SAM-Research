"""
API endpoints for GovWin contracts.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/govwin-contracts", tags=["GovWin Contracts"])


@router.post("/", response_model=schemas.GovWinContract, status_code=201)
def create_govwin_contract(
    contract: schemas.GovWinContractCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new GovWin contract.
    """
    return crud.create_govwin_contract(db, contract)


@router.get("/{contract_id}", response_model=schemas.GovWinContract)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific contract by ID.
    """
    contract = crud.get_contract(db, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.get("/govwin-opportunity/{govwin_opportunity_id}", response_model=List[schemas.GovWinContract])
def get_contracts_by_opportunity(
    govwin_opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all contracts for a specific GovWin opportunity.
    """
    return crud.get_contracts_by_govwin_opportunity(db, govwin_opportunity_id)


@router.delete("/{contract_id}", status_code=204)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a contract.
    """
    success = crud.delete_govwin_contract(db, contract_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contract not found")
    return None
