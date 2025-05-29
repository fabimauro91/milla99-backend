from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

class Administrador(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    email: str = Field(index=True, unique=True, nullable=False)
    password: str = Field(nullable=False)
    role: int = Field(nullable=False, default=1) 
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )