from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
from enum import Enum
from .vehicle_type import VehicleType
from pydantic import BaseModel
from app.models.vehicle_type import VehicleType, VehicleTypeRead

if TYPE_CHECKING:
    from .driver_info import DriverInfo
    from .driver_documents import DriverDocuments


class VehicleInfoBase(SQLModel):
    brand: str = Field(nullable=False)
    model: str = Field(nullable=False)
    model_year: int = Field(nullable=False)
    color: str = Field(nullable=False)
    plate: str = Field(nullable=False)
    vehicle_type_id: int = Field(foreign_key="vehicletype.id", nullable=False)


class VehicleInfo(VehicleInfoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={
                                 "onupdate": datetime.utcnow})
    driver_info_id: int = Field(foreign_key="driverinfo.id")
    driver_info: Optional["DriverInfo"] = Relationship(
        back_populates="vehicle_info")
    vehicle_type: VehicleType = Relationship(back_populates="vehicles")
    driver_documents: List["DriverDocuments"] = Relationship(back_populates="vehicle_info")


class VehicleInfoCreate(VehicleInfoBase):
    pass


class VehicleInfoUpdate(SQLModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    model_year: Optional[int] = None
    color: Optional[str] = None
    plate: Optional[str] = None
    vehicle_type_id: Optional[int] = None


class VehicleInfoRead(BaseModel):
    id: int
    brand: str
    model: str
    model_year: int
    color: str
    plate: str
    vehicle_type: Optional[VehicleTypeRead] = None

    class Config:
        from_attributes = True