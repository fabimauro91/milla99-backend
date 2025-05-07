from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, Annotated, List
from pydantic import constr, field_validator, ValidationInfo, BaseModel
from enum import Enum
import phonenumbers
import re
from app.models.user_has_roles import UserHasRole


# Custom validated types
CountryCode = Annotated[str, constr(pattern=r"^\+\d{1,3}$")]
PhoneNumber = Annotated[str, constr(min_length=7, max_length=15)]


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class UserType(str, Enum):
    driver = "driver"
    delivery = "delivery"


class UserBase(SQLModel):
    full_name: Optional[str] = Field(default=None)
    country_code: CountryCode = Field(
        description="Código de país, ejemplo: +57")
    phone_number: PhoneNumber = Field(
        description="Número de teléfono móvil, ejemplo: 3001234567")
    is_verified: bool = False
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


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    roles: List["Role"] = Relationship(
        back_populates="users", link_model=UserHasRole)
    driver: Optional["Driver"] = Relationship(back_populates="user")


class UserCreate(SQLModel):
    country_code: CountryCode = Field(
        description="Código de país, ejemplo: +57")
    phone_number: PhoneNumber = Field(
        description="Número de teléfono móvil, ejemplo: 3001234567")


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    country_code: Optional[CountryCode] = None
    phone_number: Optional[PhoneNumber] = None
    is_verified: Optional[bool] = None
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
        orm_mode = True


class UserRead(BaseModel):
    id: int
    country_code: str
    phone_number: str
    is_verified: bool
    is_active: bool
    full_name: Optional[str]
    roles: List[RoleRead]

    class Config:
        orm_mode = True
