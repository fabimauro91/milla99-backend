from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, ClassVar,List
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime
from pydantic import BaseModel

if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest


class TransactionType(str, Enum):
    BONUS = "BONUS"
    SERVICE = "SERVICE"
    RECHARGE = "RECHARGE"
    REFERRAL_1 = "REFERRAL_1"
    REFERRAL_2 = "REFERRAL_2"
    REFERRAL_3 = "REFERRAL_3"
    REFERRAL_4 = "REFERRAL_4"
    REFERRAL_5 = "REFERRAL_5"


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    income: Optional[int] = Field(default=0)
    expense: Optional[int] = Field(default=0)
    type: TransactionType
    client_request_id: Optional[int] = Field(
        default=None, foreign_key="clientrequest.id")
    date: datetime = Field(default_factory=datetime.utcnow)
    user: Optional["User"] = Relationship(back_populates="transactions")
    client_request: Optional["ClientRequest"] = Relationship(
        back_populates="transactions")


class TransactionCreate(BaseModel):
    income: Optional[int] = 0
    expense: Optional[int] = 0
    type: TransactionType
    client_request_id: Optional[int] = None
