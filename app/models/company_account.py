from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String
from typing import Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import relationship
import uuid

if TYPE_CHECKING:
    from .user import User
    from .client_request import ClientRequest


class cashflow(str, Enum):
    SERVICE = "SERVICE"
    WITHDRAWS = "WITHDRAWS"
    ADDITIONAL= "ADDITIONAL"


# Función para generar UUID
def generate_uuid():
    return str(uuid.uuid4())


class CompanyAccount(SQLModel, table=True):
    __tablename__ = "company_account"
    id: str = Field(
        default_factory=generate_uuid,
        primary_key=True,
        sa_column=Column(String(36), unique=True, index=True, nullable=False)
    )
    income: Optional[int] = Field(default=0)
    expense: Optional[int] = Field(default=0)
    type: cashflow
   
    client_request_id: Optional[str] = Field(
        default=None, foreign_key="client_request.id")
    date: datetime = Field(default_factory=datetime.utcnow)

    
    client_request: Optional["ClientRequest"] = Relationship(back_populates="company_accounts")

   