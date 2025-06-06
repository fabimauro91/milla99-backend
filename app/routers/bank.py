from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session
from typing import List
from app.core.db import get_session
from app.models.bank import Bank
from app.services.bank_service import BankService

router = APIRouter(prefix="/banks", tags=["banks"])


@router.get("/", response_model=List[Bank])
def list_banks(session: Session = Depends(get_session)):
    service = BankService(session)
    return service.list_banks()


@router.get("/{bank_id}", response_model=Bank)
def get_bank(bank_id: int, session: Session = Depends(get_session)):
    service = BankService(session)
    return service.get_bank(bank_id)


@router.post("/", response_model=Bank, status_code=status.HTTP_201_CREATED)
def create_bank(bank: Bank, session: Session = Depends(get_session)):
    service = BankService(session)
    return service.create_bank(bank.dict(exclude_unset=True))


@router.put("/{bank_id}", response_model=Bank)
def update_bank(bank_id: int, bank: Bank, session: Session = Depends(get_session)):
    service = BankService(session)
    return service.update_bank(bank_id, bank.dict(exclude_unset=True))


@router.delete("/{bank_id}")
def delete_bank(bank_id: int, session: Session = Depends(get_session)):
    service = BankService(session)
    return service.delete_bank(bank_id)
