from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import field_validator

# Definimos el enum para el status
class DriverStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class DriverDataBase(SQLModel):
    user_id: int = Field(foreign_key="user.id", nullable=False)
    vehicle_info_id: Optional[int] = Field(default=None, foreign_key="vehicle_info.id", nullable=True)
    soat_id: Optional[int] = Field(default=None, foreign_key="soat.id", nullable=True)
    technomechanics_id: Optional[int] = Field(default=None, foreign_key="technomechanics.id", nullable=True)
    drivers_license_id: Optional[int] = Field(default=None, foreign_key="drivers_license.id", nullable=True)
    status: DriverStatus = Field(default=DriverStatus.PENDING, nullable=False)
    qualification: Optional[int] = Field(default=None, nullable=True)

    @field_validator('qualification')
    @classmethod
    def validate_qualification(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 0 or v > 5:
                raise ValueError("Qualification must be between 0 and 5")
        return v

class DriverData(DriverDataBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    user: "User" = Relationship(back_populates="driver_data")
    vehicle_info: Optional["VehicleInfo"] = Relationship(back_populates="driver_data")
    soat: Optional["Soat"] = Relationship(back_populates="driver_data")
    technomechanics: Optional["Technomechanics"] = Relationship(back_populates="driver_data")
    drivers_license: Optional["DriversLicense"] = Relationship(back_populates="driver_data")

class DriverDataCreate(DriverDataBase):
    pass

class DriverDataRead(SQLModel):
    id: int
    user_id: int
    vehicle_info_id: Optional[int]
    soat_id: Optional[int]
    technomechanics_id: Optional[int]
    drivers_license_id: Optional[int]
    status: DriverStatus
    qualification: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class DriverDataUpdate(SQLModel):
    vehicle_info_id: Optional[int] = None
    soat_id: Optional[int] = None
    technomechanics_id: Optional[int] = None
    drivers_license_id: Optional[int] = None
    status: Optional[DriverStatus] = None
    qualification: Optional[int] = None