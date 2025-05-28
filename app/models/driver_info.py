from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String
from typing import Optional, TYPE_CHECKING, List
from datetime import date
import uuid


if TYPE_CHECKING:
    from .user import User
    from .vehicle_info import VehicleInfo
    from .driver_documents import DriverDocuments


class DriverInfoBase(SQLModel):
    first_name: str
    last_name: str
    birth_date: date
    email: Optional[str] = None
    # selfie_url: Optional[str] = None  # Eliminado, ahora está en User

def generate_uuid() -> str:
    return str(uuid.uuid4())

class DriverInfo(DriverInfoBase, table=True):
    __tablename__ = "driver_info"
    id: str = Field(
        default_factory=generate_uuid,
        primary_key=True,
        sa_column=Column(String(36), unique=True, index=True, nullable=False)
    )
    user_id: int = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="driver_info")
    # driver: Optional["Driver"] = Relationship(back_populates="driver_info")
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
    # selfie_url: Optional[str] = None  # Eliminado
