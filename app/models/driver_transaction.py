from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
from enum import Enum
from decimal import Decimal
from .driver_payment import PaymentStatus, DriverPayment


class TransactionType(str, Enum):
    DEPOSIT = "deposit"      # Ingreso de dinero
    WITHDRAWAL = "withdrawal"  # Retiro de dinero
    COMMISSION = "commission"  # Comisión de la plataforma
    REFUND = "refund"       # Reembolso
    ADJUSTMENT = "adjustment"  # Ajuste manual


class DriverTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_payment: int = Field(foreign_key="driverpayment.id")
    id_user: int = Field(foreign_key="user.id")
    transaction_type: TransactionType
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    discount_amount: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)  # Monto del descuento
    description: str = Field(max_length=255)
    # ID de referencia externo (ej: ID de pago)
    reference_id: Optional[str] = Field(default=None, max_length=100)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    payment: Optional[DriverPayment] = Relationship(
        back_populates="transactions")
    user: Optional["User"] = Relationship(back_populates="driver_transactions")

# Modelos Pydantic para operaciones


class DriverTransactionCreate(SQLModel):
    id_payment: int
    id_user: int
    transaction_type: TransactionType
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    discount_amount: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)
    description: str = Field(max_length=255)
    reference_id: Optional[str] = None


class DriverTransactionUpdate(SQLModel):
    status: Optional[PaymentStatus] = None
    reference_id: Optional[str] = None
    discount_amount: Optional[Decimal] = None
