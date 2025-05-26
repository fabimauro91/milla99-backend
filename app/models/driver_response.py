from pydantic import BaseModel
from typing import Optional


class DriverDocumentsResponse(BaseModel):
    property_card_front_url: Optional[str]
    property_card_back_url: Optional[str]
    license_front_url: Optional[str]
    license_back_url: Optional[str]
    license_expiration_date: Optional[str]
    soat_url: Optional[str]
    soat_expiration_date: Optional[str]
    vehicle_technical_inspection_url: Optional[str]
    vehicle_technical_inspection_expiration_date: Optional[str]


class VehicleInfoResponse(BaseModel):
    brand: str
    model: str
    model_year: int
    color: str
    plate: str
    vehicle_type_id: int


class DriverInfoResponse(BaseModel):
    first_name: str
    last_name: str
    birth_date: str
    email: Optional[str]


class UserResponse(BaseModel):
    id: int
    full_name: str
    country_code: str
    phone_number: str
    selfie_url: Optional[str] = None


class DriverFullResponse(BaseModel):
    user: UserResponse
    driver_info: DriverInfoResponse
    vehicle_info: VehicleInfoResponse
    driver_documents: DriverDocumentsResponse
