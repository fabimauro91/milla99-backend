from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from enum import Enum
from datetime import datetime


class AllowedRole(str, Enum):
    DRIVER = "DRIVER"
    CLIENT = "CLIENT"
    ADMIN = "ADMIN"


class TypeService(SQLModel, table=True):
    __tablename__ = "type_service"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    vehicle_type_id: int = Field(foreign_key="vehicle_type.id")
    allowed_role: AllowedRole
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

    # Relaciones
    vehicle_type: "VehicleType" = Relationship(back_populates="type_services")
    client_requests: List["ClientRequest"] = Relationship(
        back_populates="type_service")
    config_service_value: Optional["ConfigServiceValue"] = Relationship(
        back_populates="type_service")


class TypeServiceCreate(SQLModel):
    name: str
    description: Optional[str] = None
    vehicle_type_id: int
    allowed_role: AllowedRole


class TypeServiceRead(SQLModel):
    id: int
    name: str
    description: Optional[str]
    vehicle_type_id: int
    allowed_role: AllowedRole
    created_at: datetime
    updated_at: datetime
