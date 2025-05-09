from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from pydantic import field_validator

class TechnomechanicsBase(SQLModel):
    vehicle_id: int = Field(foreign_key="vehicle_info.id")
    expiration_date: datetime
    registration: str
    type: str = Field(description="Tipo de vehiculo")

    @field_validator('expiration_date')
    @classmethod
    def validate_expiration_date(cls, v: datetime) -> datetime:
        if v < datetime.now():
            raise ValueError("Expiration date cannot be in the past")
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = ['REGULAR', 'HEAVY', 'PUBLIC_SERVICE', 'SPECIAL']
        if v.upper() not in valid_types:
            raise ValueError(f'Type must be one of {valid_types}')
        return v.upper()

    @field_validator('registration')
    @classmethod
    def validate_registration(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Registration number cannot be empty")
        if len(v) < 5:
            raise ValueError("Registration number must be at least 5 characters long")
        return v.upper()

class Technomechanics(TechnomechanicsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relación con el vehículo
    vehicle: "VehicleInfo" = Relationship(back_populates="technomechanics")
    driver_data: Optional["DriverData"] = Relationship(back_populates="technomechanics")

class TechnomechanicsCreate(TechnomechanicsBase):
    pass

class TechnomechanicsRead(SQLModel):
    id: int
    vehicle_id: int
    expiration_date: datetime
    registration: str
    type: str
    created_at: datetime

    class Config:
        orm_mode = True

class TechnomechanicsUpdate(SQLModel):
    expiration_date: Optional[datetime] = None
    registration: Optional[str] = None
    type: Optional[str] = None