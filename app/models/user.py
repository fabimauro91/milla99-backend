from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, Annotated, List, ClassVar
from pydantic import constr, field_validator, ValidationInfo, BaseModel
from enum import Enum
import phonenumbers
import re
from datetime import datetime, date
from app.models.user_has_roles import UserHasRole
from app.models.driver_documents import DriverDocuments
from datetime import datetime
from sqlalchemy.orm import relationship
from uuid import UUID, uuid4


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


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    CLIENT = "CLIENT"


class User(UserBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, unique=True)
    selfie_url: Optional[str] = None
    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )

    # Relaciones
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
    transactions: List["Transaction"] = Relationship(back_populates="user")
    driver_savings: List["DriverSavings"] = Relationship(back_populates="user")
    verify_mount: Optional["VerifyMount"] = Relationship(back_populates="user")
    bank_accounts: List["BankAccount"] = Relationship(back_populates="user")
    withdrawals: List["Withdrawal"] = Relationship(back_populates="user")


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
    referral_phone: Optional[str] = Field(
        default=None,
        description="Token de referido (opcional)"
    )
    selfie_url: Optional[str] = None

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
    selfie_url: Optional[str] = None

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
    id: UUID
    brand: str
    model: str
    model_year: int
    color: str
    plate: str
    vehicle_type: VehicleTypeRead


class DriverInfoRead(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    birth_date: date
    email: Optional[str]
    vehicle_info: Optional[VehicleInfoRead] = None


class UserRead(BaseModel):
    id: UUID
    country_code: str
    phone_number: str
    is_verified_phone: bool
    is_active: bool
    full_name: Optional[str]
    selfie_url: Optional[str] = None
    roles: List[RoleRead]
    driver_info: Optional[DriverInfoRead] = None

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    id: UUID
    is_active: bool
    is_verified_phone: bool
    selfie_url: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified_phone: bool
    selfie_url: Optional[str] = None

    class Config:
        from_attributes = True
