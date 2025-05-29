from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID

class RoleStatus(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXPIRED = 'expired'

class UserHasRole(SQLModel, table=True):
    __tablename__ = "user_has_role"
    id_user: Optional[UUID] = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    id_rol: Optional[str] = Field(foreign_key="role.id", primary_key=True, ondelete="RESTRICT")
    is_verified: bool = Field(default=False)
    status: RoleStatus = Field(default=RoleStatus.PENDING)
    verified_at: Optional[datetime] = Field(default=None) 