from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4
from .bank_account import BankAccountRead
from .user import UserRead

if TYPE_CHECKING:
    from .bank_account import BankAccount
    from .user import User


class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Withdrawal(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")
    amount: int  # Monto total del retiro (incluye comisión si aplica)
    status: WithdrawalStatus = Field(default=WithdrawalStatus.PENDING)
    withdrawal_date: datetime = Field(default_factory=datetime.utcnow)
    # Relación con la cuenta bancaria
    bank_account_id: UUID = Field(foreign_key="bank_account.id")

    # Relaciones
    bank_account: Optional["BankAccount"] = Relationship(
        back_populates="withdrawals")
    user: Optional["User"] = Relationship(back_populates="withdrawals")


class WithdrawalRead(SQLModel):
    """Modelo para leer retiros con información relacionada"""
    id: UUID
    user_id: UUID
    amount: int  # Monto total del retiro
    status: WithdrawalStatus
    withdrawal_date: datetime
    bank_account_id: UUID
    user: UserRead
    bank_account: BankAccountRead

    class Config:
        from_attributes = True
