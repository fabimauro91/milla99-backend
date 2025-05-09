from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date
from enum import Enum


class VehicleType(str, Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"


class VehicleInfoBase(SQLModel):
    vehicle_type: VehicleType
    brand: str
    model: str
    model_year: int
    color: str
    number_plate: str
    vehicle_photo_url: str
    vehicle_subtype: str  # FK table vehicle_subtype


class VehicleInfo(VehicleInfoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_info_id: int = Field(foreign_key="driverinfo.id")
    driver_info: Optional["DriverInfo"] = Relationship(
        back_populates="vehicle_info")


class VehicleInfoCreate(VehicleInfoBase):
    driver_info_id: int


class VehicleInfoUpdate(SQLModel):
    vehicle_type: Optional[VehicleType] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    model_year: Optional[int] = None
    color: Optional[str] = None
    number_plate: Optional[str] = None
    vehicle_photo_url: Optional[str] = None
    vehicle_subtype: Optional[str] = None
