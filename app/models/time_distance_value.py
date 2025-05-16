from typing import Optional,Dict, Any, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship, Column, Integer, ForeignKey


class TimeDistanceValue(SQLModel, table=True):
    __tablename__ = "time_and_distance_value"
    id: Optional[int] = Field(default=None, primary_key=True)
    km_value: float = Field(..., nullable=False)
    min_value: float = Field(..., nullable=False)
    tarifa_value: float = Field(..., nullable=True)
    weight_value: float = Field(..., nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )
    # Llave foránea única a VehicleType
    vehicle_type_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("vehicletype.id", ondelete="CASCADE"),
            unique=True,
            nullable=False
        )
    )
    vehicle_type: Optional["VehicleType"] = Relationship(back_populates="time_distance_value")

class CalculateFareRequest(BaseModel):
    fare_id: int
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float

# Modelo para la respuesta
class FareCalculationResponse(BaseModel):
    recommended_value: float
    destination_addresses: str
    origin_addresses: str
    distance: str
    duration: str


class TimeDistanceValueCreate(BaseModel):
    km_value: float
    min_value: float
    tarifa_value: Optional[float] = None
    weight_value: Optional[float] = None

class TimeDistanceValueUpdate(BaseModel):
    km_value: Optional[float] = None
    min_value: Optional[float] = None
    tarifa_value: Optional[float] = None
    weight_value: Optional[float] = None

class TimeDistanceValueResponse(BaseModel):
    id: int
    km_value: float
    min_value: float
    tarifa_value: Optional[float]
    weight_value: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True