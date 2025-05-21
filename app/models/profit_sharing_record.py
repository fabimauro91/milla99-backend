# app/models/earning.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Earning(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_request_id: int = Field(foreign_key="clientrequest.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")  # None = empresa
    amount: float
    concept: str  # company | driver_saving | referral_1 | referral_2 | referral_3
    created_at: datetime = Field(default_factory=datetime.utcnow)