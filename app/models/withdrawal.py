from sqlmodel import SQLModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Withdrawal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    amount: int
    status: WithdrawalStatus = Field(default=WithdrawalStatus.PENDING)
    withdrawal_date: datetime = Field(default_factory=datetime.utcnow)
