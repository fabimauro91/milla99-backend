from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import relationship
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest


class cashflow(str, Enum):
    SERVICE = "SERVICE"
    WITHDRAWS = "WITHDRAWS"
    ADDITIONAL= "ADDITIONAL"


class CompanyAccount(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    income: Optional[int] = Field(default=0)
    expense: Optional[int] = Field(default=0)
    type: cashflow
   
    client_request_id: Optional[UUID] = Field(
        default=None, foreign_key="clientrequest.id")
    date: datetime = Field(default_factory=datetime.utcnow)

    
    client_request: Optional["ClientRequest"] = Relationship(back_populates="company_accounts")

   