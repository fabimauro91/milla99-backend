from sqlmodel import SQLModel, Field
from datetime import datetime


class Bank(SQLModel, table=True):
    __tablename__ = "bank"

    id: int = Field(default=None, primary_key=True, index=True)
    bank_code: str = Field(max_length=10, nullable=False,
                           unique=True, index=True)
    bank_name: str = Field(max_length=100, nullable=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
