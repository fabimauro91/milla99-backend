from sqlmodel import SQLModel, Field, Relationship
from typing import Optional


class VerifyMount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    mount: int
    user: Optional["User"] = Relationship(back_populates="verify_mount")
