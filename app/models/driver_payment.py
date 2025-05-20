from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DriverPayment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_user: int = Field(foreign_key="user.id")
    total_balance: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)  # Saldo total
    available_balance: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)  # Saldo disponible
    pending_balance: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)  # Saldo pendiente
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    user: Optional["User"] = Relationship(back_populates="driver_payment")
    transactions: List["DriverTransaction"] = Relationship(
        back_populates="payment")

# Modelos Pydantic para operaciones


class DriverPaymentCreate(SQLModel):
    id_user: int
    total_balance: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    available_balance: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)
    pending_balance: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)


class DriverPaymentUpdate(SQLModel):
    total_balance: Optional[Decimal] = None
    available_balance: Optional[Decimal] = None
    pending_balance: Optional[Decimal] = None
    status: Optional[PaymentStatus] = None
