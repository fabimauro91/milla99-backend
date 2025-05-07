from sqlmodel import SQLModel, Field
from typing import Optional, Annotated
from pydantic import constr, field_validator, ValidationInfo
from enum import Enum
import phonenumbers
import re


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
    full_name: str
    country_code: CountryCode  # "+57"
    phone_number: PhoneNumber
    user_type: UserType = Field(default=UserType.driver)
    role: UserRole = Field(default=UserRole.user)
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

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        if len(value) < 3:
            raise ValueError("Full name must be at least 3 characters long.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", value):
            raise ValueError("Full name can only contain letters and spaces.")
        return value


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class UserCreate(UserBase):
    pass


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    country_code: Optional[CountryCode] = None
    phone_number: Optional[PhoneNumber] = None
    role: Optional[UserRole] = None
    user_type: Optional[UserType] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
