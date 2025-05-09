from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date


class DriverDocumentsBase(SQLModel):
    # Documentos del vehículo
    property_card_front_url: Optional[str] = None
    property_card_back_url: Optional[str] = None

    # Licencia de conducción
    license_front_url: Optional[str] = None
    license_back_url: Optional[str] = None
    license_expiration_date: Optional[date] = None

    # SOAT
    soat_url: Optional[str] = None
    soat_expiration_date: Optional[date] = None

    # Revisión técnico mecánica
    vehicle_technical_inspection_url: Optional[str] = None
    vehicle_technical_inspection_expiration_date: Optional[date] = None


class DriverDocuments(DriverDocumentsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
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
