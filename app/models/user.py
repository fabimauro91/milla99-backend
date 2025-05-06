from sqlmodel import SQLModel, Field
from typing import Optional, Annotated, Literal
from pydantic import constr


# Custom validated types
CountryCode = Annotated[str, constr(pattern=r"^\+\d{1,3}$")]
PhoneNumber = Annotated[str, constr(min_length=7, max_length=15)]


class UserBase(SQLModel):
    full_name: str
    country_code: CountryCode  # e.g. "+57"
    phone_number: PhoneNumber
    role: Literal["driver", "delivery"]
    is_verified: bool = False
    is_active: bool = True


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class UserCreate(UserBase):
    pass


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    country_code: Optional[CountryCode] = None
    phone_number: Optional[PhoneNumber] = None
    role: Optional[Literal["driver", "delivery"]] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
