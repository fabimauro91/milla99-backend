# app/models/referral.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from pydantic import BaseModel
from uuid import UUID, uuid4
from datetime import datetime

class Referral(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")          # usuario referido (hijo)
    referred_by_id: Optional[UUID] = Field(default=None,  # quién lo refirió (padre)
                                          foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

    # Relaciones
    user:        "User" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Referral.user_id]"})
    referred_by: "User" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Referral.referred_by_id]"})


class ReferralLinkResponse(BaseModel):
    referral_link: str
    message: str

class ReferralSendResponse(BaseModel):
    success: bool
    message: str
