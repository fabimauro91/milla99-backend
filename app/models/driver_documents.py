from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import field_validator

# Definimos el enum para el status
class DriverStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class DriverDocumentsBase(SQLModel):
    user_id: int = Field(foreign_key="user.id", nullable=False)
    document_type_id: int = Field(foreign_key="documenttype.id", nullable=False)
    # vehicle_info_id: Optional[int] = Field(default=None, foreign_key="vehicle_info.id", nullable=True)
    document_front_url: str = Field(nullable=False)
    document_back_url: Optional[str] = Field(default=None, nullable=True)
    status: DriverStatus = Field(default=DriverStatus.PENDING, nullable=False)
    expiration_date: Optional[datetime] = Field(default=None, nullable=True)
    



class DriverDocuments(DriverDocumentsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
<<<<<<< HEAD
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relaciones
    user: "User" = Relationship(back_populates="driver_documents")
    documenttype: "DocumentType" = Relationship(back_populates="driver_documents")
    # vehicle_info: Optional["VehicleInfo"] = Relationship(back_populates="driver_data")
    

class DriverDocumentsCreate(DriverDocumentsBase):
    pass

class DriverDocumentsRead(SQLModel):
    id: int
    user_id: int
    document_type_id: int
    # vehicle_info_id: Optional[int]
    soat_id: Optional[int]
    technomechanics_id: Optional[int]
    drivers_license_id: Optional[int]
    status: DriverStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DriverDocumentsUpdate(SQLModel):
    document_type_id: Optional[int] = None
    # vehicle_info_id: Optional[int] = None
    soat_id: Optional[int] = None
    technomechanics_id: Optional[int] = None
    drivers_license_id: Optional[int] = None
    document_front_url: Optional[str] = None
    document_back_url: Optional[str] = None
    status: Optional[DriverStatus] = None
=======
    driver_info_id: int = Field(foreign_key="driverinfo.id")
    driver_info: Optional["DriverInfo"] = Relationship(
        back_populates="documents")


class DriverDocumentsCreate(DriverDocumentsBase):
    driver_info_id: int


class DriverDocumentsUpdate(SQLModel):
    property_card_front_url: Optional[str] = None
    property_card_back_url: Optional[str] = None
    license_front_url: Optional[str] = None
    license_back_url: Optional[str] = None
    license_expiration_date: Optional[date] = None
    soat_url: Optional[str] = None
    soat_expiration_date: Optional[date] = None
    vehicle_technical_inspection_url: Optional[str] = None
    vehicle_technical_inspection_expiration_date: Optional[date] = None
>>>>>>> feature/user-crud
