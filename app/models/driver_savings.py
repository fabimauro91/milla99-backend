from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, ClassVar
from sqlalchemy import Column, String
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import relationship
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest


class SavingsType(str, Enum):
    SERVICE = "SERVICE"
    RECHARGE = "RECHARGE"
    WITHDRAWS = "WITHDRAWS"


class DriverSavings(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    income: Optional[int] = Field(default=0)
    expense: Optional[int] = Field(default=0)
    user_id: UUID = Field(foreign_key="user.id")
    type: SavingsType
    client_request_id: Optional[UUID] = Field(
        default=None, foreign_key="clientrequest.id")
    date: datetime = Field(default_factory=datetime.utcnow)

    # Relación con ClassVar
    user: Optional["User"] = Relationship(back_populates="driver_savings")
    client_request: Optional["ClientRequest"] = Relationship(back_populates="driver_savings")