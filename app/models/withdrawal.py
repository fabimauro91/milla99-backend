from sqlmodel import SQLModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4

class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Withdrawal(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")
    amount: int
    status: WithdrawalStatus = Field(default=WithdrawalStatus.PENDING)
    withdrawal_date: datetime = Field(default_factory=datetime.utcnow)
