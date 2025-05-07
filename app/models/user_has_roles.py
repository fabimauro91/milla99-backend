from sqlmodel import SQLModel, Field
from typing import Optional

class UserHasRole(SQLModel, table=True):
    id_user: Optional[int] = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    id_rol: Optional[str] = Field(foreign_key="role.id", primary_key=True, ondelete="RESTRICT") 