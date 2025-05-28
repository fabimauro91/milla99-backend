from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from uuid import UUID, uuid4


class VerifyMount(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")
    mount: int
    user: Optional["User"] = Relationship(back_populates="verify_mount")
