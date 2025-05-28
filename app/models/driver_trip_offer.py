from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.driver_response import DriverInfoResponse, UserResponse, VehicleInfoResponse
from uuid import UUID, uuid4

class DriverTripOfferCreate(SQLModel):
    id_driver: UUID
    id_client_request: UUID
    fare_offer: float
    time: float
    distance: float

class DriverTripOffer(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, unique=True)
    id_driver: UUID = Field(foreign_key="user.id")
    id_client_request: UUID = Field(foreign_key="clientrequest.id")
    fare_offer: float
    time: float
    distance: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DriverTripOfferResponse(BaseModel):
    id: UUID
    fare_offer: float
    time: float
    distance: float
    created_at: str
    updated_at: str
    user: UserResponse
    driver_info: DriverInfoResponse
    vehicle_info: VehicleInfoResponse