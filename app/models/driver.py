from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date

if TYPE_CHECKING:
    from .user import User
    from .driver_info import DriverInfo


class DriverBase(SQLModel):

    driver_info_id: Optional[int] = Field(
        default=None, foreign_key="driverinfo.id")

    # Vehicle info/ table vehicle_info id_driver_info FK (2)
    # "car" o "motorcycle" fk table vehicle_type = id, name, capacity, no optional
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None  # no optional
    model: Optional[str] = None  # no optional
    model_year: Optional[int] = None  # no optional
    color: Optional[str] = None  # no optional
    number_plate: Optional[str] = None  # no optional
    vehicle_photo_url: Optional[str] = None  # no optional
    vehicle_subtype: str = None  # FK table vehicle_subtype

    # License/ table driver_documents id_driver_info (3)
    property_card_front_url: Optional[str] = None  # no optional
    property_card_back_url: Optional[str] = None  # no optional

    license_front_url: Optional[str] = None
    license_back_url: Optional[str] = None
    license_expiration_date: Optional[date] = None

    soat_url: Optional[str] = None
    soat_expiration_date: Optional[date] = None

    vehicle_technical_inspection_url: Optional[str] = None
    vehicle_technical_inspection_expiration_date: Optional[date] = None


class Driver(DriverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="driver")
    driver_info: Optional["DriverInfo"] = Relationship(back_populates="driver")


class DriverCreate(DriverBase):
    user_id: int  # necesario para crear


class DriverUpdate(SQLModel):
    is_active: Optional[bool] = None
    driver_info_id: Optional[int] = None

    # Basic info
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None

    # License
    license_number: Optional[str] = None
    license_expiration_date: Optional[date] = None
    license_selfie_url: Optional[str] = None
    license_front_url: Optional[str] = None
    license_back_url: Optional[str] = None

    # Criminal record
    criminal_record_url: Optional[str] = None

    # Vehicle info
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    license_plate: Optional[str] = None
    vehicle_photo_url: Optional[str] = None
    property_card_front_url: Optional[str] = None
    property_card_back_url: Optional[str] = None
    manufacture_year: Optional[int] = None

    # reference code
    reference_code: Optional[str] = None

    # soat info
    soat_photo: Optional[str] = None

    # Only for motorcycles
    id_card_number: Optional[str] = None
    id_card_front_url: Optional[str] = None
    id_card_back_url: Optional[str] = None
