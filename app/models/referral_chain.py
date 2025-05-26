# app/models/referral.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from pydantic import BaseModel

class Referral(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")          # usuario referido (hijo)
    referred_by_id: Optional[int] = Field(default=None,  # quién lo refirió (padre)
                                          foreign_key="user.id")

    user:        "User" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Referral.user_id]"})
    referred_by: "User" = Relationship(sa_relationship_kwargs={"foreign_keys": "[Referral.referred_by_id]"})


class ReferralLinkResponse(BaseModel):
    referral_link: str
    message: str

class ReferralSendResponse(BaseModel):
    success: bool
    message: str
