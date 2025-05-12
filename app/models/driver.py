from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date
from app.models.driver_documents import DriverDocuments, DriverDocumentsCreate
from app.models.user import UserCreate, UserRead
from app.models.driver_info import DriverInfoCreate, DriverInfo
from app.models.vehicle_info import VehicleInfo, VehicleInfoCreate

if TYPE_CHECKING:
    from .user import User


class DriverBase(SQLModel):
    driver_info_id: Optional[int] = Field(
        default=None, foreign_key="driverinfo.id")


class Driver(DriverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="driver")
    driver_info: Optional["DriverInfo"] = Relationship(back_populates="driver")


class DriverCreate(DriverBase):
    user_id: int  # necesario para crear

class DriverDocumentsInput(BaseModel):
    property_card_front_url: Optional[str] = Field(None, alias="tarjeta_propiedad_frente")
    property_card_back_url: Optional[str] = Field(None, alias="tarjeta_propiedad_reverso")
    license_front_url: Optional[str] = Field(None, alias="licencia_frente")
    license_back_url: Optional[str] = Field(None, alias="licencia_reverso")
    license_expiration_date: Optional[date] = Field(None, alias="licencia_vencimiento")
    soat_url: Optional[str] = Field(None, alias="soat_url")
    soat_expiration_date: Optional[date] = Field(None, alias="soat_vencimiento")
    vehicle_technical_inspection_url: Optional[str] = Field(None, alias="tecnomecanica_url")
    vehicle_technical_inspection_expiration_date: Optional[date] = Field(None, alias="tecnomecanica_vencimiento")

class DriverFullCreate(SQLModel):
    user: UserCreate
    driver_info: DriverInfoCreate
    vehicle_info: VehicleInfoCreate
    driver_documents:  DriverDocumentsInput


class DriverFullRead(BaseModel):
    user: UserRead
    driver_info: DriverInfo
    vehicle_info: VehicleInfo
