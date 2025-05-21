from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, Annotated, List
from pydantic import constr, field_validator, ValidationInfo, BaseModel
from enum import Enum
import phonenumbers
import re
from datetime import datetime, date
from app.models.user_has_roles import UserHasRole
from app.models.driver_documents import DriverDocuments
from datetime import datetime
from app.models.driver_payment import DriverPayment
from app.models.driver_transaction import DriverTransaction
from app.models.verify_mount import VerifyMount


# Custom validated types
CountryCode = Annotated[str, constr(pattern=r"^\+\d{1,3}$")]
PhoneNumber = Annotated[str, constr(min_length=7, max_length=15)]


class UserBase(SQLModel):
    full_name: Optional[str] = Field(default=None)
    country_code: CountryCode = Field(
        description="Código de país, ejemplo: +57")
    phone_number: PhoneNumber = Field(
        description="Número de teléfono móvil, ejemplo: 3001234567")
    is_verified_phone: bool = False
    is_active: bool = False

    # Validation for phone number
    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str, info: ValidationInfo) -> str:
        country_code = info.data.get("country_code", "")
        full_number = f"{country_code}{value}"

        try:
            parsed = phonenumbers.parse(full_number, None)

            if phonenumbers.region_code_for_number(parsed) != "CO":
                raise ValueError("Phone number must be Colombian.")
            if not str(parsed.national_number).startswith("3"):
                raise ValueError("Colombian mobile numbers must start with 3.")
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number.")
        except phonenumbers.NumberParseException as e:
            raise ValueError("Invalid phone number format.") from e

        return value


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    CLIENT = "CLIENT"


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    roles: List["Role"] = Relationship(
        back_populates="users", link_model=UserHasRole)
    driver_info: Optional["DriverInfo"] = Relationship(back_populates="user")
    driver_position: Optional["DriverPosition"] = Relationship(
        back_populates="user")
    client_requests: List["ClientRequest"] = Relationship(
        back_populates="client",
        sa_relationship_kwargs={"foreign_keys": "[ClientRequest.id_client]"}
    )
    assigned_requests: List["ClientRequest"] = Relationship(
        back_populates="driver_assigned",
        sa_relationship_kwargs={
            "foreign_keys": "[ClientRequest.id_driver_assigned]"}
    )
    driver_payment: Optional[DriverPayment] = Relationship(
        back_populates="user")
    transactions: List[DriverTransaction] = Relationship(back_populates="user")
    verify_mounts: List[VerifyMount] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[VerifyMount.id_user]"}
    )
    verified_mounts: List[VerifyMount] = Relationship(
        back_populates="verifier",
        sa_relationship_kwargs={"foreign_keys": "[VerifyMount.verified_by]"}
    )


class UserCreate(SQLModel):
    full_name: str = Field(
        description="Nombre completo del usuario",
        min_length=3
    )
    country_code: CountryCode = Field(
        description="Código de país, ejemplo: +57")
    phone_number: PhoneNumber = Field(
        description="Número de teléfono móvil, ejemplo: 3001234567",
        min_length=10,
        max_length=10
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError(
                "El nombre completo debe tener al menos 3 caracteres.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", value):
            raise ValueError(
                "El nombre completo solo puede contener letras y espacios.")
        return value


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    country_code: Optional[CountryCode] = None
    phone_number: Optional[PhoneNumber] = None
    is_verified_phone: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        value = value.strip()

        if len(value) < 3:
            raise ValueError("Full name must be at least 3 characters long.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", value):
            raise ValueError("Full name can only contain letters and spaces.")
        return value


class RoleRead(BaseModel):
    id: str
    name: str
    route: str

    class Config:
        from_attributes = True


class VehicleTypeRead(BaseModel):
    id: int
    name: str
    capacity: int


class VehicleInfoRead(BaseModel):
    id: int
    brand: str
    model: str
    model_year: int
    color: str
    plate: str
    vehicle_type: VehicleTypeRead


class DriverInfoRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    birth_date: date
    email: Optional[str]
    selfie_url: str
    vehicle_info: Optional[VehicleInfoRead] = None


class UserRead(BaseModel):
    id: int
    country_code: str
    phone_number: str
    is_verified_phone: bool
    is_active: bool
    full_name: Optional[str]
    roles: List[RoleRead]
    driver_info: Optional[DriverInfoRead] = None

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    id: int
    is_active: bool
    is_verified_phone: bool

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified_phone: bool

    class Config:
        from_attributes = True
