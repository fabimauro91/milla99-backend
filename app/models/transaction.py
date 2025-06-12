from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, ClassVar, List
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, validator
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest
    from .withdrawal import Withdrawal
    from .bank_account import BankAccount


class TransactionType(str, Enum):
    BONUS = "BONUS"
    SERVICE = "SERVICE"
    RECHARGE = "RECHARGE"
    REFERRAL_1 = "REFERRAL_1"
    REFERRAL_2 = "REFERRAL_2"
    REFERRAL_3 = "REFERRAL_3"
    REFERRAL_4 = "REFERRAL_4"
    REFERRAL_5 = "REFERRAL_5"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_SAVINGS = "TRANSFER_SAVINGS"
    BALANCE = "BALANCE"
    PAYMENT = "PAYMENT"
    COMMISSION = "COMMISSION"
    PENALITY_COMPENSATION = "PENALITY_COMPENSATION"
    PENALITY_DEDUCTION = "PENALITY_DEDUCTION"


class Transaction(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")
    income: Optional[int] = Field(default=0)
    expense: Optional[int] = Field(default=0)
    commission: Optional[int] = Field(default=0)  # Nuevo campo para comisiones
    type: TransactionType
    client_request_id: Optional[UUID] = Field(
        default=None, foreign_key="client_request.id")
    id_withdrawal: Optional[UUID] = Field(
        default=None, foreign_key="withdrawal.id")
    is_confirmed: bool = Field(default=True)
    date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )
    description: Optional[str] = None
    bank_account_id: Optional[UUID] = Field(
        foreign_key="bank_account.id",
        nullable=True
    )

    # Relaciones
    user: Optional["User"] = Relationship(back_populates="transactions")
    client_request: Optional["ClientRequest"] = Relationship(
        back_populates="transactions")
    withdrawal: Optional["Withdrawal"] = Relationship()
    bank_account: Optional["BankAccount"] = Relationship()

    @validator('bank_account_id')
    def validate_bank_account_id(cls, v, values):
        """Valida que bank_account_id sea requerido para transacciones de tipo WITHDRAWAL"""
        if 'type' in values and values['type'] == TransactionType.WITHDRAWAL and v is None:
            raise ValueError(
                'bank_account_id is required for WITHDRAWAL transactions')
        return v


class TransactionCreate(BaseModel):
    income: Optional[int] = 0
    expense: Optional[int] = 0
    type: TransactionType
    client_request_id: Optional[UUID] = None
    bank_account_id: Optional[UUID] = None

    @validator('bank_account_id')
    def validate_bank_account_id(cls, v, values):
        """Valida que bank_account_id sea requerido para transacciones de tipo WITHDRAWAL"""
        if 'type' in values and values['type'] == TransactionType.WITHDRAWAL and v is None:
            raise ValueError(
                'bank_account_id is required for WITHDRAWAL transactions')
        return v
