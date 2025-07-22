from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal


class DeletedUser(SQLModel, table=True):
    __tablename__ = "deleted_users"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    phone_number: str = Field(unique=True, index=True)
    deleted_at: datetime = Field(default_factory=datetime.utcnow)
    original_balance: Decimal = Field(default=0)
    deletion_reason: Optional[str] = None
    user_type: Optional[str] = None  # 'DRIVER' o 'CLIENT'
