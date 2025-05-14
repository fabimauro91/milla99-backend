from typing import Optional, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from geoalchemy2 import Geometry
from pydantic import BaseModel

class DriverPosition(SQLModel, table=True):
    id_driver: int = Field(foreign_key="user.id", primary_key=True)
    position: Optional[Any] = Field(
        sa_column=Column(
            Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
            nullable=False
        )
    )
    user: Optional["User"] = Relationship(back_populates="driver_position")

class DriverPositionCreate(BaseModel):
    id_driver: int
    lat: float
    lng: float

class DriverPositionRead(BaseModel):
    id_driver: int
    lat: float
    lng: float

    @classmethod
    def from_orm_with_point(cls, obj):
        from geoalchemy2.shape import to_shape
        point = to_shape(obj.position)
        return cls(
            id_driver=obj.id_driver,
            lat=point.y,
            lng=point.x
        )

# Recuerda registrar la relación en el modelo User agregando:
# driver_position: Optional["DriverPosition"] = Relationship(back_populates="user") 