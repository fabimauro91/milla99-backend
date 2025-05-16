from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.driver_response import DriverInfoResponse, UserResponse, VehicleInfoResponse

class DriverTripOfferCreate(SQLModel):
    id_driver: int
    id_client_request: int
    fare_offer: float
    time: float
    distance: float

class DriverTripOffer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_driver: int = Field(foreign_key="user.id")
    id_client_request: int = Field(foreign_key="clientrequest.id")
    fare_offer: float
    time: float
    distance: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DriverTripOfferResponse(BaseModel):
    id: int
    fare_offer: float
    time: float
    distance: float
    created_at: str
    updated_at: str
    user: UserResponse
    driver_info: DriverInfoResponse
    vehicle_info: VehicleInfoResponse