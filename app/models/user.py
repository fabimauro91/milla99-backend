from sqlmodel import SQLModel, Field
from typing import Optional, Annotated
from pydantic import constr
from enum import Enum


# Custom validated types
CountryCode = Annotated[str, constr(pattern=r"^\+\d{1,3}$")]
PhoneNumber = Annotated[str, constr(min_length=7, max_length=15)]


class UserRole(str, Enum):
    driver = "driver"
    delivery = "delivery"


class UserBase(SQLModel):
    full_name: str
    country_code: CountryCode  # e.g. "+57"
    phone_number: PhoneNumber
    role: UserRole = Field(default=UserRole.driver)
    is_verified: bool = False
    is_active: bool = False


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class UserCreate(UserBase):
    pass


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    country_code: Optional[CountryCode] = None
    phone_number: Optional[PhoneNumber] = None
    role: Optional[UserRole] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
