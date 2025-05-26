from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, ClassVar
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest


class SavingsType(str, Enum):
    SERVICE = "SERVICE"
    RECHARGE = "RECHARGE"
    WITHDRAWS = "WITHDRAWS"


class DriverSavings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    income: Optional[int] = Field(default=0)
    expense: Optional[int] = Field(default=0)
    user_id: int = Field(foreign_key="user.id")
    type: SavingsType
    client_request_id: Optional[int] = Field(
        default=None, foreign_key="clientrequest.id")
    date: datetime = Field(default_factory=datetime.utcnow)

    # Relación con ClassVar
    user: Optional["User"] = Relationship(back_populates="driver_savings")
    client_request: Optional["ClientRequest"] = Relationship(back_populates="driver_savings")