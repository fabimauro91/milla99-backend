from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class VerificationBase(SQLModel):
    user_id: UUID = Field(foreign_key="user.id")
    verification_code: str
    expires_at: datetime
    is_verified: bool = Field(default=False)
    attempts: int = Field(default=0)

class Verification(VerificationBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

class VerificationCreate(VerificationBase):
    pass