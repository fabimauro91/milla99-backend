from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date


class DriverBase(SQLModel):
    is_active: bool = False

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
    vehicle_type: Optional[str] = None  # "car" o "motorcycle"
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
    # identification user
    id_card_number: Optional[str] = None
    id_card_front_url: Optional[str] = None
    id_card_back_url: Optional[str] = None


class Driver(DriverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")


class DriverCreate(DriverBase):
    user_id: int  # necesary to create


class DriverUpdate(SQLModel):
    is_active: Optional[bool] = None

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
