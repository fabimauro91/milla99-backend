from sqlmodel import Session, select
from app.models.bank import Bank
from typing import List, Optional
from fastapi import HTTPException


class BankService:
    def __init__(self, session: Session):
        self.session = session

    def list_banks(self) -> List[Bank]:
        return self.session.exec(select(Bank)).all()

    def get_bank(self, bank_id: int) -> Optional[Bank]:
        bank = self.session.get(Bank, bank_id)
        if not bank:
            raise HTTPException(status_code=404, detail="Bank not found")
        return bank

    def create_bank(self, bank_data: dict) -> Bank:
        bank = Bank(**bank_data)
        self.session.add(bank)
        self.session.commit()
        self.session.refresh(bank)
        return bank

    def update_bank(self, bank_id: int, bank_data: dict) -> Bank:
        bank = self.get_bank(bank_id)
        for key, value in bank_data.items():
            if hasattr(bank, key):
                setattr(bank, key, value)
        self.session.add(bank)
        self.session.commit()
        self.session.refresh(bank)
        return bank

    def delete_bank(self, bank_id: int) -> dict:
        bank = self.get_bank(bank_id)
        self.session.delete(bank)
        self.session.commit()
        return {"message": "Bank deleted successfully"}
