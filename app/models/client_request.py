from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum
import enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import Field as PydanticField  # Renombrar para evitar conflictos
from geoalchemy2 import Geometry

# Modelo de entrada (lo que el usuario envía)


class ClientRequestCreate(SQLModel):
    fare_offered: Optional[float] = None
    fare_assigned: Optional[float] = None
    pickup_description: Optional[str] = None
    destination_description: Optional[str] = None
    client_rating: Optional[float] = None
    driver_rating: Optional[float] = None
    pickup_lat: float
    pickup_lng: float
    destination_lat: float
    destination_lng: float


class StatusEnum(str, enum.Enum):
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    ON_THE_WAY = "ON_THE_WAY"
    ARRIVED = "ARRIVED"
    TRAVELLING = "TRAVELLING"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"

# Modelo de base de datos


class ClientRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_client: int = Field(foreign_key="user.id")
    id_driver_assigned: Optional[int] = Field(
        default=None, foreign_key="user.id")
    fare_offered: Optional[float] = Field(default=None)
    fare_assigned: Optional[float] = Field(default=None)
    pickup_description: Optional[str] = Field(default=None, max_length=255)
    destination_description: Optional[str] = Field(
        default=None, max_length=255)
    client_rating: Optional[float] = Field(default=None)
    driver_rating: Optional[float] = Field(default=None)
    status: StatusEnum = Field(
        default=StatusEnum.CREATED,
        sa_column=Column(Enum(StatusEnum))
    )

    pickup_lat: Optional[float] = Field(default=None)
    pickup_lng: Optional[float] = Field(default=None)
    destination_lat: Optional[float] = Field(default=None)
    destination_lng: Optional[float] = Field(default=None)

    pickup_position: Optional[object] = Field(
        sa_column=Column(Geometry(geometry_type="POINT", srid=4326)))
    destination_position: Optional[object] = Field(
        sa_column=Column(Geometry(geometry_type="POINT", srid=4326)))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    # Relaciones explícitas
    client: Optional["User"] = Relationship(
        back_populates="client_requests",
        sa_relationship_kwargs={"foreign_keys": "[ClientRequest.id_client]"}
    )
    driver_assigned: Optional["User"] = Relationship(
        back_populates="assigned_requests",
        sa_relationship_kwargs={
            "foreign_keys": "[ClientRequest.id_driver_assigned]"}
    )
