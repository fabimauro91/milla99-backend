from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List
from datetime import date

if TYPE_CHECKING:
    from .user import User
    from .driver import Driver
    from .vehicle_info import VehicleInfo
    from .driver_documents import DriverDocuments


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
    vehicle_info: Optional["VehicleInfo"] = Relationship(
        back_populates="driver_info")
    documents: List["DriverDocuments"] = Relationship(
        back_populates="driver_info")


class DriverInfoCreate(DriverInfoBase):
    pass


class DriverInfoUpdate(SQLModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    email: Optional[str] = None
    selfie_url: Optional[str] = None
