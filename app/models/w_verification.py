from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class VerificationBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    verification_code: str
    expires_at: datetime
    is_verified: bool = Field(default=False)
    attempts: int = Field(default=0)

class Verification(VerificationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class VerificationCreate(VerificationBase):
    pass