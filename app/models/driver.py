from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List
from datetime import date
from fastapi import UploadFile
from app.models.driver_documents import DriverDocuments, DriverDocumentsCreate
from app.models.user import UserCreate, UserRead
from app.models.driver_info import DriverInfoCreate, DriverInfo
from app.models.vehicle_info import VehicleInfo, VehicleInfoCreate

if TYPE_CHECKING:
    from .user import User


class DriverBase(BaseModel):
    driver_info_id: Optional[int] = Field(
        default=None, foreign_key="driverinfo.id")


class Driver(DriverBase):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    #user: Optional["User"] = Relationship(back_populates="driver")
    driver_info: Optional["DriverInfo"] = Relationship(back_populates="driver")


class DriverCreate(DriverBase):
    user_id: int  # necesario para crear


class DriverDocumentsInput(BaseModel):
    property_card_front: Optional[UploadFile] = None
    property_card_back: Optional[UploadFile] = None
    license_front: Optional[UploadFile] = None
    license_back: Optional[UploadFile] = None
    license_expiration_date: Optional[date] = None
    soat: Optional[UploadFile] = None
    soat_expiration_date: Optional[date] = None
    vehicle_technical_inspection: Optional[UploadFile] = None
    vehicle_technical_inspection_expiration_date: Optional[date] = None

    # URLs (opcionales, para compatibilidad con el modelo existente)
    property_card_front_url: Optional[str] = None
    property_card_back_url: Optional[str] = None
    license_front_url: Optional[str] = None
    license_back_url: Optional[str] = None
    soat_url: Optional[str] = None
    vehicle_technical_inspection_url: Optional[str] = None


class DriverFullCreate(SQLModel):
    user: UserCreate
    driver_info: DriverInfoCreate
    vehicle_info: VehicleInfoCreate
    driver_documents: DriverDocumentsInput
    selfie: Optional[UploadFile] = None  # Selfie del conductor


class DriverFullRead(BaseModel):
    user: UserRead
    driver_info: DriverInfo
    vehicle_info: VehicleInfo
    driver_documents: List[DriverDocuments]
