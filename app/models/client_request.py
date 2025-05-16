from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum
import enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import Field as PydanticField  # Renombrar para evitar conflictos

# Modelo de entrada (lo que el usuario envía)
class ClientRequestCreate(SQLModel):
    id_client: Optional[int] = PydanticField(default=None, example=1)
    fare_offered: Optional[float] = PydanticField(default=None, example=20.0)
    fare_assigned: Optional[float] = PydanticField(default=None, example=25.0)
    pickup_description: Optional[str] = PydanticField(
        default=None, example="Suba Bogotá")
    destination_description: Optional[str] = PydanticField(
        default=None, example="Santa Rosita Engativa, Bogota")
    client_rating: Optional[float] = PydanticField(default=None, example=4.5)
    driver_rating: Optional[float] = PydanticField(default=None, example=4.8)
    pickup_lat: float = PydanticField(example=4.718136)
    pickup_lng: float = PydanticField(example=-74.07317)
    destination_lat: float = PydanticField(example=4.702468)
    destination_lng: float = PydanticField(example=-74.109776)

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
    id_driver_assigned: Optional[int] = Field(default=None, foreign_key="user.id")
    fare_offered: Optional[float] = Field(default=None)
    fare_assigned: Optional[float] = Field(default=None)
    pickup_description: Optional[str] = Field(default=None, max_length=255)
    destination_description: Optional[str] = Field(default=None, max_length=255)
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
        sa_relationship_kwargs={"foreign_keys": "[ClientRequest.id_driver_assigned]"}
    )