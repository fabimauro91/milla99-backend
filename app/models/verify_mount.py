from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime


class VerifyMount(SQLModel, table=True):
    __tablename__ = "verify_mount"
    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, unique=True)
    user_id: UUID = Field(foreign_key="user.id")
    mount: int
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 nullable=False, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relaciones
    user: Optional["User"] = Relationship(back_populates="verify_mount")
