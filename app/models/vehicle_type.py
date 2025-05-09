from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class VehicleTypeBase(SQLModel):
    name: str = Field(unique=True, index=True)
    capacity: int = Field(nullable=False)

class VehicleType(VehicleTypeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relación con VehicleInfo
    vehicles: List["VehicleInfo"] = Relationship(back_populates="vehicle_type")

class VehicleTypeCreate(VehicleTypeBase):
    pass

class VehicleTypeUpdate(SQLModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
