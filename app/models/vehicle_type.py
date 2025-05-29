from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class VehicleTypeBase(SQLModel):
    name: str = Field(unique=True, index=True)
    capacity: int = Field(nullable=False)


class VehicleType(SQLModel, table=True):
    __tablename__ = "vehicle_type"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=255)
    capacity: int = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

    # Relaciones
    type_services: List["TypeService"] = Relationship(
        back_populates="vehicle_type")
    vehicles: List["VehicleInfo"] = Relationship(back_populates="vehicle_type")


class VehicleTypeCreate(SQLModel):
    name: str
    description: Optional[str] = None
    capacity: int


class VehicleTypeRead(SQLModel):
    id: int
    name: str
    description: Optional[str]
    capacity: int
    created_at: datetime
    updated_at: datetime


class VehicleTypeUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
