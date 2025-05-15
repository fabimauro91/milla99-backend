from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class DriverTripOffer(SQLModel, table=True):
    __tablename__ = "driver_trip_offer"
    id: Optional[int] = Field(default=None, primary_key=True)
    id_driver: int = Field(foreign_key="user.id")
    id_client_request: int = Field(foreign_key="client_request.id")
    fare_offered: float = Field(..., nullable=False)
    time: float = Field(..., nullable=False)
    distance: float = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

