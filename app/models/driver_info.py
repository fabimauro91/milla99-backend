from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date

if TYPE_CHECKING:
    from .user import User
    from .driver import Driver


class DriverInfoBase(SQLModel):
    first_name: str
    last_name: str
    birth_date: date
    email: Optional[str] = None
    selfie_url: str


class DriverInfo(DriverInfoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="driver_info")
    driver: Optional["Driver"] = Relationship(back_populates="driver_info")
