from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class RoleStatus(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXPIRED = 'expired'

class UserHasRole(SQLModel, table=True):
    id_user: Optional[int] = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    id_rol: Optional[str] = Field(foreign_key="role.id", primary_key=True, ondelete="RESTRICT")
    is_verified: bool = Field(default=False)
    status: RoleStatus = Field(default=RoleStatus.PENDING)
    verified_at: Optional[datetime] = Field(default=None) 