from pydantic import EmailStr, field_validator
from sqlmodel import SQLModel, Field, Relationship, Session, select
from typing import List, Optional
from app.core.db import engine

class CustomerBase(SQLModel):
    name: str = Field(default=None)
    description: str | None = Field(default=None)
    email: EmailStr = Field(default=None)
    age: int = Field(default=None)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        session = Session(engine)
        query = select(Customer).where(Customer.email == value)
        result = session.exec(query).first()
        if result:
            raise ValueError("This email is already registered")
        return value

class Customer(CustomerBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    transactions: List["Transaction"] = Relationship(back_populates="customer")


class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    pass 