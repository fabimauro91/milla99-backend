from sqlmodel import SQLModel, Field as SQLField, Relationship
from sqlalchemy import Column, Enum
from geoalchemy2 import Geometry
import enum
from datetime import datetime, timezone
from typing import Optional
from shapely.geometry import Point
from geoalchemy2.shape import from_shape
from pydantic import Field
# Modelo de entrada (lo que el usuario envía)


class ClientRequestCreate(SQLModel):
    id_client: Optional[int] = Field(default=None, example=1)
    fare_offered: Optional[float] = Field(default=None, example=20.0)
    fare_assigned: Optional[float] = Field(default=None, example=25.0)
    pickup_description: Optional[str] = Field(
        default=None, example="Suba Bogotá")
    destination_description: Optional[str] = Field(
        default=None, example="Santa Rosita Engativa, Bogota")
    client_rating: Optional[float] = Field(default=None, example=4.5)
    driver_rating: Optional[float] = Field(default=None, example=4.8)
    pickup_lat: float = Field(example=4.718136)
    pickup_lng: float = Field(example=-74.07317)
    destination_lat: float = Field(example=4.702468)
    destination_lng: float = Field(example=-74.109776)

    def to_db(self):
        pickup_point = from_shape(
            Point(self.pickup_lng, self.pickup_lat), srid=4326)
        destination_point = from_shape(
            Point(self.destination_lng, self.destination_lat), srid=4326)
        return self


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
    id: Optional[int] = SQLField(default=None, primary_key=True)
    id_client: int = SQLField(foreign_key="user.id")
    id_driver_assigned: Optional[int] = SQLField(
        default=None, foreign_key="user.id")
    fare_offered: Optional[float]
    fare_assigned: Optional[float] = None
    pickup_description: Optional[str] = SQLField(max_length=255)
    destination_description: Optional[str] = SQLField(max_length=255)
    client_rating: Optional[float] = None
    driver_rating: Optional[float] = None
    status: StatusEnum = SQLField(
        default=StatusEnum.CREATED, sa_column=Column(Enum(StatusEnum)))
    pickup_position: Optional[str] = SQLField(
        sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )
    destination_position: Optional[str] = SQLField(
        sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = SQLField(
        default_factory=lambda: datetime.now(timezone.utc))

    # Relaciones explícitas
    client: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ClientRequest.id_client]"})
    driver_assigned: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ClientRequest.id_driver_assigned]"})
