from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from .customer import Customer

class TransactionBase(SQLModel):
    amount: int
    description: str

class Transaction(TransactionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    customer: Customer = Relationship(back_populates="transactions")

class TransactionCreate(TransactionBase):
    customer_id: int = Field(foreign_key="customer.id")

class TransactionUpdate(TransactionBase):
    pass 