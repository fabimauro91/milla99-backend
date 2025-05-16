from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum
# Eliminar: from geoalchemy2 import Geometry
import enum
from datetime import datetime, timezone
from typing import Optional

# Modelo de entrada (lo que el usuario envía)
class ClientRequestCreate(SQLModel):
    id_client: int
    fare_offered: Optional[float]
    fare_assigned: Optional[float]
    pickup_description: Optional[str]
    destination_description: Optional[str]
    client_rating: Optional[float]
    driver_rating: Optional[float]
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
    fare_offered: Optional[float]
    fare_assigned: Optional[float]
    pickup_description: Optional[str] = Field(max_length=255)
    destination_description: Optional[str] = Field(max_length=255)
    client_rating: Optional[float]
    driver_rating: Optional[float]
    status: StatusEnum = Field(
        default=StatusEnum.CREATED, sa_column=Column(Enum(StatusEnum)))

    # Cambiar campos geométricos por coordenadas simples
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    # Relaciones explícitas
    client: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ClientRequest.id_client]"})
    driver_assigned: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ClientRequest.id_driver_assigned]"})