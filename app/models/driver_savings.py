from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, ClassVar
from sqlalchemy import Column, String
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import relationship
import uuid


if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest


class SavingsType(str, Enum):
    SERVICE = "SERVICE"
    RECHARGE = "RECHARGE"
    WITHDRAWS = "WITHDRAWS"

def generate_uuid() -> str:
    return str(uuid.uuid4())


class DriverSavings(SQLModel, table=True):
    __tablename__ = "driver_savings"
    id: str = Field(
        default_factory=generate_uuid,
        primary_key=True,
        sa_column=Column(String(36), unique=True, index=True, nullable=False)
    )
    income: Optional[int] = Field(default=0)
    expense: Optional[int] = Field(default=0)
    user_id: int = Field(foreign_key="user.id")
    type: SavingsType
    client_request_id: Optional[str] = Field(
        default=None, foreign_key="clientrequest.id")
    date: datetime = Field(default_factory=datetime.utcnow)

    # Relación con ClassVar
    user: Optional["User"] = Relationship(back_populates="driver_savings")
    client_request: Optional["ClientRequest"] = Relationship(back_populates="driver_savings")